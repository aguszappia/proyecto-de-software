from __future__ import annotations

import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from flask import Blueprint, current_app, jsonify, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from marshmallow import ValidationError
from sqlalchemy import func, or_

from src.core.database import db
from src.core.flags import service as flags_service
from src.core.sites.models import ConservationStatus, SiteCategory, SiteTag
from src.core.sites.service import (
    create_site,
    get_site,
    get_sites_by_location,
    list_sites,
    mark_site_favorite,
    unmark_site_favorite,
    list_favorite_site_ids,
    is_favorite_for_user,
)
from src.core.sites import images_service, tags_service
from src.core.sites.reviews_service import (
    create_site_review,
    delete_review as remove_review,
    find_review_by_user,
    get_public_review_stats,
    get_review,
    list_public_reviews_for_site,
    update_site_review,
)
from src.core.sites.validators import clean_str, safe_float, safe_int
from src.core.security.passwords import verify_password
from src.core.users import UserRole
from src.core.users import service as users_service
from src.web.schemas.sites import (
    review_list_schema,
    review_schema,
    single_site_schema,
    site_create_schema,
    site_schema,
)
from src.web.controllers.featureflags import (
    ADMIN_MAINTENANCE_FLAG_KEY,
    DEFAULT_FLAG_MESSAGES,
    PORTAL_MAINTENANCE_FLAG_KEY,
)
from src.web.controllers.sites import images_helpers

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100
VALID_ORDER_CHOICES = {"rating-5-1", "rating-1-5", "latest", "oldest"}
TOKEN_SALT_FALLBACK = "public-api-token"
REVIEW_MIN_SCORE = 1
REVIEW_MAX_SCORE = 5
REVIEW_MIN_LENGTH = 20
REVIEW_MAX_LENGTH = 1000


class QueryParamError(ValueError):
    """Error amigable para indicar problemas con parámetros de query."""

    def __init__(self, message: str, *, details: Dict[str, List[str]] | None = None) -> None:
        super().__init__(message)
        self.details = details


