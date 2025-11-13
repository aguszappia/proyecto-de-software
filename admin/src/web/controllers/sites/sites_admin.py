"""Blueprint para la gestión interna de sitios históricos."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Dict

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from src.core.sites import images_service
from src.core.sites.history_service import list_deleted_sites
from src.core.sites.images_service import SiteImageError
from src.core.sites.models import ConservationStatus, SiteCategory
from src.core.sites.service import (
    create_site,
    delete_site,
    fetch_sites_for_export,
    get_site,
    search_sites,
    update_site,
)
from src.core.sites.tags_service import list_tags
from src.web.controllers.auth import require_login, require_permissions
# Archivo helper - ruta relativa para evitar imports circulares
from src.core.sites.validators import (
    build_site_payload,
    clean_str,
    parse_enum,
    parse_tag_ids,
    safe_int,
)
from src.core.database import db
from src.web.controllers.sites import images_helpers
from .sites_utils import PROVINCES, empty_site_form, parse_date

bp = Blueprint("sites", __name__, url_prefix="/sites")



@bp.get("/")
@require_login
@require_permissions("site_index")
def index():
    """Armo el listado de sitios con filtros, paginado y enlaces de navegación."""

    args = request.args
    tag_ids = parse_tag_ids(args.getlist("tags"))
    visibility_raw = clean_str(args.get("is_visible")) or ""
    match_visibility = None
    if visibility_raw == "true":
        match_visibility = True
    elif visibility_raw == "false":
        match_visibility = False

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
        "is_visible": visibility_raw,
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
        is_visible=match_visibility,
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
    if visibility_raw:
        params["is_visible"] = visibility_raw

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
@require_permissions("site_new")
def create():
    """Creo un sitio nuevo o muestro el formulario con errores."""

    if request.method == "POST":
        payload, form_values, errors = build_site_payload(request.form)
        form_values["cover_image_preview"] = ""
        cover_data = None
        cover_file = request.files.get("cover_image")
        has_file = bool(cover_file and getattr(cover_file, "filename", "").strip())
        if not has_file:
            errors.append("Subí una imagen representativa del sitio.")
        else:
            image_errors, extension, size = images_helpers._validate_image_file(cover_file)
            if image_errors:
                errors.extend(image_errors)
            else:
                cover_data = (cover_file, extension, size)
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
        try:
            new_site = create_site(performed_by=session.get("user_id"), **payload)
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe un sitio histórico con ese nombre. Elegí otro antes de guardar.", "error")
            return render_template(
                "sites/form.html",
                form_values=form_values,
                tags=list_tags(),
                conservation_statuses=list(ConservationStatus),
                categories=list(SiteCategory),
                provinces=PROVINCES,
                is_edit=False,
            )
        if cover_data:
            try:
                object_name, url = images_helpers.upload_file(new_site.id, cover_data)
                images_service.create_image(
                    new_site.id,
                    object_name=object_name,
                    url=url,
                    title=payload["name"],
                    description=None,
                    make_cover=True,
                )
            except (SiteImageError, Exception) as error:
                flash(f"La imagen no pudo subirse automáticamente: {error}", "error")
                flash("Podés volver a intentarlo luego desde la sección de imágenes.", "warning")
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
@require_permissions("site_update")
def edit(site_id: int):
    """Actualizo un sitio existente ajustando historial según los cambios."""

    site = get_site(site_id)
    if not site: # control si no existe 
        abort(404)
    cover_preview = site.get("cover_image_url") or ""

    if request.method == "POST":
        payload, form_values, errors = build_site_payload(request.form)
        form_values["cover_image_preview"] = cover_preview
        cover_data = None
        cover_file = request.files.get("cover_image")
        has_file = bool(cover_file and getattr(cover_file, "filename", "").strip())
        if has_file:
            image_errors, extension, size = images_helpers._validate_image_file(cover_file)
            if image_errors:
                errors.extend(image_errors)
            else:
                cover_data = (cover_file, extension, size)
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
        action_type = "Edición"
        details = "Datos editados"
        if payload.get("tag_ids") != site.get("tag_ids", []):
            action_type = "Cambio de tags"
            details = "Etiquetas editadas"
        elif payload.get("is_visible") != bool(site.get("is_visible", False)):
            action_type = "Cambio de estado"
            details = "Visibilidad editada"

        try:
            update_site(
                site_id,
                performed_by=session.get("user_id"),
                action_type=action_type,
                details=details,
                **payload,
            )
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe un sitio histórico con ese nombre. Elegí otro antes de guardar.", "error")
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
        if cover_data:
            try:
                object_name, url = images_helpers.upload_file(site_id, cover_data)
                images_service.create_image(
                    site_id,
                    object_name=object_name,
                    url=url,
                    title=payload["name"],
                    description=None,
                    make_cover=True,
                )
                flash("Se actualizó la portada del sitio.", "success")
            except (SiteImageError, Exception) as error:
                flash(f"La imagen no pudo subirse automáticamente: {error}", "error")
                flash("Podés volver a intentarlo desde la sección de imágenes.", "warning")
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
        "cover_image_preview": cover_preview,
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
@require_permissions("site_destroy")
def remove(site_id: int):
    """Elimino el sitio y notifico según el resultado."""

    if delete_site(site_id, performed_by=session.get("user_id")):
        flash("Sitio histórico eliminado correctamente.", "success")
    else:
        flash("No se encontró el sitio histórico solicitado.", "error")
    return redirect(url_for("sites.index"))


@bp.get("/deleted")
@require_login
@require_permissions("site_index")
def deleted_list():
    """Muestro el historial de sitios que fueron eliminados."""

    deleted_sites = list_deleted_sites()
    return render_template(
        "sites/deleted.html",
        deleted_sites=deleted_sites,
    )


@bp.get("/export")
@require_login
@require_permissions("site_export")
def export_sites():
    """Genero el CSV con los sitios filtrados y lo envío como descarga."""
    args = request.args
    tag_ids = parse_tag_ids(args.getlist("tags"))
    visibility_raw = clean_str(args.get("is_visible")) or ""
    match_visibility = None
    if visibility_raw == "true":
        match_visibility = True
    elif visibility_raw == "false":
        match_visibility = False

    filters = {
        "city": clean_str(args.get("city")),
        "province": clean_str(args.get("province")),
        "q": clean_str(args.get("q")),
        "conservation_status": clean_str(args.get("conservation_status")),
        "created_from": clean_str(args.get("created_from")),
        "created_to": clean_str(args.get("created_to")),
        "sort_by": clean_str(args.get("sort_by")) or "created_at",
        "sort_dir": clean_str(args.get("sort_dir")) or "desc",
        "is_visible": visibility_raw,
    }

    created_from = parse_date(filters["created_from"])
    created_to = parse_date(filters["created_to"], end_of_day=True)
    status_enum = parse_enum(filters["conservation_status"], ConservationStatus)

    sites = fetch_sites_for_export(
        city=filters["city"] or None,
        province=filters["province"] or None,
        tag_ids=tag_ids or None,
        conservation_status=status_enum,
        created_from=created_from,
        created_to=created_to,
        is_visible=match_visibility,
        q=filters["q"] or None,
        sort_by=filters["sort_by"],
        sort_dir=filters["sort_dir"],
    )

    params: Dict[str, object] = {}
    for key in ("city", "province", "q", "conservation_status", "created_from", "created_to", "sort_by", "sort_dir"):
        if filters[key]:
            params[key] = filters[key]
    if tag_ids:
        params["tags"] = tag_ids
    if visibility_raw:
        params["is_visible"] = visibility_raw

    if not sites:
        flash("No hay datos para exportar con los filtros seleccionados.", "error")
        return redirect(url_for("sites.index", **params))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Nombre",
            "Descripción breve",
            "Ciudad",
            "Provincia",
            "Estado de conservación",
            "Fecha de registro",
            "Latitud",
            "Longitud",
            "Tags",
        ]
    )

    for site in sites:
        status_value = site.conservation_status.value if hasattr(site.conservation_status, "value") else str(site.conservation_status)
        created_value = site.created_at.strftime("%Y-%m-%d %H:%M") if site.created_at else ""

        lat_value = ""
        if getattr(site, "latitude", None) is not None:
            lat_value = f"{site.latitude:.6f}"

        lon_value = ""
        if getattr(site, "longitude", None) is not None:
            lon_value = f"{site.longitude:.6f}"

        tag_names = ", ".join(sorted(tag.name for tag in getattr(site, "tags", []) if tag and tag.name)) or "-"

        writer.writerow(
            [
                site.id,
                site.name,
                site.short_description,
                site.city,
                site.province,
                status_value,
                created_value,
                lat_value,
                lon_value,
                tag_names,
            ]
        )

    csv_content = output.getvalue()
    output.close()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"sitios_{timestamp}.csv"

    response = Response(csv_content, mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
