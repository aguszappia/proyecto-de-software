"""Blueprint de gestión de feature flags del panel."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from src.core.flags import service as flags_service
from src.core.flags.service import FeatureFlagError
from src.web.controllers.auth import require_login, require_permissions

bp = Blueprint("featureflags", __name__, url_prefix="/featureflags")

DEFAULT_FLAG_MESSAGES = {
    "admin_maintenance_mode": "El panel de administración está en mantenimiento.",
    "portal_maintenance_mode": "El portal público está en mantenimiento.",
    "reviews_enabled": "Las reseñas están disponibles.",
}

ADMIN_MAINTENANCE_FLAG_KEY = "admin_maintenance_mode"
ADMIN_MAINTENANCE_SESSION_KEY = "admin_maintenance_message"
PORTAL_MAINTENANCE_FLAG_KEY = "portal_maintenance_mode"


@bp.route("/", methods=["GET", "POST"])
@require_login
@require_permissions("featureflags_manage")
def manage():
    """Permito a sysadmin ver y modificar los feature flags."""
    if request.method == "POST":
        key = request.form.get("flag_key")
        enabled = request.form.get("enabled") == "true"

        if enabled:
            message = (request.form.get("message") or "").strip()
            if not message:
                flash("Ingresá un mensaje de mantenimiento para activar el flag.", "error")
                return redirect(url_for("featureflags.manage"))
            if len(message) > flags_service.MAX_MESSAGE_LENGTH:
                flash(
                    f"El mensaje no puede superar {flags_service.MAX_MESSAGE_LENGTH} caracteres.",
                    "error",
                )
                return redirect(url_for("featureflags.manage"))
        else:
            message = ""

        try:
            flag = flags_service.set_flag(
                key,
                enabled=enabled,
                message=message,
                user_id=session.get("user_id"),
            )
            flash(
                f"{flag.name} {'activado' if enabled else 'desactivado'}.",
                "success",
            )
        except FeatureFlagError as exc:
            flash(str(exc), "error")

        return redirect(url_for("featureflags.manage"))

    flags = flags_service.list_flags()
    return render_template(
        "flags/featureflags.html",
        flags=flags,
        default_messages=DEFAULT_FLAG_MESSAGES,
        max_message_length=flags_service.MAX_MESSAGE_LENGTH,
    )


__all__ = [
    "bp",
    "manage",
    "DEFAULT_FLAG_MESSAGES",
    "ADMIN_MAINTENANCE_FLAG_KEY",
    "ADMIN_MAINTENANCE_SESSION_KEY",
    "PORTAL_MAINTENANCE_FLAG_KEY",
]
