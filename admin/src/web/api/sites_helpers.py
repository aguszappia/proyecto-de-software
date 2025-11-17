from __future__ import annotations

import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from flask import current_app, jsonify, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import func, inspect, or_, text

from src.core.database import db
from src.core.sites.models import ConservationStatus, Historic_Site, SiteCategory, SiteTag
from src.core.sites.service import get_site
from src.core.sites.validators import clean_str, safe_float, safe_int
from src.core.users import UserRole
from src.core.users import service as users_service
from src.web.schemas.sites import single_site_schema

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100
VALID_ORDER_CHOICES = {"rating-5-1", "rating-1-5", "latest", "oldest", "visits"}
TOKEN_SALT_FALLBACK = "public-api-token"
REVIEW_MIN_SCORE = 1
REVIEW_MAX_SCORE = 5
REVIEW_MIN_LENGTH = 20
REVIEW_MAX_LENGTH = 1000
_VISITS_COLUMN_CHECKED = False


class QueryParamError(ValueError):
    """Error amigable para indicar problemas con parámetros de query."""

    def __init__(self, message: str, *, details: Dict[str, List[str]] | None = None) -> None:
        super().__init__(message)
        self.details = details


class AuthError(RuntimeError):
    """Errores de autenticación para endpoints públicos."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)


def _ensure_visits_column():
    """Crea la columna visits si no existe (para despliegues ya en producción)."""
    global _VISITS_COLUMN_CHECKED
    if _VISITS_COLUMN_CHECKED:
        return
    try:
        inspector = inspect(db.engine)
        columns = {col["name"] for col in inspector.get_columns("historic_sites")}
        if "visits" not in columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE historic_sites ADD COLUMN visits INTEGER NOT NULL DEFAULT 0"))
    except Exception:
        # Defensive: no interrumpe el request si falla la verificación/alter.
        pass
    _VISITS_COLUMN_CHECKED = True


def _serialize_flag_state(
    flag,
    *,
    flag_key: str,
    default_messages: Dict[str, str],
    show_message_when_disabled: bool = False,
) -> Dict[str, Any]:
    """Devuelvo el estado simplificado de un flag con mensaje por defecto."""
    enabled = bool(flag and flag.enabled)
    default_message = default_messages.get(flag_key, "")
    message = ""
    if enabled:
        message = flag.message or default_message
    elif show_message_when_disabled:
        message = (flag.message or default_message or "").strip()
    return {
        "enabled": enabled,
        "message": message,
    }


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    return stripped.casefold()


def _format_user_display(user) -> str:
    if not user:
        return "Visitante"
    parts = [getattr(user, "first_name", "") or "", getattr(user, "last_name", "") or ""]
    clean = " ".join(part.strip() for part in parts if part.strip()).strip()
    if clean:
        return clean
    return getattr(user, "email", None) or "Visitante"


STATUS_ALIASES = {
    _normalize_text("excelente"): ConservationStatus.GOOD,
    _normalize_text("good"): ConservationStatus.GOOD,
    _normalize_text("bueno"): ConservationStatus.GOOD,
    _normalize_text("regular"): ConservationStatus.REGULAR,
    _normalize_text("fair"): ConservationStatus.REGULAR,
    _normalize_text("malo"): ConservationStatus.BAD,
    _normalize_text("bad"): ConservationStatus.BAD,
}
CATEGORY_ALIASES = {
    _normalize_text("arquitectura"): SiteCategory.ARCHITECTURE,
    _normalize_text("architecture"): SiteCategory.ARCHITECTURE,
    _normalize_text("infraestructura"): SiteCategory.INFRASTRUCTURE,
    _normalize_text("infrastructure"): SiteCategory.INFRASTRUCTURE,
    _normalize_text("sitio arqueologico"): SiteCategory.ARCHAEOLOGICAL,
    _normalize_text("sitio arqueológico"): SiteCategory.ARCHAEOLOGICAL,
    _normalize_text("archaeological"): SiteCategory.ARCHAEOLOGICAL,
    _normalize_text("arqueologico"): SiteCategory.ARCHAEOLOGICAL,
    _normalize_text("otro"): SiteCategory.OTRO,
    _normalize_text("other"): SiteCategory.OTRO,
}


def _parse_int_arg(name: str, *, default: int | None = None, minimum: int | None = None,
                   maximum: int | None = None) -> int | None:
    raw_value = request.args.get(name, type=str)
    parsed = safe_int(raw_value)
    if raw_value not in (None, "") and parsed is None:
        raise QueryParamError(f"El parámetro '{name}' debe ser numérico.")
    value = parsed if parsed is not None else default
    if value is None:
        return None
    if minimum is not None and value < minimum:
        raise QueryParamError(f"El parámetro '{name}' debe ser mayor o igual a {minimum}.")
    if maximum is not None and value > maximum:
        raise QueryParamError(f"El parámetro '{name}' no puede superar {maximum}.")
    return value


def _parse_float_arg(name: str) -> float | None:
    raw_value = request.args.get(name, type=str)
    parsed = safe_float(raw_value)
    if raw_value not in (None, "") and parsed is None:
        raise QueryParamError(f"El parámetro '{name}' debe ser numérico.")
    return parsed


def _filter_by_text(items: Iterable[Dict[str, Any]], field: str, needle: str) -> List[Dict[str, Any]]:
    needle_cf = needle.casefold()
    return [
        item for item in items if needle_cf in (item.get(field) or "").casefold()
    ]


def _filter_by_description(items: Iterable[Dict[str, Any]], needle: str) -> List[Dict[str, Any]]:
    needle_cf = needle.casefold()
    results = []
    for item in items:
        short_match = needle_cf in (item.get("short_description") or "").casefold()
        full_match = needle_cf in (item.get("full_description") or "").casefold()
        if short_match or full_match:
            results.append(item)
    return results


def _filter_exact(items: Iterable[Dict[str, Any]], field: str, expected: str) -> List[Dict[str, Any]]:
    expected_cf = expected.casefold()
    return [
        item for item in items if (item.get(field) or "").casefold() == expected_cf
    ]


def _filter_by_tags(items: Iterable[Dict[str, Any]], tags: Sequence[str]) -> List[Dict[str, Any]]:
    if not tags:
        return list(items)
    tag_set = [tag.casefold() for tag in tags]
    filtered: List[Dict[str, Any]] = []
    for item in items:
        site_tags = {(tag or "").casefold() for tag in item.get("tags") or []}
        if all(tag in site_tags for tag in tag_set):
            filtered.append(item)
    return filtered


def _sort_sites(items: List[Dict[str, Any]], order_by: str) -> List[Dict[str, Any]]:
    if order_by not in VALID_ORDER_CHOICES:
        raise QueryParamError(
            f"El parámetro 'order_by' debe ser uno de: {', '.join(sorted(VALID_ORDER_CHOICES))}."
        )

    def rating_value(site: Dict[str, Any]) -> float:
        for field in ("average_rating", "rating", "score"):
            value = site.get(field)
            if value is not None:
                return float(value)
        return 0.0

    if order_by == "latest":
        return sorted(
            items,
            key=lambda site: site.get("updated_at") or site.get("created_at") or "",
            reverse=True,
        )
    if order_by == "oldest":
        return sorted(
            items,
            key=lambda site: site.get("updated_at") or site.get("created_at") or "",
        )
    if order_by == "rating-5-1":
        return sorted(items, key=rating_value, reverse=True)
    if order_by == "rating-1-5":
        return sorted(items, key=rating_value)
    if order_by == "visits":
        return sorted(
            items,
            key=lambda site: site.get("visits") or 0,
            reverse=True,
        )
    return items


def _filter_visible(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item for item in items if item.get("is_visible")]


def _apply_filters(
    sites: List[Dict[str, Any]],
    *,
    name: str,
    description: str,
    city: str,
    province: str,
    tags: Sequence[str],
) -> List[Dict[str, Any]]:
    filtered = _filter_visible(sites)
    if name:
        filtered = _filter_by_text(filtered, "name", name)
    if description:
        filtered = _filter_by_description(filtered, description)
    if city:
        filtered = _filter_exact(filtered, "city", city)
    if province:
        filtered = _filter_exact(filtered, "province", province)
    if tags:
        filtered = _filter_by_tags(filtered, tags)
    return filtered


def _paginate(items: List[Dict[str, Any]], page: int, per_page: int) -> Dict[str, Any]:
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    sliced = items[start:end]
    return {
        "data": sliced,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
        },
    }


def _get_token_serializer() -> URLSafeTimedSerializer:
    secret_key = current_app.config.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY no configurada para emitir tokens.")
    salt = current_app.config.get("API_TOKEN_SALT") or TOKEN_SALT_FALLBACK
    return URLSafeTimedSerializer(secret_key=secret_key, salt=salt)


def _issue_api_token(user_id: int) -> str:
    serializer = _get_token_serializer()
    return serializer.dumps({"user_id": int(user_id)})


def _get_token_ttl() -> int:
    return current_app.config.get("API_TOKEN_TTL_SECONDS", 60 * 60 * 24)


def _require_api_user(optional: bool = False):
    session_user_id = session.get("user_id")
    session_role = session.get("user_role")
    if session_user_id and session_role == UserRole.PUBLIC.value:
        user = users_service.get_user(session_user_id)
        if user and user.is_active:
            return user

    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        if optional:
            return None
        raise AuthError("Missing Authorization header.")
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Authorization header must be 'Bearer <token>'.")
    token = parts[1].strip()
    serializer = _get_token_serializer()
    try:
        payload = serializer.loads(token, max_age=_get_token_ttl())
    except SignatureExpired:
        raise AuthError("Token expired.")
    except BadSignature:
        raise AuthError("Invalid token.")

    user_id = payload.get("user_id")
    user = users_service.get_user(user_id)
    if not user or not user.is_active or user.role != UserRole.PUBLIC.value:
        raise AuthError("Invalid user.")
    return user


def _auth_error_response(message: str):
    response = jsonify({"error": {"code": "not_authenticated", "message": message}})
    response.status_code = 401
    response.headers["WWW-Authenticate"] = "Bearer"
    return response


def _parse_state_of_conservation(value: str | None) -> ConservationStatus:
    if not value:
        raise QueryParamError("El campo 'state_of_conservation' es obligatorio.")
    normalized = _normalize_text(value)
    if normalized in STATUS_ALIASES:
        return STATUS_ALIASES[normalized]
    for option in ConservationStatus:
        if normalized in {_normalize_text(option.value), option.name.casefold()}:
            return option
    allowed = ", ".join(option.value.lower() for option in ConservationStatus)
    raise QueryParamError(f"El campo 'state_of_conservation' debe ser uno de: {allowed}.")


def _parse_category(value: str | None) -> SiteCategory:
    if not value:
        return SiteCategory.OTRO
    normalized = _normalize_text(value)
    if normalized in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[normalized]
    for option in SiteCategory:
        if normalized in {_normalize_text(option.value), option.name.casefold()}:
            return option
    allowed = ", ".join(option.value for option in SiteCategory)
    raise QueryParamError(f"El campo 'category' debe ser uno de: {allowed}.")


def _parse_tags(raw_tags: Any) -> Tuple[List[str], List[int]]:
    if raw_tags in (None, ""):
        return [], []
    if isinstance(raw_tags, str):
        candidates = [tag.strip() for tag in raw_tags.split(",")]
    elif isinstance(raw_tags, list):
        candidates = []
        for item in raw_tags:
            if isinstance(item, str):
                candidates.append(item.strip())
    else:
        raise QueryParamError("El campo 'tags' debe ser una lista de cadenas o una cadena separada por comas.")

    normalized = [tag for tag in candidates if tag]
    if not normalized:
        return [], []

    lowered = [tag.lower() for tag in normalized]
    query = db.session.query(SiteTag).filter(
        or_(
            func.lower(SiteTag.slug).in_(lowered),
            func.lower(SiteTag.name).in_(lowered),
        )
    )
    records = query.all()
    found = {
        tag.slug.lower(): tag.id
        for tag in records
    }
    found.update({tag.name.lower(): tag.id for tag in records})
    missing = sorted({tag for tag in lowered if tag not in found})
    if missing:
        raise QueryParamError(f"Las etiquetas {', '.join(missing)} no existen.")

    tag_ids = []
    seen = set()
    for tag in normalized:
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        tag_ids.append(found[key])
    return normalized, tag_ids


def _error_response(status_code: int, code: str, message: str, details: Dict[str, List[str]] | None = None):
    payload: Dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status_code


def _handle_query_error(error: QueryParamError):
    details = getattr(error, "details", None)
    if not details:
        details = {"general": [str(error)]}
    return _error_response(400, "invalid_query", "Parameter validation failed", details)


def _invalid_data_response(details: Dict[str, List[str]] | None = None):
    if details is None:
        details = {"general": ["Invalid input data"]}
    return _error_response(400, "invalid_data", "Invalid input data", details)


def _is_multipart_request() -> bool:
    content_type = (request.content_type or "").lower()
    return "multipart/form-data" in content_type


def _extract_site_payload() -> Tuple[Dict[str, Any], bool]:
    if _is_multipart_request():
        data = {key: value for key, value in request.form.items()}
        tags = request.form.getlist("tags[]") or request.form.getlist("tags")
        data.pop("tags[]", None)
        data.pop("tags", None)
        if not tags and data.get("tags"):
            raw_tags = data["tags"]
            tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
        data["tags"] = tags
        return data, True
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        return payload, False
    raise QueryParamError("El cuerpo debe ser JSON o multipart/form-data.")


def _validate_review_payload(payload: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Optional[int], str]:
    """Valido los datos de reseñas públicas."""
    errors: Dict[str, List[str]] = {}
    rating_value = safe_int(payload.get("rating"))
    if rating_value is None or rating_value < REVIEW_MIN_SCORE or rating_value > REVIEW_MAX_SCORE:
        errors.setdefault("rating", []).append("Elegí un puntaje entre 1 y 5.")

    comment_value = clean_str(payload.get("comment"))
    if not comment_value:
        errors.setdefault("comment", []).append("Escribí una reseña.")
    elif len(comment_value) < REVIEW_MIN_LENGTH:
        errors.setdefault("comment", []).append(
            f"La reseña debe tener al menos {REVIEW_MIN_LENGTH} caracteres.",
        )
    elif len(comment_value) > REVIEW_MAX_LENGTH:
        errors.setdefault("comment", []).append(
            f"La reseña no puede superar los {REVIEW_MAX_LENGTH} caracteres.",
        )
    return errors, rating_value, comment_value


def _get_site_or_404(site_id: int):
    """Trae un sitio visible o devuelve None si no existe/visible."""
    site = get_site(site_id)
    if not site or not site.get("is_visible"):
        return None
    return site


def _increment_site_visit(site_model: Historic_Site):
    """Incrementa visitas de forma segura."""
    try:
        site_model.visits = (site_model.visits or 0) + 1
        db.session.add(site_model)
        db.session.commit()
    except Exception:
        db.session.rollback()
