"""Blueprint para gestionar las imágenes asociadas a un sitio."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from minio.error import S3Error

from src.core.sites.images_service import (
    MAX_IMAGES_PER_SITE,
    SiteImageError,
    create_image as create_site_image,
    delete_image as delete_site_image,
    list_images,
    mark_as_cover,
    move_image as move_site_image,
    update_image as update_site_image,
)
from src.web.controllers.auth import require_login, require_permissions
from .images_helpers import (
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    delete_storage_object,
    extract_image_form,
    get_image_or_404,
    get_site_or_404,
    upload_file,
)

bp = Blueprint("site_images", __name__, url_prefix="/sites/<int:site_id>/images")


@bp.get("/")
@require_login
@require_permissions("site_update")
def manage(site_id: int):
    site = get_site_or_404(site_id)
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


@bp.post("/")
@require_login
@require_permissions("site_update")
def upload(site_id: int):
    get_site_or_404(site_id)
    title, description, file_data, errors = extract_image_form(request, file_required=True)
    make_cover = request.form.get("is_cover") == "on"

    if errors:
        _flash_errors(errors)
        return _redirect(site_id)

    try:
        object_name, public_url = upload_file(site_id, file_data)
    except (S3Error, RuntimeError):
        flash("No se pudo subir el archivo. Reintentá en unos segundos.", "error")
        return _redirect(site_id)
    except Exception:
        flash("Ocurrió un error inesperado al subir la imagen.", "error")
        return _redirect(site_id)

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
        delete_storage_object(object_name)
        flash(str(error), "error")
    except Exception:
        delete_storage_object(object_name)
        flash("No se pudo guardar la imagen. Intentá nuevamente.", "error")

    return _redirect(site_id)


@bp.post("/<int:image_id>/update")
@require_login
@require_permissions("site_update")
def update(site_id: int, image_id: int):
    image = get_image_or_404(site_id, image_id)
    title, description, file_data, errors = extract_image_form(request, file_required=False)

    if errors:
        _flash_errors(errors)
        return _redirect(site_id)

    new_object_name = None
    new_url = None
    old_object_name = None

    if file_data:
        try:
            new_object_name, new_url = upload_file(site_id, file_data)
            old_object_name = image.object_name
        except (S3Error, RuntimeError):
            flash("No se pudo reemplazar el archivo. Intentá nuevamente.", "error")
            return _redirect(site_id)
        except Exception:
            flash("Ocurrió un error inesperado al subir la nueva imagen.", "error")
            return _redirect(site_id)

    try:
        update_site_image(
            image_id,
            title=title,
            description=description or None,
            new_object_name=new_object_name,
            new_url=new_url,
        )
        flash("Cambios guardados correctamente.", "success")
        if new_object_name and old_object_name:
            delete_storage_object(old_object_name)
    except Exception:
        if new_object_name:
            delete_storage_object(new_object_name)
        flash("No se pudo actualizar la imagen.", "error")

    return _redirect(site_id)


@bp.post("/<int:image_id>/cover")
@require_login
@require_permissions("site_update")
def set_cover(site_id: int, image_id: int):
    get_image_or_404(site_id, image_id)
    updated = mark_as_cover(image_id)
    if updated:
        flash("Actualizaste la portada correctamente.", "success")
    else:
        flash("No se pudo actualizar la portada del sitio.", "error")
    return _redirect(site_id)


@bp.post("/<int:image_id>/delete")
@require_login
@require_permissions("site_update")
def delete(site_id: int, image_id: int):
    image = get_image_or_404(site_id, image_id)
    try:
        delete_site_image(image_id)
        flash("Imagen eliminada correctamente.", "success")
        delete_storage_object(image.object_name)
    except SiteImageError as error:
        flash(str(error), "error")
    except Exception:
        flash("No se pudo eliminar la imagen. Intentá nuevamente.", "error")
    return _redirect(site_id)


@bp.post("/<int:image_id>/move")
@require_login
@require_permissions("site_update")
def move(site_id: int, image_id: int):
    direction = (request.form.get("direction") or "").lower()
    if direction not in {"up", "down"}:
        flash("Acción no válida para ordenar las imágenes.", "error")
        return _redirect(site_id)
    get_image_or_404(site_id, image_id)
    moved = move_site_image(image_id, direction)
    if moved:
        flash("Orden actualizado.", "success")
    else:
        flash("No se pudo mover la imagen solicitada.", "error")
    return _redirect(site_id)


def _redirect(site_id: int):
    return redirect(url_for("site_images.manage", site_id=site_id))


def _flash_errors(errors):
    for error in errors:
        flash(error, "error")
