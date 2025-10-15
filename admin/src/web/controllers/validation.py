"""Blueprint para validar propuestas ciudadanas."""

from flask import Blueprint, render_template
from src.web.controllers.auth import require_login, require_permissions

validation_bp = Blueprint("validation", __name__, url_prefix="/validacion_propuestas")

@validation_bp.get("/")
@require_login
@require_permissions("proposals_validate")
def index():
    """Muestro la vista de validación a quienes tienen el permiso."""
    return render_template("validacionPropuestas.html")
