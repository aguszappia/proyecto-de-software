"""Blueprint para moderar reseñas dentro del panel."""

from flask import Blueprint, render_template
from src.web.controllers.auth import require_login, require_permissions

reviews_bp = Blueprint("reviews", __name__, url_prefix="/moderacion_reseñas")

@reviews_bp.get("/")
@require_login
@require_permissions("reviews_moderate")
def index():
    """Renderizo la vista de moderación para usuarios autorizados."""
    return render_template("moderacionReseñas.html")
