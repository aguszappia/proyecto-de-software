from __future__ import annotations

from typing import Dict, List, Optional

from flask import Blueprint, jsonify, request, session
from itsdangerous import BadSignature, SignatureExpired
from marshmallow import ValidationError

from src.core.database import db
from src.core.flags import service as flags_service
from src.core.sites import images_service, tags_service
from src.core.sites.models import Historic_Site
from src.core.sites.reviews_service import (
    create_site_review,
    delete_review as remove_review,
    find_review_by_user,
    get_public_review_stats,
    get_review,
    list_public_reviews_for_site,
    list_reviews_for_user,
    update_site_review,
)
from src.core.sites.service import (
    create_site,
    get_site,
    get_sites_by_location,
    is_favorite_for_user,
    list_favorite_site_ids,
    list_sites,
    mark_site_favorite,
    unmark_site_favorite,
)
from src.core.security.passwords import verify_password
from src.core.users import UserRole
from src.core.users import service as users_service
from src.core.sites.validators import safe_float, safe_int
from src.web.api.sites_helpers import (
    CATEGORY_ALIASES,
    DEFAULT_PER_PAGE,
    MAX_PER_PAGE,
    STATUS_ALIASES,
    VALID_ORDER_CHOICES,
    _apply_filters,
    _auth_error_response,
    _ensure_visits_column,
    _error_response,
    _extract_site_payload,
    _filter_by_tags,
    _filter_visible,
    _format_user_display,
    _get_token_serializer,
    _get_token_ttl,
    _get_site_or_404,
    _handle_query_error,
    _increment_site_visit,
    _invalid_data_response,
    _issue_api_token,
    _normalize_text,
    _paginate,
    _parse_category,
    _parse_float_arg,
    _parse_int_arg,
    _parse_state_of_conservation,
    _parse_tags,
    _require_api_user,
    _serialize_flag_state,
    _sort_sites,
    _validate_review_payload,
    AuthError,
    QueryParamError,
    TOKEN_SALT_FALLBACK,
)
from src.web.controllers.featureflags import (
    ADMIN_MAINTENANCE_FLAG_KEY,
    DEFAULT_FLAG_MESSAGES,
    PORTAL_MAINTENANCE_FLAG_KEY,
    REVIEWS_ENABLED_FLAG_KEY,
)
from src.web.schemas.sites import (
    review_list_schema,
    review_schema,
    single_site_schema,
    site_create_schema,
    site_schema,
)

bp = Blueprint("sites_api", __name__, url_prefix="/api/sites")
auth_bp = Blueprint("public_auth_api", __name__, url_prefix="/api")

REVIEWS_DISABLED_ERROR_MESSAGE = "La creación de reseñas está deshabilitada temporalmente."


def _is_reviews_feature_enabled() -> bool:
    flags = flags_service.load_flags()
    flag = flags.get(REVIEWS_ENABLED_FLAG_KEY)
    if not flag:
        return True
    return bool(flag.enabled)


def _reviews_disabled_response():
    return _error_response(503, "reviews_disabled", REVIEWS_DISABLED_ERROR_MESSAGE)


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
        _ensure_visits_column()
        name = request.args.get("name")
        description = request.args.get("description")
        city = request.args.get("city")
        province = request.args.get("province")
        tags_raw = request.args.get("tags") or ""
        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]
        filter_mode = request.args.get("filter") or ""
        order_by = request.args.get("order_by") or "latest"

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
            name=_normalize_text(name) if name else "",
            description=_normalize_text(description) if description else "",
            city=_normalize_text(city) if city else "",
            province=_normalize_text(province) if province else "",
            tags=[_normalize_text(tag) for tag in tags],
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
        _ensure_visits_column()
        site_model = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
        if not site_model or not getattr(site_model, "is_visible", False):
            return _error_response(404, "not_found", "Site not found")
        _increment_site_visit(site_model)
        payload = single_site_schema.dump(site_model)
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
        site = _get_site_or_404(site_id)
        if not site:
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
        if not _is_reviews_feature_enabled():
            return _reviews_disabled_response()
        user = _require_api_user()
        site = _get_site_or_404(site_id)
        if not site:
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
        if not _is_reviews_feature_enabled():
            return _reviews_disabled_response()
        user = _require_api_user()
        site = _get_site_or_404(site_id)
        if not site:
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
        if not _is_reviews_feature_enabled():
            return _reviews_disabled_response()
        user = _require_api_user()
        site = _get_site_or_404(site_id)
        if not site:
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
            return _invalid_data_response(error.messages)

        name = data.get("name")
        short_description = data.get("short_description")
        description = data.get("description")
        city = data.get("city")
        province = data.get("province")
        latitude = safe_float(data.get("lat")) if hasattr(data, "get") else None
        longitude = safe_float(data.get("long")) if hasattr(data, "get") else None
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
    except ValidationError as error:
        return _invalid_data_response(error.messages)
    except Exception:
        return _error_response(500, "server_error", "An unexpected error occurred")


