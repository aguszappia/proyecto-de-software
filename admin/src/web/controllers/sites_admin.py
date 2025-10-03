"""Blueprint para la gestión interna de sitios históricos."""

from __future__ import annotations

from typing import Dict, List

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from src.core.sites.models import ConservationStatus, SiteCategory
from src.core.sites.service import (create_site, delete_site, get_site, list_tags, search_sites, update_site)
from src.web.controllers.auth import require_login, require_roles
# Archivo helep
from src.web.controllers.sites_utils import (
    PROVINCES,
    build_site_payload,
    clean_str,
    empty_site_form,
    parse_date,
    parse_enum,
    parse_tag_ids,
    safe_int,
)

bp = Blueprint("sites", __name__, url_prefix="/sites")


@bp.get("/")
@require_login
@require_roles("editor", "admin", "sysadmin")
def index():
    """Lista los sitios con filtros y paginación para el panel de gestion"""

    args = request.args
    tag_ids = parse_tag_ids(args.getlist("tags"))
    only_visible = args.get("is_visible") == "on"

    filters = {
        "city": clean_str(args.get("city")),
        "province": clean_str(args.get("province")),
        "q": clean_str(args.get("q")),
        "conservation_status": clean_str(args.get("conservation_status")),
        "created_from": clean_str(args.get("created_from")),
        "created_to": clean_str(args.get("created_to")),
        "sort_by": clean_str(args.get("sort_by")) or "created_at",
        "sort_dir": clean_str(args.get("sort_dir")) or "desc",
        "tags": tag_ids,
        "is_visible": only_visible,
    }

    page = safe_int(args.get("page")) or 1
    created_from = parse_date(filters["created_from"])
    created_to = parse_date(filters["created_to"], end_of_day=True)
    status_enum = parse_enum(filters["conservation_status"], ConservationStatus)

    pagination = search_sites(
        city=filters["city"] or None,
        province=filters["province"] or None,
        tag_ids=tag_ids or None,
        conservation_status=status_enum,
        created_from=created_from,
        created_to=created_to,
        is_visible=True if only_visible else None,
        q=filters["q"] or None,
        sort_by=filters["sort_by"],
        sort_dir=filters["sort_dir"],
        page=page,
        per_page=25,
    )

    params: Dict[str, object] = {}
    for key in ("city", "province", "q", "conservation_status", "created_from", "created_to", "sort_by", "sort_dir"):
        if filters[key]:
            params[key] = filters[key]
    if tag_ids:
        params["tags"] = tag_ids
    if only_visible:
        params["is_visible"] = "on"

    prev_url = url_for("sites.index", page=pagination.page - 1, **params) if pagination.page > 1 else None
    next_url = (
        url_for("sites.index", page=pagination.page + 1, **params)
        if pagination.page < pagination.pages
        else None
    )

    return render_template(
        "sites/index.html",
        pagination=pagination,
        filters=filters,
        tags=list_tags(),
        provinces=PROVINCES,
        conservation_statuses=list(ConservationStatus),
        prev_url=prev_url,
        next_url=next_url,
    )


@bp.route("/new", methods=["GET", "POST"])
@require_login
@require_roles("editor", "admin", "sysadmin")
def create():
    """Funcion para crear un nuevo sitio histórico
        Si el HTTP es GET renderiza el template de formulario vacío
        Si el HTTP es POST procesa el formulario y crea el sitio histórico
    """

    if request.method == "POST":
        payload, form_values, errors = build_site_payload(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "sites/form.html",
                form_values=form_values,
                tags=list_tags(),
                conservation_statuses=list(ConservationStatus),
                categories=list(SiteCategory),
                provinces=PROVINCES,
                is_edit=False,
            )
        create_site(**payload)
        flash("Sitio histórico creado correctamente.", "success")
        return redirect(url_for("sites.index"))

    return render_template(
        "sites/form.html",
        form_values=empty_site_form(),
        tags=list_tags(),
        conservation_statuses=list(ConservationStatus),
        categories=list(SiteCategory),
        provinces=PROVINCES,
        is_edit=False,
    )


@bp.route("/<int:site_id>/edit", methods=["GET", "POST"])
@require_login
@require_roles("editor", "admin", "sysadmin")
def edit(site_id: int):
    """Edita un sitio histórico existente
        Si el HTTP es GET renderiza el template de formulario vacío
        Si el HTTP es POST procesa el formulario y crea el sitio histórico
    """

    site = get_site(site_id)
    if not site: # control si no existe 
        abort(404)

    if request.method == "POST":
        payload, form_values, errors = build_site_payload(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "sites/form.html",
                form_values=form_values,
                tags=list_tags(),
                conservation_statuses=list(ConservationStatus),
                categories=list(SiteCategory),
                provinces=PROVINCES,
                is_edit=True,
                site_id=site_id,
            )
        update_site(site_id, **payload)
        flash("Sitio histórico actualizado correctamente.", "success")
        return redirect(url_for("sites.index"))

    form_values = {
        "name": site.get("name", ""),
        "short_description": site.get("short_description", ""),
        "full_description": site.get("full_description", ""),
        "city": site.get("city", ""),
        "province": site.get("province", ""),
        "conservation_status": (
            site.get("conservation_status").value
            if hasattr(site.get("conservation_status"), "value")
            else site.get("conservation_status", "")
        ),
        "category": (
            site.get("category").value
            if hasattr(site.get("category"), "value")
            else site.get("category", "")
        ),
        "inaguration_year": str(site.get("inaguration_year") or ""),
        "latitude": str(site.get("latitude") or ""),
        "longitude": str(site.get("longitude") or ""),
        "is_visible": bool(site.get("is_visible", False)),
        "tag_ids": site.get("tag_ids", []),
    }

    return render_template(
        "sites/form.html",
        form_values=form_values,
        tags=list_tags(),
        conservation_statuses=list(ConservationStatus),
        categories=list(SiteCategory),
        provinces=PROVINCES,
        is_edit=True,
        site_id=site_id,
    )


@bp.post("/<int:site_id>/delete")
@require_login
@require_roles("admin", "sysadmin")
def remove(site_id: int):
    """Elimina un sitio histórico (solo para admin o sysadmin)"""

    if delete_site(site_id):
        flash("Sitio histórico eliminado correctamente.", "success")
    else:
        flash("No se encontró el sitio histórico solicitado.", "error")
    return redirect(url_for("sites.index"))
