"""Servicios CRUD y búsquedas para sitios históricos."""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from geoalchemy2 import WKTElement
from geoalchemy2 import functions as geofunctions, elements as geoelements, Geography
from sqlalchemy import asc, desc, or_
from src.core.pagination import Pagination
from src.core.sites.models import (
    Historic_Site,
    SiteTag,
    ConservationStatus,
    SiteCategory,
    SiteFavorite,
)
from src.core.sites.history_service import record_event
from src.core.database import db

def list_sites():
    """Devuelvo todos los sitios convertidos a diccionarios."""
    sites = db.session.query(Historic_Site).all()
    return [site.to_dict() for site in sites]

def create_site(**kwargs):
    """Creo un sitio con su ubicación y registro el evento de creación."""
    performed_by = kwargs.pop("performed_by", None)
    name = kwargs.get("name")
    short_description = kwargs.get("short_description")
    full_description = kwargs.get("full_description")
    city = kwargs.get("city")
    province = kwargs.get("province")
    lat = kwargs.get("latitude")
    lon = kwargs.get("longitude")
    point = WKTElement(f'POINT({lon} {lat})', srid=4326)
    conservation_status = kwargs.get("conservation_status")
    inaguration_year = kwargs.get("inaguration_year")
    category = kwargs.get("category")
    is_visible = kwargs.get("is_visible", False)
    updated_at = datetime.now(timezone.utc)
    tag_ids = kwargs.get("tag_ids") or []

    new_site = Historic_Site(
        name=name,
        short_description=short_description,
        full_description=full_description,
        city=city,
        province=province,
        location=point,
        conservation_status=conservation_status,
        inaguration_year=inaguration_year,
        category=category,
        is_visible=is_visible,
        updated_at=updated_at
    )
    if tag_ids:
        tags = db.session.query(SiteTag).filter(SiteTag.id.in_(tag_ids)).all()
        new_site.tags = tags
    db.session.add(new_site)
    db.session.commit()
    record_event(site_id=new_site.id, user_id=performed_by, action_type="Creación", details="Sitio creado")
    return new_site


def get_site(site_id):
    """Traigo un sitio por id y agrego los ids de tags."""
    site = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
    if not site:
        return None
    data = site.to_dict()
    data["tag_ids"] = [tag.id for tag in site.tags]
    return data


def update_site(site_id, **kwargs):
    """Actualizo los campos permitidos y registro el evento correspondiente."""
    site = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
    if not site:
        return None
    performed_by = kwargs.pop("performed_by", None)
    action_type = kwargs.pop("action_type", "Edición")
    details = kwargs.pop("details", "Datos editados")

    if "name" in kwargs:
        site.name = kwargs.get("name")
    if "short_description" in kwargs:
        site.short_description = kwargs.get("short_description")
    if "full_description" in kwargs:
        site.full_description = kwargs.get("full_description")
    if "city" in kwargs:
        site.city = kwargs.get("city")
    if "province" in kwargs:
        site.province = kwargs.get("province")
    if kwargs.get("latitude") is not None and kwargs.get("longitude") is not None:
        lat = kwargs.get("latitude")
        lon = kwargs.get("longitude")
        site.location = WKTElement(f'POINT({lon} {lat})', srid=4326)
    if "conservation_status" in kwargs and kwargs.get("conservation_status") is not None:
        site.conservation_status = kwargs.get("conservation_status")
    if "inaguration_year" in kwargs:
        site.inaguration_year = kwargs.get("inaguration_year")
    if "category" in kwargs and kwargs.get("category") is not None:
        site.category = kwargs.get("category")
    if "is_visible" in kwargs:
        site.is_visible = kwargs.get("is_visible")
    if "tag_ids" in kwargs:
        tag_ids = kwargs.get("tag_ids") or []
        tags = []
        if tag_ids:
            tags = db.session.query(SiteTag).filter(SiteTag.id.in_(tag_ids)).all()
        site.tags = tags

    site.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    record_event(site_id=site.id, user_id=performed_by, action_type=action_type, details=details)
    return site


def delete_site(site_id, performed_by: Optional[int] = None):
    """Borro el sitio y guardo en historial la metadata de la eliminación."""
    site = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
    if not site:
        return False

    payload = {
        "message": f'Sitio "{site.name}" eliminado',
        "name": site.name,
        "city": site.city,
        "province": site.province,
        "category": site.category.value if isinstance(site.category, SiteCategory) else str(site.category)
        if site.category
        else None,
        "conservation_status": site.conservation_status.value
        if isinstance(site.conservation_status, ConservationStatus)
        else str(site.conservation_status)
        if site.conservation_status
        else None,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }

    record_event(
        site_id=site.id,
        user_id=performed_by,
        action_type="Eliminación",
        details=json.dumps(payload),
    )

    db.session.delete(site)
    db.session.commit()
    return True


