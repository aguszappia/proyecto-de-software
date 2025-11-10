"""Blueprint para la gestión interna de sitios históricos."""

from __future__ import annotations

import csv
import io
import os
from datetime import datetime
from typing import Dict
from uuid import uuid4

from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, session, url_for
from minio.error import S3Error

from src.core.sites.models import ConservationStatus, SiteCategory
from src.core.sites.history_service import list_deleted_sites
from src.core.sites.service import (
    create_site,
    delete_site,
    fetch_sites_for_export,
    get_site,
    search_sites,
    update_site,
)
from src.core.sites.images_service import (
    MAX_IMAGES_PER_SITE,
    SiteImageError,
    create_image as create_site_image,
    delete_image as delete_site_image,
    get_image,
    list_images,
    mark_as_cover,
    move_image as move_site_image,
    update_image as update_site_image,
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
from .sites_utils import PROVINCES, empty_site_form, parse_date

bp = Blueprint("sites", __name__, url_prefix="/sites")

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


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
        create_site(performed_by=session.get("user_id"), **payload)
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
        action_type = "Edición"
        details = "Datos editados"
        if payload.get("tag_ids") != site.get("tag_ids", []):
            action_type = "Cambio de tags"
            details = "Etiquetas editadas"
        elif payload.get("is_visible") != bool(site.get("is_visible", False)):
            action_type = "Cambio de estado"
            details = "Visibilidad editada"

        update_site(
            site_id,
            performed_by=session.get("user_id"),
            action_type=action_type,
            details=details,
            **payload,
        )
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


@bp.get("/<int:site_id>/images")
@require_login
@require_permissions("site_update")
def manage_images(site_id: int):
    """Pantalla principal para administrar imagenes de un ssitio"""
    site = get_site(site_id)
    if not site:
        abort(404)
    images = list_images(site_id)
    return render_template(
        "sites/images.html",
        site=site,
        images=images,
        max_images=MAX_IMAGES_PER_SITE,
        total_images=len(images),
        limit_reached=len(images) >= MAX_IMAGES_PER_SITE,
        allowed_extensions=sorted(ext.upper() for ext in ALLOWED_IMAGE_EXTENSIONS),
        max_file_size=MAX_FILE_SIZE_BYTES,
        max_file_size_mb=MAX_FILE_SIZE_BYTES // (1024 * 1024),
    )


@bp.post("/<int:site_id>/images")
@require_login
@require_permissions("site_update")
def upload_image(site_id: int):
    """Subo imagen a MiniO y la guardo en la bd."""
    site = get_site(site_id)
    if not site:
        abort(404)

    image_file = request.files.get("image_file")
    title = clean_str(request.form.get("title"))
    description = clean_str(request.form.get("description"))
    make_cover = request.form.get("is_cover") == "on"

    errors = []
    if not title:
        errors.append("El título/alt de la imagen es obligatorio.")
    file_errors, extension, size = _validate_image_file(image_file)
    errors.extend(file_errors)

    if errors:
        for error in errors:
            flash(error, "error")
        return _redirect_to_images(site_id)

    object_name = f"sites/{site_id}/{uuid4().hex}.{extension}"
    try:
        public_url = _upload_to_storage(image_file, object_name, size, image_file.mimetype)
    except (S3Error, RuntimeError):
        flash("No se pudo subir el archivo. Reintentá en unos segundos.", "error")
        return _redirect_to_images(site_id)
    except Exception:
        flash("Ocurrió un error inesperado al subir la imagen.", "error")
        return _redirect_to_images(site_id)

    try:
        create_site_image(
            site_id,
            object_name=object_name,
            url=public_url,
            title=title,
            description=description or None,
            make_cover=make_cover,
        )
        flash("Imagen agregada correctamente.", "success")
    except SiteImageError as error:
        _delete_storage_object(object_name)
        flash(str(error), "error")
    except Exception:
        _delete_storage_object(object_name)
        flash("No se pudo guardar la imagen. Intentá nuevamente.", "error")
    return _redirect_to_images(site_id)


@bp.post("/<int:site_id>/images/<int:image_id>/update")
@require_login
@require_permissions("site_update")
def update_image(site_id: int, image_id: int):
    """Permito editar metadatos y reemplazar el archivo de una imagen existente."""
    site = get_site(site_id)
    if not site:
        abort(404)
    image = get_image(image_id)
    if not image or image.site_id != site_id:
        abort(404)

    title = clean_str(request.form.get("title"))
    description = clean_str(request.form.get("description"))
    new_file = request.files.get("image_file")

    errors = []
    if not title:
        errors.append("El título/alt de la imagen es obligatorio.")

    extension = None
    size = None
    if new_file and new_file.filename:
        file_errors, extension, size = _validate_image_file(new_file)
        errors.extend(file_errors)

    if errors:
        for error in errors:
            flash(error, "error")
        return _redirect_to_images(site_id)

    new_object_name = None
    new_url = None
    uploaded_object = None
    old_object_name = None

    if new_file and new_file.filename:
        new_object_name = f"sites/{site_id}/{uuid4().hex}.{extension}"
        try:
            new_url = _upload_to_storage(new_file, new_object_name, size, new_file.mimetype)
            uploaded_object = new_object_name
            old_object_name = image.object_name
        except (S3Error, RuntimeError):
            flash("No se pudo reemplazar el archivo. Intentá nuevamente.", "error")
            return _redirect_to_images(site_id)
        except Exception:
            flash("Ocurrió un error inesperado al subir la nueva imagen.", "error")
            return _redirect_to_images(site_id)

    try:
        updated = update_site_image(
            image_id,
            title=title,
            description=description or None,
            new_object_name=new_object_name,
            new_url=new_url,
        )
        if not updated:
            flash("No se encontró la imagen solicitada.", "error")
            if uploaded_object:
                _delete_storage_object(uploaded_object)
            abort(404)
        flash("Cambios guardados correctamente.", "success")
        if uploaded_object and old_object_name:
            _delete_storage_object(old_object_name)
    except Exception:
        if uploaded_object:
            _delete_storage_object(uploaded_object)
        flash("No se pudo actualizar la imagen.", "error")
    return _redirect_to_images(site_id)


@bp.post("/<int:site_id>/images/<int:image_id>/cover")
@require_login
@require_permissions("site_update")
def set_cover_image(site_id: int, image_id: int):
    """Marco imagen existente como portada del sitil"""
    site = get_site(site_id)
    if not site:
        abort(404)
    image = get_image(image_id)
    if not image or image.site_id != site_id:
        abort(404)
    updated = mark_as_cover(image_id)
    if not updated:
        flash("No se pudo actualizar la portada del sitio.", "error")
    else:
        flash("Actualizaste la portada correctamente.", "success")
    return _redirect_to_images(site_id)


@bp.post("/<int:site_id>/images/<int:image_id>/delete")
@require_login
@require_permissions("site_update")
def delete_image(site_id: int, image_id: int):
    """Elimino una imagen del sitio siempre que no sea la portada"""
    site = get_site(site_id)
    if not site:
        abort(404)
    image = get_image(image_id)
    if not image or image.site_id != site_id:
        abort(404)
    object_name = image.object_name
    try:
        delete_site_image(image_id)
        flash("Imagen eliminada correctamente.", "success")
        _delete_storage_object(object_name)
    except SiteImageError as error:
        flash(str(error), "error")
    except Exception:
        flash("No se pudo eliminar la imagen. Intentá nuevamente.", "error")
    return _redirect_to_images(site_id)


@bp.post("/<int:site_id>/images/<int:image_id>/move")
@require_login
@require_permissions("site_update")
def move_image(site_id: int, image_id: int):
    """Reordeno las imágenes moviendo una posición hacia arriba o abajo."""
    direction = (request.form.get("direction") or "").lower()
    if direction not in {"up", "down"}:
        flash("Acción no válida para ordenar las imágenes.", "error")
        return _redirect_to_images(site_id)
    site = get_site(site_id)
    if not site:
        abort(404)
    image = get_image(image_id)
    if not image or image.site_id != site_id:
        abort(404)
    moved = move_site_image(image_id, direction)
    if moved:
        flash("Orden actualizado.", "success")
    else:
        flash("No se pudo mover la imagen solicitada.", "error")
    return _redirect_to_images(site_id)


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


def _redirect_to_images(site_id: int):
    """Atajo para volver a la pantalla de imágenes"""
    return redirect(url_for("sites.manage_images", site_id=site_id))


def _validate_image_file(file_storage):
    """Verifico formato y tamaño y devuelvo (errores, extensión, tamaño)."""
    errors = []
    if not file_storage or not getattr(file_storage, "filename", ""):
        errors.append("Seleccioná un archivo de imagen.")
        return errors, None, 0

    filename = (file_storage.filename or "").strip()
    if not filename:
        errors.append("Seleccioná un archivo de imagen.")
        return errors, None, 0

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        errors.append("Formato no permitido. Usá JPG, PNG o WEBP.")

    size = _get_file_size(file_storage)
    if size <= 0:
        errors.append("El archivo está vacío.")
    if size > MAX_FILE_SIZE_BYTES:
        errors.append("El archivo supera el límite de 5 MB.")

    return errors, extension, size


def _get_file_size(file_storage) -> int:
    """Calculo el tamaño en bytes sin perder el puntero original"""
    stream = getattr(file_storage, "stream", None)
    if not stream:
        return 0
    current_pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0, os.SEEK_SET)
    try:
        stream.seek(current_pos, os.SEEK_SET)
    except (OSError, ValueError):
        stream.seek(0, os.SEEK_SET)
    return size