class AuthError(RuntimeError):
    """Errores de autenticación para endpoints públicos."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)


def _serialize_flag_state(flag, *, flag_key: str) -> Dict[str, Any]:
    """Devuelvo el estado simplificado de un flag con mensaje por defecto."""
    enabled = bool(flag and flag.enabled)
    message = ""
    if enabled:
        message = flag.message or DEFAULT_FLAG_MESSAGES.get(flag_key, "")
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


bp = Blueprint("sites_api", __name__, url_prefix="/api/sites")
auth_bp = Blueprint("public_auth_api", __name__, url_prefix="/api")


@auth_bp.get("/tags")
def list_public_tags():
    """Lista todas las etiquetas disponibles para el portal público."""
    try:
        tags = tags_service.list_tags()
        return jsonify({"data": tags}), 200
    except Exception:
        return _error_response(500, "server_error", "No se pudieron obtener las etiquetas.")


@bp.get("/")
def index():
    """Implementa el endpoint público GET /api/sites."""
    try:
        name = clean_str(request.args.get("name"))
        description = clean_str(request.args.get("description"))
        city = clean_str(request.args.get("city"))
        province = clean_str(request.args.get("province"))
        tags_raw = clean_str(request.args.get("tags")) or ""
        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]
        filter_mode = clean_str(request.args.get("filter")) or ""
        order_by = clean_str(request.args.get("order_by")) or "latest"

        latitude = _parse_float_arg("lat")
        longitude = _parse_float_arg("long")
        radius_km = _parse_float_arg("radius")

        if radius_km is not None:
            if radius_km <= 0:
                raise QueryParamError("El parámetro 'radius' debe ser mayor a 0.")
            if latitude is None or longitude is None:
                raise QueryParamError("Los filtros geoespaciales requieren 'lat' y 'long'.")
            base_sites = get_sites_by_location(latitude, longitude, radius_km * 1000)
        else:
            if latitude is not None or longitude is not None:
                raise QueryParamError("Para filtrar por coordenadas debés incluir 'radius'.")
            base_sites = list_sites()

        filtered_sites = _apply_filters(
            base_sites,
            name=name,
            description=description,
            city=city,
            province=province,
            tags=tags,
        )

        sorted_sites = _sort_sites(filtered_sites, order_by or "latest")

        favorite_user = None
        favorite_ids = set()
        try:
            if filter_mode == "favorites":
                favorite_user = _require_api_user()
            else:
                favorite_user = _require_api_user(optional=True)
        except AuthError as error:
            return _auth_error_response(str(error))

        if favorite_user:
            favorite_ids = set(list_favorite_site_ids(favorite_user.id))
            if filter_mode == "favorites":
                sorted_sites = [site for site in sorted_sites if site["id"] in favorite_ids]

        page = _parse_int_arg("page", default=1, minimum=1) or 1
        per_page = _parse_int_arg(
            "per_page",
            default=DEFAULT_PER_PAGE,
            minimum=1,
            maximum=MAX_PER_PAGE,
        ) or DEFAULT_PER_PAGE

        serialized_sites = site_schema.dump(sorted_sites)
        if favorite_ids:
            for site in serialized_sites:
                site["is_favorite"] = site.get("id") in favorite_ids
        payload = _paginate(serialized_sites, page, per_page)
        return jsonify(payload), 200
    except AuthError as error:
        return _auth_error_response(str(error))
    except QueryParamError as error:
        return _handle_query_error(error)
    except Exception:
        return _error_response(500, "server_error", "An unexpected error occurred")


@bp.get("/<int:site_id>")
def site_details(site_id: int):
    """Obtiene el detalle público de un sitio histórico."""
    try:
        site = get_site(site_id)
        if not site or not site.get("is_visible"):
            return _error_response(404, "not_found", "Site not found")
        payload = single_site_schema.dump(site)
        user = _require_api_user(optional=True)
        if user:
            payload["is_favorite"] = is_favorite_for_user(site_id, user.id)
        return jsonify(payload), 200
    except AuthError as error:
        return _auth_error_response(str(error))
    except Exception:
        return _error_response(500, "server_error", "An unexpected error occurred")


@bp.get("/<int:site_id>/reviews")
def list_site_reviews(site_id: int):
    """Lista reseñas aprobadas y la reseña del usuario autenticado."""
    try:
        site = get_site(site_id)
        if not site or not site.get("is_visible"):
            return _error_response(404, "not_found", "Site not found")
        user = _require_api_user(optional=True)
        approved_reviews = list_public_reviews_for_site(site_id)
        stats = get_public_review_stats(site_id)
        reviews_payload = review_list_schema.dump(approved_reviews)
        user_review_payload = None
        if user:
            user_review = find_review_by_user(site_id, user.id)
            if user_review:
                user_review_payload = review_schema.dump(user_review)
        payload = {
            "data": {
                "reviews": reviews_payload,
                "stats": stats,
                "user_review": user_review_payload,
            }
        }
        return jsonify(payload), 200
    except AuthError as error:
        return _auth_error_response(str(error))
    except Exception:
        return _error_response(500, "server_error", "No se pudieron obtener las reseñas.")


@bp.post("/<int:site_id>/reviews")
def create_site_review_endpoint(site_id: int):
    """Crea una reseña pendiente para un sitio visible."""
    try:
        user = _require_api_user()
        site = get_site(site_id)
        if not site or not site.get("is_visible"):
            return _error_response(404, "not_found", "Site not found")
        if not request.is_json:
            return _invalid_data_response({"general": ["El cuerpo debe ser JSON."]})
        payload = request.get_json(silent=True) or {}
        errors, rating, comment = _validate_review_payload(payload)
        if errors:
            return _invalid_data_response(errors)
        existing = find_review_by_user(site_id, user.id)
        if existing:
            return _invalid_data_response(
                {"general": ["Ya registraste una reseña para este sitio. Podés editarla."]},
            )
        review = create_site_review(site_id=site_id, user_id=user.id, rating=rating or 0, comment=comment)
        review.author_name = _format_user_display(user)
        return jsonify({"data": review_schema.dump(review)}), 201
    except AuthError as error:
        return _auth_error_response(str(error))
    except Exception:
        return _error_response(500, "server_error", "No se pudo crear la reseña.")


@bp.put("/<int:site_id>/reviews/<int:review_id>")
def update_site_review_endpoint(site_id: int, review_id: int):
    """Actualiza la reseña existente del usuario autenticado."""
    try:
        user = _require_api_user()
        site = get_site(site_id)
        if not site or not site.get("is_visible"):
            return _error_response(404, "not_found", "Site not found")
        if not request.is_json:
            return _invalid_data_response({"general": ["El cuerpo debe ser JSON."]})
        payload = request.get_json(silent=True) or {}
        errors, rating, comment = _validate_review_payload(payload)
        if errors:
            return _invalid_data_response(errors)
        review = get_review(review_id)
        if not review or review.site_id != site_id or review.user_id != user.id:
            return _error_response(404, "not_found", "Review not found")
        updated_review = update_site_review(review, rating=rating or 0, comment=comment)
        updated_review.author_name = _format_user_display(user)
        return jsonify({"data": review_schema.dump(updated_review)}), 200
    except AuthError as error:
        return _auth_error_response(str(error))
    except Exception:
        return _error_response(500, "server_error", "No se pudo actualizar la reseña.")


@bp.delete("/<int:site_id>/reviews/<int:review_id>")
def delete_site_review_endpoint(site_id: int, review_id: int):
    """Elimina la reseña propia del sitio."""
    try:
        user = _require_api_user()
        site = get_site(site_id)
        if not site or not site.get("is_visible"):
            return _error_response(404, "not_found", "Site not found")
        review = get_review(review_id)
        if not review or review.site_id != site_id or review.user_id != user.id:
            return _error_response(404, "not_found", "Review not found")
        remove_review(review)
        return "", 204
    except AuthError as error:
        return _auth_error_response(str(error))
    except Exception:
        return _error_response(500, "server_error", "No se pudo eliminar la reseña.")


@bp.post("/")
def create_site_endpoint():
    """Permite a la app pública proponer un nuevo sitio histórico."""
    try:
        payload, is_multipart = _extract_site_payload()
        cover_image_data = None
        if is_multipart:
            file_storage = request.files.get("cover_image")
            has_file = file_storage and getattr(file_storage, "filename", "").strip()
            if not has_file:
                return _invalid_data_response({"cover_image": ["Subí una imagen representativa del sitio."]})
            image_errors, extension, size = images_helpers._validate_image_file(file_storage)
            if image_errors:
                return _invalid_data_response({"cover_image": image_errors})
            cover_image_data = (file_storage, extension, size)
        else:
            return _invalid_data_response({"cover_image": ["La imagen del sitio es obligatoria."]})

        try:
            data = site_create_schema.load(payload)
        except ValidationError as error:
            # Marshmallow already organiza las claves por campo
            return _invalid_data_response(error.messages)

        name = clean_str(data.get("name"))
        short_description = clean_str(data.get("short_description"))
        description = clean_str(data.get("description"))
        city = clean_str(data.get("city"))
        province = clean_str(data.get("province"))
        latitude = safe_float(data.get("lat"))
        longitude = safe_float(data.get("long"))
        state_of_conservation = _parse_state_of_conservation(data.get("state_of_conservation"))
        category = _parse_category(data.get("category"))
        inauguration_raw = data.get("inaguration_year")
        inaguration_year = safe_int(inauguration_raw)

        missing_fields = [
            field
            for field, value in {
                "name": name,
                "short_description": short_description,
                "description": description,
                "city": city,
                "province": province,
            }.items()
            if not value
        ]
        if missing_fields:
            return _invalid_data_response({field: ["This field is required"] for field in missing_fields})
        if latitude is None or longitude is None:
            return _invalid_data_response({"general": ["'lat' and 'long' must be numeric."]})

        if inauguration_raw not in (None, "") and inaguration_year is None:
            return _invalid_data_response({"inaguration_year": ["Must be a number."]})

        _, tag_ids = _parse_tags(data.get("tags"))

        site = create_site(
            name=name,
            short_description=short_description,
            full_description=description,
            city=city,
            province=province,
            latitude=latitude,
            longitude=longitude,
            conservation_status=state_of_conservation,
            inaguration_year=inaguration_year,
            category=category,
            is_visible=False,
            tag_ids=tag_ids,
        )
        if cover_image_data:
            object_name, url = images_helpers.upload_file(site.id, cover_image_data)
            images_service.create_image(
                site.id,
                object_name=object_name,
                url=url,
                title=name or "Portada del sitio",
                description=None,
                make_cover=True,
            )
        db.session.refresh(site)
        response_payload = single_site_schema.dump(site)
        return jsonify(response_payload), 201
    except QueryParamError as error:
        details = getattr(error, "details", None) or {"general": [str(error)]}
        return _invalid_data_response(details)
    except ValidationError as error:  # Defensive: por si aparece fuera del load principal
        return _invalid_data_response(error.messages)
    except Exception:  # pragma: no cover - defensive fallback
        return _error_response(500, "server_error", "An unexpected error occurred")


@bp.put("/<int:site_id>/favorite")
def mark_favorite_endpoint(site_id: int):
    """Marca un sitio como favorito para el usuario autenticado."""
    try:
        user = _require_api_user()
        site = get_site(site_id)
        if not site or not site.get("is_visible"):
            return _error_response(404, "not_found", "Site not found")
        success = mark_site_favorite(site_id, user.id)
        if not success:
            return _error_response(404, "not_found", "Site not found")
        return "", 204
    except AuthError as error:
        return _auth_error_response(str(error))
    except Exception:
        return _error_response(500, "server_error", "An unexpected error occurred")


@bp.delete("/<int:site_id>/favorite")
def unmark_favorite_endpoint(site_id: int):
    """Elimina un sitio de los favoritos del usuario."""
    try:
        user = _require_api_user()
        site = get_site(site_id)
        if not site or not site.get("is_visible"):
            return _error_response(404, "not_found", "Site not found")
        unmark_site_favorite(site_id, user.id)
        return "", 204
    except AuthError as error:
        return _auth_error_response(str(error))
    except Exception:
        return _error_response(500, "server_error", "An unexpected error occurred")


@auth_bp.post("/login")
def api_login():
    """Obtengo un token Bearer para usuarios públicos."""
    try:
        if not request.is_json:
            raise QueryParamError("El cuerpo debe ser JSON válido.")
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            raise QueryParamError("El cuerpo JSON debe ser un objeto.")

        email = clean_str(payload.get("email")).lower()
        password = payload.get("password") or ""
        if not email or not password:
            raise QueryParamError("Los campos 'email' y 'password' son obligatorios.")

        user = users_service.find_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("Credenciales inválidas.")
        if not user.is_active:
            raise AuthError("Usuario inactivo.")
        if user.role != UserRole.PUBLIC.value:
            raise AuthError("Solo usuarios con rol público pueden usar esta API.")

        token = _issue_api_token(user.id)
        ttl = current_app.config.get("API_TOKEN_TTL_SECONDS", 60 * 60 * 24)
        return jsonify(
            {
                "token": token,
                "token_type": "bearer",
                "expires_in": ttl,
            }
        ), 200
    except QueryParamError as error:
        return jsonify({"error": str(error)}), 400
    except AuthError as error:
        response = jsonify({"error": str(error)})
        response.status_code = 401
        response.headers["WWW-Authenticate"] = "Bearer"
        return response
    except Exception as error:  # pragma: no cover - defensive fallback
        return jsonify({"error": "No se pudo generar el token.", "details": str(error)}), 500


@auth_bp.get("/status")
def public_status():
    """Expongo el estado de mantenimiento para las apps pública y privada."""
    flags = flags_service.load_flags()
    admin_flag = flags.get(ADMIN_MAINTENANCE_FLAG_KEY)
    portal_flag = flags.get(PORTAL_MAINTENANCE_FLAG_KEY)

    admin_state = _serialize_flag_state(admin_flag, flag_key=ADMIN_MAINTENANCE_FLAG_KEY)
    portal_state = _serialize_flag_state(portal_flag, flag_key=PORTAL_MAINTENANCE_FLAG_KEY)

    payload = {
        "maintenance": {
            "admin": admin_state,
            "portal": portal_state,
        }
    }
    return jsonify(payload), 200
