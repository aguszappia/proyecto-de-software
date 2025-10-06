"""Blueprint exclusivamente para ver el historial de un sitio."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from src.core.sites.history_service import ACTIONS, list_history
from src.web.controllers.auth import require_login, require_roles
from .sites_utils import clean_str, parse_date, safe_int

history_bp = Blueprint("sites_history", __name__, url_prefix="/sites")


@history_bp.get("/<int:site_id>/history")
@require_login
@require_roles("editor", "admin", "sysadmin")
def view_history(site_id: int):
    """Muestra el historial de un sitio con filtros y paginación (25)"""

    args = request.args
    user_email = clean_str(args.get("user"))
    action = clean_str(args.get("action_type"))
    date_from = parse_date(clean_str(args.get("date_from")))
    date_to = parse_date(clean_str(args.get("date_to")), end_of_day=True)
    page = safe_int(args.get("page")) or 1

    pagination = list_history(
        site_id=site_id,
        user_email=user_email or None,
        action_type=action or None,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=25,
    )

    filters = {
        "user": user_email,
        "action_type": action,
        "date_from": args.get("date_from") or "",
        "date_to": args.get("date_to") or "",
    }

    return render_template(
        "sites/history.html",
        site_id=site_id,
        filters=filters,
        actions=ACTIONS,
        pagination=pagination,
    )
