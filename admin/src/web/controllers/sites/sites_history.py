"""Blueprint para revisar el historial de cada sitio."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from src.core.sites.history_service import ACTIONS, list_history
from src.core.sites.service import get_site
from src.web.controllers.auth import require_login, require_permissions
from .sites_utils import clean_str, parse_date, safe_int

history_bp = Blueprint("sites_history", __name__, url_prefix="/sites")


@history_bp.get("/<int:site_id>/history")
@require_login
@require_permissions("site_history_view")
def view_history(site_id: int):
    """Consulto el historial del sitio con filtros y lo paso al template."""

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

    site = get_site(site_id)
    site_name = site.get("name") if site else "Sitio #{}".format(site_id)

    return render_template(
        "sites/history.html",
        site_id=site_id,
        site_name=site_name,
        filters=filters,
        actions=ACTIONS,
        pagination=pagination,
    )
