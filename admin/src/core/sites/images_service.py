"""Operaciones de negocio para manejar las imágenes de los sitios."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func

from src.core.database import db
from src.core.sites.history_service import record_event
from src.core.sites.models import SiteImage

MAX_IMAGES_PER_SITE = 10

class SiteImageError(ValueError):
    """Errores controlados para informar a la capa web."""


def list_images(site_id: int) -> List[SiteImage]:
    """Devuelvo las imágenes ordenadas por posición."""
    return (
        db.session.query(SiteImage)
        .filter(SiteImage.site_id == site_id)
        .order_by(SiteImage.order_index.asc(), SiteImage.created_at.asc(), SiteImage.id.asc())
        .all()
    )


def count_images(site_id: int) -> int:
    """Cantidad de imágenes asignadas a un sitio."""
    return (
        db.session.query(func.count(SiteImage.id))
        .filter(SiteImage.site_id == site_id)
        .scalar()
        or 0
    )


def get_image(image_id: int) -> Optional[SiteImage]:
    """Busco una imagen por id."""
    return db.session.query(SiteImage).filter(SiteImage.id == image_id).first()


def create_image(
    site_id: int,
    *,
    object_name: str,
    url: str,
    title: str,
    description: Optional[str] = None,
    make_cover: bool = False,
    performed_by: Optional[int] = None,
) -> SiteImage:
    """Agrego una nueva imagen respetando max y la portada."""
    current_total = count_images(site_id)
    if current_total >= MAX_IMAGES_PER_SITE:
        raise SiteImageError("Se alcanzó el máximo de 10 imágenes permitidas para este sitio.")

    last_order = (
        db.session.query(func.max(SiteImage.order_index))
        .filter(SiteImage.site_id == site_id)
        .scalar()
        or 0
    )
    should_be_cover = make_cover or not _has_cover(site_id)
    image = SiteImage(
        site_id=site_id,
        object_name=object_name,
        url=url,
        title=title,
        description=description or None,
        order_index=last_order + 1,
        is_cover=should_be_cover,
    )
    db.session.add(image)
    db.session.flush()
    if should_be_cover:
        _clear_cover_flags(site_id, keep_id=image.id)
        image.is_cover = True
    db.session.commit()
    record_event(
        site_id=site_id,
        user_id=performed_by,
        action_type="Cambio de imágenes",
        details=f"Imagen agregada: {object_name}",
    )
    return image


def update_image(
    image_id: int,
    *,
    title: str,
    description: Optional[str] = None,
    new_object_name: Optional[str] = None,
    new_url: Optional[str] = None,
    performed_by: Optional[int] = None,
) -> Optional[SiteImage]:
    """Actualizo los metadatos de una imagen y reemplazo archivo si corresponde."""
    image = get_image(image_id)
    if not image:
        return None
    image.title = title
    image.description = description or None
    if new_object_name and new_url:
        image.object_name = new_object_name
        image.url = new_url
    db.session.commit()
    record_event(
        site_id=image.site_id,
        user_id=performed_by,
        action_type="Cambio de imágenes",
        details="Imagen editada",
    )
    return image


def mark_as_cover(image_id: int, *, performed_by: Optional[int] = None) -> Optional[SiteImage]:
    """Marco una imagen como portada única para su sitio."""
    image = get_image(image_id)
    if not image:
        return None
    _clear_cover_flags(image.site_id, keep_id=image.id)
    image.is_cover = True
    db.session.commit()
    record_event(
        site_id=image.site_id,
        user_id=performed_by,
        action_type="Cambio de imágenes",
        details="Portada actualizada",
    )
    return image


def delete_image(image_id: int, *, performed_by: Optional[int] = None) -> bool:
    """Elimino una imagen si no es la portada."""
    image = get_image(image_id)
    if not image:
        return False
    if image.is_cover:
        total = count_images(image.site_id)
        if total > 1:
            raise SiteImageError("No podés eliminar la portada. Elegí otra portada antes.")
    site_id = image.site_id # guardo el site de la imagen a eliminar
    db.session.delete(image)
    db.session.flush()
    _resequence_orders(site_id) # reordeno imágenes restantes
    db.session.commit()
    record_event(
        site_id=site_id,
        user_id=performed_by,
        action_type="Cambio de imágenes",
        details="Imagen eliminada",
    )
    return True


def move_image(image_id: int, direction: str, *, performed_by: Optional[int] = None) -> Optional[SiteImage]:
    """Desplazo una imagen hacia arriba o abajo en el orden."""
    image = get_image(image_id)
    if not image:
        return None
    direction = (direction or "").lower()
    ordered = list_images(image.site_id)
    if not ordered:
        return None
    positions = {item.id: idx for idx, item in enumerate(ordered)}
    current_idx = positions.get(image_id)
    if current_idx is None:
        return None

    if direction == "up" and current_idx > 0:
        swap_idx = current_idx - 1
    elif direction == "down" and current_idx < len(ordered) - 1:
        swap_idx = current_idx + 1
    else:
        return None

    target = ordered[swap_idx]
    current_order = image.order_index
    target_order = target.order_index

    image.order_index = -1
    db.session.flush()

    target.order_index = current_order
    db.session.flush()

    image.order_index = target_order
    db.session.commit()
    record_event(
        site_id=image.site_id,
        user_id=performed_by,
        action_type="Cambio de imágenes",
        details="Orden de imágenes actualizado",
    )
    return image


def _has_cover(site_id: int) -> bool:
    """Verifico si existe una portada asignada."""
    return (
        db.session.query(SiteImage.id)
        .filter(SiteImage.site_id == site_id, SiteImage.is_cover.is_(True))
        .first()
        is not None
    )


def _clear_cover_flags(site_id: int, *, keep_id: Optional[int] = None) -> None:
    """Desactivo banderas de portada excepto la indicada."""
    query = db.session.query(SiteImage).filter(SiteImage.site_id == site_id, SiteImage.is_cover.is_(True))
    if keep_id is not None:
        query = query.filter(SiteImage.id != keep_id)
    query.update({SiteImage.is_cover: False}, synchronize_session=False)


def _resequence_orders(site_id: int) -> None:
    """Normalizo el orden consecutivo de las imágenes."""
    ordered = (
        db.session.query(SiteImage)
        .filter(SiteImage.site_id == site_id)
        .order_by(SiteImage.order_index.asc(), SiteImage.created_at.asc(), SiteImage.id.asc())
        .all()
    )
    for position, image in enumerate(ordered, start=1):
        image.order_index = -position
    db.session.flush()
    for position, image in enumerate(ordered, start=1):
        image.order_index = position
