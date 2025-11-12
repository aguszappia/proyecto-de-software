"""Funciones auxiliares para el manejo de imágenes y archivos."""

from __future__ import annotations

from typing import Optional, Tuple
import os
from uuid import uuid4

from flask import abort, current_app
from minio.error import S3Error

from src.core.sites.images_service import get_image
from src.core.sites.service import get_site

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def get_site_or_404(site_id: int):
    site = get_site(site_id)
    if not site:
        abort(404)
    return site


def get_image_or_404(site_id: int, image_id: int):
    image = get_image(image_id)
    if not image or image.site_id != site_id:
        abort(404)
    return image


def extract_image_form(request, *, file_required: bool):
    """Obtengo campos comunes del formulario de imágenes."""
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    file_storage = request.files.get("image_file")

    errors = []
    if not title:
        errors.append("El título/alt de la imagen es obligatorio.")

    file_data: Optional[Tuple] = None
    has_file = bool(file_storage and getattr(file_storage, "filename", "").strip())
    if file_required or has_file:
        file_errors, extension, size = _validate_image_file(file_storage)
        errors.extend(file_errors)
        if not file_errors:
            file_data = (file_storage, extension, size)

    return title, description, file_data, errors


def upload_file(site_id: int, file_data):
    """Subo el archivo recibido y devuelvo (object_name, url)."""
    if not file_data:
        return None, None
    file_storage, extension, size = file_data
    object_name = f"sites/{site_id}/{uuid4().hex}.{extension}"
    public_url = _upload_to_storage(file_storage, object_name, size, file_storage.mimetype)
    return object_name, public_url


def delete_storage_object(object_name: str) -> None:
    """Borro el objeto en MinIO, ignorando errores silenciosamente."""
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
    """Calculo el tamaño en bytes sin perder el puntero original."""
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
    """Subo el archivo a MinIO y devuelvo la URL pública."""
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