@bp.put("/<int:site_id>/favorite")
def mark_favorite_endpoint(site_id: int):
    """Marca un sitio como favorito para el usuario autenticado."""
    try:
        user = _require_api_user()
        site = _get_site_or_404(site_id)
        if not site:
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
        site = _get_site_or_404(site_id)
        if not site:
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

        email = (payload.get("email") or "").strip().lower()
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
        ttl = _get_token_ttl()
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
    except Exception as error:
        return jsonify({"error": "No se pudo generar el token.", "details": str(error)}), 500


@auth_bp.get("/status")
def public_status():
    """Expongo el estado de mantenimiento para las apps pública y privada."""
    flags = flags_service.load_flags()
    admin_flag = flags.get(ADMIN_MAINTENANCE_FLAG_KEY)
    portal_flag = flags.get(PORTAL_MAINTENANCE_FLAG_KEY)

    admin_state = _serialize_flag_state(admin_flag, flag_key=ADMIN_MAINTENANCE_FLAG_KEY, default_messages=DEFAULT_FLAG_MESSAGES)
    portal_state = _serialize_flag_state(portal_flag, flag_key=PORTAL_MAINTENANCE_FLAG_KEY, default_messages=DEFAULT_FLAG_MESSAGES)

    payload = {
        "maintenance": {
            "admin": admin_state,
            "portal": portal_state,
        }
    }
    return jsonify(payload), 200


@auth_bp.get("/token/verify")
def verify_token():
    """Verifica un token público existente."""
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        return jsonify({"valid": False, "error": "Missing Authorization header."}), 401
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return jsonify({"valid": False, "error": "Invalid Authorization header."}), 401
    token = parts[1].strip()
    serializer = _get_token_serializer()
    try:
        payload = serializer.loads(token, max_age=_get_token_ttl())
        user_id = payload.get("user_id")
        if not user_id:
            raise AuthError("Invalid token.")
        user = users_service.get_user(user_id)
        if not user or not user.is_active or user.role != UserRole.PUBLIC.value:
            raise AuthError("Invalid user.")
        return jsonify({"valid": True, "user_id": user_id}), 200
    except (AuthError, BadSignature, SignatureExpired) as err:
        return jsonify({"valid": False, "error": str(err)}), 401


@auth_bp.get("/flags")
def get_public_flags():
    """Retorna el estado de los flags de mantenimiento."""
    flags = flags_service.load_flags()
    admin_flag = flags.get(ADMIN_MAINTENANCE_FLAG_KEY)
    portal_flag = flags.get(PORTAL_MAINTENANCE_FLAG_KEY)
    reviews_flag = flags.get(REVIEWS_ENABLED_FLAG_KEY)

    admin_state = _serialize_flag_state(admin_flag, flag_key=ADMIN_MAINTENANCE_FLAG_KEY, default_messages=DEFAULT_FLAG_MESSAGES)
    portal_state = _serialize_flag_state(portal_flag, flag_key=PORTAL_MAINTENANCE_FLAG_KEY, default_messages=DEFAULT_FLAG_MESSAGES)
    reviews_state = _serialize_flag_state(
        reviews_flag,
        flag_key=REVIEWS_ENABLED_FLAG_KEY,
        default_messages=DEFAULT_FLAG_MESSAGES,
        show_message_when_disabled=True,
    )

    return jsonify(
        {
            "flags": {
                "admin": admin_state,
                "portal": portal_state,
                "reviews": reviews_state,
            }
        }
    ), 200


@auth_bp.get("/me/reviews")
def list_my_reviews():
    """Devuelve las reseñas creadas por el usuario autenticado."""
    try:
        user = _require_api_user()
        reviews = list_reviews_for_user(user.id)
        payload: List[Dict[str, Optional[object]]] = []
        for item in reviews:
            review = item.get("review")
            site = item.get("site")
            serialized = review_schema.dump(review)
            serialized["site"] = {
                "id": getattr(site, "id", None),
                "name": getattr(site, "name", None),
                "city": getattr(site, "city", None),
                "province": getattr(site, "province", None),
                "cover_image_url": getattr(site, "cover_image_url", None),
                "cover_image_title": getattr(site, "cover_image_title", None),
            }
            payload.append(serialized)
        return jsonify({"data": payload}), 200
    except AuthError as error:
        return _auth_error_response(str(error))
    except Exception:
        return _error_response(500, "server_error", "No se pudieron obtener tus reseñas.")