def search_sites(
    *,
    city: Optional[str] = None,
    province: Optional[str] = None,
    tag_ids: Optional[List[int]] = None,
    conservation_status: Optional[ConservationStatus] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    is_visible: Optional[bool] = None,
    q: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    per_page: int = 25,
) -> Pagination:
    """Armo el query con filtros, pagino y devuelvo un Pagination de dicts."""
    session = db.session
    query = session.query(Historic_Site)

    if tag_ids:
        for tag_id in tag_ids:
            query = query.filter(Historic_Site.tags.any(SiteTag.id == tag_id))
    if city:
        query = query.filter(Historic_Site.city.ilike(f"%{city}%"))
    if province:
        query = query.filter(Historic_Site.province == province)
    if conservation_status:
        query = query.filter(Historic_Site.conservation_status == conservation_status)
    if created_from:
        query = query.filter(Historic_Site.created_at >= created_from)
    if created_to:
        query = query.filter(Historic_Site.created_at <= created_to)
    if is_visible is not None:
        query = query.filter(Historic_Site.is_visible.is_(is_visible))
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Historic_Site.name.ilike(pattern),
                Historic_Site.short_description.ilike(pattern),
            )
        )

    query = query.distinct()

    total = query.order_by(None).count()

    allowed_sort = {"created_at", "name", "city"}
    sort_by = sort_by if sort_by in allowed_sort else "created_at"
    sort_dir = sort_dir if sort_dir in {"asc", "desc"} else "desc"

    order_column_map = {
        "created_at": Historic_Site.created_at,
        "name": Historic_Site.name,
        "city": Historic_Site.city,
    }
    order_column = order_column_map[sort_by]
    order_fn = asc if sort_dir == "asc" else desc
    query = query.order_by(order_fn(order_column))

    page = max(page, 1)
    per_page = max(1, min(per_page, 25))
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    site_dicts: List[Dict[str, Any]] = []
    for site in items:
        site_dict = site.to_dict()
        status = site_dict.get("conservation_status")
        if isinstance(status, ConservationStatus):
            site_dict["conservation_status"] = status.value
        category = site_dict.get("category")
        if isinstance(category, SiteCategory):
            site_dict["category"] = category.value
        site_dicts.append(site_dict)
    return Pagination(site_dicts, total, page, per_page)


def fetch_sites_for_export(
    *,
    city: Optional[str] = None,
    province: Optional[str] = None,
    tag_ids: Optional[List[int]] = None,
    conservation_status: Optional[ConservationStatus] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    is_visible: Optional[bool] = None,
    q: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> List[Historic_Site]:
    """Obtengo los sitios filtrados listos para exportar a CSV."""
    query = db.session.query(Historic_Site)

    if tag_ids:
        for tag_id in tag_ids:
            query = query.filter(Historic_Site.tags.any(SiteTag.id == tag_id))
    if city:
        query = query.filter(Historic_Site.city.ilike(f"%{city}%"))
    if province:
        query = query.filter(Historic_Site.province == province)
    if conservation_status:
        query = query.filter(Historic_Site.conservation_status == conservation_status)
    if created_from:
        query = query.filter(Historic_Site.created_at >= created_from)
    if created_to:
        query = query.filter(Historic_Site.created_at <= created_to)
    if is_visible is not None:
        query = query.filter(Historic_Site.is_visible.is_(is_visible))
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Historic_Site.name.ilike(pattern),
                Historic_Site.short_description.ilike(pattern),
            )
        )

    allowed_sort = {"created_at", "name", "city"}
    sort_by = sort_by if sort_by in allowed_sort else "created_at"
    sort_dir = sort_dir if sort_dir in {"asc", "desc"} else "desc"

    order_column_map = {
        "created_at": Historic_Site.created_at,
        "name": Historic_Site.name,
        "city": Historic_Site.city,
    }
    order_column = order_column_map[sort_by]
    order_fn = asc if sort_dir == "asc" else desc
    query = query.order_by(order_fn(order_column))

    return query.all()

def get_sites_by_location(lat, lon, redius):
    center = geoelements.WKTElement(f'POINT({lon} {lat})', srid=4326)
    sites = db.session.query(Historic_Site).filter(
        geofunctions.ST_DWithin(Historic_Site.location.cast(Geography), center, redius)
    ).all()
    return [site.to_dict() for site in sites]


def mark_site_favorite(site_id: int, user_id: int) -> bool:
    """Marca un sitio como favorito para el usuario."""
    session = db.session
    site = (
        session.query(Historic_Site.id, Historic_Site.is_visible)
        .filter(Historic_Site.id == site_id)
        .first()
    )
    if not site or not site.is_visible:
        return False

    existing = (
        session.query(SiteFavorite)
        .filter(SiteFavorite.site_id == site_id, SiteFavorite.user_id == user_id)
        .first()
    )
    if existing:
        return True

    session.add(SiteFavorite(site_id=site_id, user_id=user_id))
    session.commit()
    return True


def unmark_site_favorite(site_id: int, user_id: int) -> bool:
    """Elimina el sitio de los favoritos del usuario."""
    session = db.session
    favorite = (
        session.query(SiteFavorite)
        .filter(SiteFavorite.site_id == site_id, SiteFavorite.user_id == user_id)
        .first()
    )
    if not favorite:
        return True
    session.delete(favorite)
    session.commit()
    return True


def list_favorite_site_ids(user_id: int) -> List[int]:
    """Lista los IDs de sitios favoritos del usuario."""
    session = db.session
    rows = session.query(SiteFavorite.site_id).filter(SiteFavorite.user_id == user_id).all()
    return [row[0] for row in rows]


def is_favorite_for_user(site_id: int, user_id: int) -> bool:
    """Indica si un sitio está marcado como favorito por el usuario."""
    session = db.session
    record = (
        session.query(SiteFavorite.id)
        .filter(SiteFavorite.site_id == site_id, SiteFavorite.user_id == user_id)
        .first()
    )
    return record is not None
