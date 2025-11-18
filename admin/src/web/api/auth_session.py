"""Endpoints REST de autenticación para el portal público."""

from __future__ import annotations

from flask import Blueprint, jsonify, session

from src.core.permissions import service as permissions_service
from src.core.users import service as users_service

session_api_bp = Blueprint("public_session_api", __name__, url_prefix="/api")


def _serialize_user(user, permissions: list[str]):
    """Preparo la respuesta pública con los datos básicos del usuario."""
    full_name = f"{user.first_name} {user.last_name}".strip()
    payload = {
        "id": user.id,
        "name": full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "permissions": permissions,
    }
    avatar = session.get("user_avatar")
    if avatar:
        payload["avatar"] = avatar
    return payload


@session_api_bp.get("/me")
def show_current_user():
    """Devuelve el usuario autenticado utilizando la sesión existente."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "not_authenticated"}), 401

    user = users_service.get_user(user_id)
    if not user:
        session.clear()
        return jsonify({"error": "not_authenticated"}), 401

    permissions = session.get("permissions")
    if permissions is None:
        permissions = [
            perm.code for perm in permissions_service.list_role_permissions(user.role)
        ]
        session["permissions"] = permissions

    return jsonify({"data": _serialize_user(user, permissions)}), 200


@session_api_bp.post("/auth/logout")
def api_logout():
    """Cierra la sesión activa y devuelve una respuesta JSON."""
    session.clear()
    return jsonify({"message": "logged_out"}), 200
