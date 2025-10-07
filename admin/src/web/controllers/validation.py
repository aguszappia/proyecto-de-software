from flask import Blueprint, render_template
from src.web.controllers.auth import require_login, require_permissions

validation_bp = Blueprint("validation", __name__, url_prefix="/validacionPropuestas")

@validation_bp.get("/")
@require_login
@require_permissions("proposals_validate")
def index():
    return render_template("validacionPropuestas.html")
