"""Blueprint público para mostrar los sitios visibles."""

from __future__ import annotations

from flask import Blueprint, render_template

from src.core.sites.service import list_sites

public_bp = Blueprint("public_sites", __name__, url_prefix="/sites")


@public_bp.get("/public")
def show_public_sites():
    """Filtro los sitios visibles y los muestro en la vista pública."""

    visible_sites = [site for site in list_sites() if site.get("is_visible")]
    for site in visible_sites:
        status = site.get("conservation_status")
        if hasattr(status, "value"):
            site["conservation_status"] = status.value
        category = site.get("category")
        if hasattr(category, "value"):
            site["category"] = category.value
    return render_template("sites/public.html", sites=visible_sites)
