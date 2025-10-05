from flask import Blueprint, render_template
from src.web.controllers.auth import require_login, require_roles

reviews_bp = Blueprint("reviews", __name__, url_prefix="/reviews")

@reviews_bp.get("/")
@require_login
@require_roles("editor", "admin", "sysadmin")
def index():
    return render_template("moderacionReseñas.html")