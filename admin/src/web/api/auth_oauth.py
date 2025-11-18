"""Endpoints de OAuth para login público con Google."""

from __future__ import annotations

import secrets

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for
from flask_jwt_extended import create_access_token, set_access_cookies

from src.core.users import UserRole
from src.core.users import service as users_service
from src.web.oauth import oauth

public_oauth_bp = Blueprint("public_oauth_api", __name__, url_prefix="/api/auth")


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
    # Forzamos a Google a mostrar el selector de cuentas aunque haya sesiones activas.
    return oauth.google.authorize_redirect(
        redirect_uri,
        prompt="select_account",
    )


@public_oauth_bp.get("/google/callback")
def google_callback():
    """Completa el flujo OAuth: crea/actualiza el usuario y arma la sesión."""
    next_url = session.get("next_url") or "/"
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

    session.pop("next_url", None)

    target = next_url or "/"
    if isinstance(target, str) and target.lower().startswith(("http://", "https://")):
        response = redirect(target)
    else:
        response = redirect(target)

    claims = {
        "email": user.email,
        "role": user.role,
    }
    if avatar:
        claims["avatar"] = avatar
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    set_access_cookies(response, access_token)
    return response
