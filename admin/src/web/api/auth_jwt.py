"""Endpoints alternativos basados en JWT para el portal público."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required, unset_jwt_cookies

from src.core.permissions import service as permissions_service
from src.core.users import service as users_service

jwt_api_bp = Blueprint("public_jwt_api", __name__, url_prefix="/api/auth/jwt")


def _serialize_user(user, permissions: list[str], avatar_url: str | None = None):
    """Mantengo el mismo formato de /api/me."""
    full_name = f"{user.first_name} {user.last_name}".strip()
    payload = {
        "id": user.id,
        "name": full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "permissions": permissions,
    }
    if avatar_url:
        payload["avatar"] = avatar_url
    return payload


@jwt_api_bp.get("/me")
@jwt_required()
def show_current_user_jwt():
    """Devuelve la información del usuario usando la identidad del JWT."""
    identity = get_jwt_identity()
    if not identity:
        return jsonify({"error": "not_authenticated"}), 401

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 400

    user = users_service.get_user(user_id)
    if not user or not user.is_active:
        return jsonify({"error": "not_authenticated"}), 401

    permissions = [perm.code for perm in permissions_service.list_role_permissions(user.role)]
    avatar_url = get_jwt().get("avatar")
    return jsonify({"data": _serialize_user(user, permissions, avatar_url)}), 200


@jwt_api_bp.post("/logout")
def logout_jwt():
    """Limpia cookies JWT."""
    response = jsonify({"message": "logged_out"})
    unset_jwt_cookies(response)
    return response
