"""Endpoints de OAuth para login público con Google."""

from __future__ import annotations

import secrets

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for

from src.core.permissions import service as permissions_service
from src.core.users import UserRole
from src.core.users import service as users_service
from src.web.oauth import oauth

public_oauth_bp = Blueprint("public_oauth_api", __name__, url_prefix="/api/auth")


def _issue_session_for_user(user, *, avatar_url: str | None = None) -> None:
    """Limpio y actualizo la sesión para el usuario autenticado."""
    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["user_role"] = user.role
    permissions = [perm.code for perm in permissions_service.list_role_permissions(user.role)]
    session["permissions"] = permissions
    if avatar_url:
        session["user_avatar"] = avatar_url


def _default_redirect_uri() -> str:
    configured = current_app.config.get("GOOGLE_REDIRECT_URI")
    if configured:
        return configured
    return url_for("public_oauth_api.google_callback", _external=True)


@public_oauth_bp.get("/google/login")
def google_login():
    """Inicia el flujo OAuth guardando el next solicitado."""
    next_url = request.args.get("next") or "/"
    session["next_url"] = next_url
    redirect_uri = _default_redirect_uri()
    return oauth.google.authorize_redirect(redirect_uri)


@public_oauth_bp.get("/google/callback")
def google_callback():
    """Completa el flujo OAuth: crea/actualiza el usuario y arma la sesión."""
    try:
        token = oauth.google.authorize_access_token()
    except Exception as exc:
        session.pop("next_url", None)
        # TEMPORAL: devolver el detalle del error para debug
        return jsonify(
            {
                "error": "oauth_failed",
                "details": str(exc),
            }
        ), 400

    userinfo = token.get("userinfo")
    
    if not userinfo:
        try:
            resp = oauth.google.get("userinfo")
            userinfo = resp.json()
        except Exception:
            userinfo = None

    if not userinfo:
        session.pop("next_url", None)
        return jsonify({"error": "userinfo_unavailable"}), 400

    email = (userinfo.get("email") or "").strip().lower()
    if not email:
        session.pop("next_url", None)
        return jsonify({"error": "email_required"}), 400

    # GUARDO NEXT ANTES DE HACER session.clear()
    next_url = session.get("next_url") or "/"

    user = users_service.find_user_by_email(email)
    if not user:
        first_name = userinfo.get("given_name") or userinfo.get("name") or "Usuario"
        last_name = userinfo.get("family_name") or ""
        generated_password = secrets.token_urlsafe(16)
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": generated_password,
            "role": UserRole.PUBLIC.value,
            "is_active": True,
        }
        success, created_user, errors = users_service.create_user(payload, allowed_roles=[UserRole.PUBLIC])
        if not success or created_user is None:
            session.pop("next_url", None)
            return jsonify({"error": "user_creation_failed", "details": errors or {}}), 400
        user = created_user

    if not user.is_active:
        session.pop("next_url", None)
        return jsonify({"error": "user_inactive"}), 403

    avatar = userinfo.get("picture")

    # AHORA SÍ: ARMO LA SESIÓN
    _issue_session_for_user(user, avatar_url=avatar)

    # Limpio el next_url de la sesión, pero uso el que me guardé antes
    session.pop("next_url", None)

    # Redirijo al portal público
    return redirect(next_url or "/")