def _upload_to_storage(file_storage, object_name: str, size: int, content_type: str | None) -> str:
    """Sube archivo a Minio y devuelvo la URL pública"""
    if size <= 0:
        raise RuntimeError("El archivo está vacío.")
    client = getattr(current_app, "storage", None)
    bucket = current_app.config.get("MINIO_BUCKET")
    if not client or not bucket:
        raise RuntimeError("El servicio de almacenamiento no está configurado.")
    stream = getattr(file_storage, "stream", None)
    if not stream:
        raise RuntimeError("No se pudo acceder al contenido del archivo.")
    stream.seek(0)
    client.put_object(
        bucket,
        object_name,
        stream,
        length=size,
        content_type=content_type or "application/octet-stream",
    )
    return _build_public_url(object_name)


def _delete_storage_object(object_name: str) -> None:
    """Borro el objeto en Minio, ignorando errores"""
    if not object_name:
        return
    client = getattr(current_app, "storage", None)
    bucket = current_app.config.get("MINIO_BUCKET")
    if not client or not bucket:
        return
    try:
        client.remove_object(bucket, object_name)
    except (S3Error, Exception):
        return


def _build_public_url(object_name: str) -> str:
    """Construyo la URL pública a partir de la configuración."""
    bucket = current_app.config.get("MINIO_BUCKET")
    if not bucket:
        raise RuntimeError("El bucket de MinIO no está configurado.")
    server = current_app.config.get("MINIO_SERVER", "").rstrip("/")
    secure = bool(current_app.config.get("MINIO_SECURE"))
    if server.startswith(("http://", "https://")):
        base = server.rstrip("/")
    else:
        scheme = "https" if secure else "http"
        base = f"{scheme}://{server}".rstrip("/")
    return f"{base}/{bucket}/{object_name}"