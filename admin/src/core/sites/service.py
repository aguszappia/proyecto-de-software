from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from geoalchemy2 import WKTElement
from sqlalchemy import asc, desc, or_
from src.core.pagination import Pagination
from src.core.sites.models import Historic_Site, SiteTag, ConservationStatus, SiteCategory
from src.core.database import db

def list_sites():
    sites = db.session.query(Historic_Site).all()
    return [site.to_dict() for site in sites]

def create_site(**kwargs):
    name = kwargs.get("name")
    short_description = kwargs.get("short_description")
    full_description = kwargs.get("full_description")
    city = kwargs.get("city")
    province = kwargs.get("province")
    lat = kwargs.get("latitude")
    lon = kwargs.get("longitude")
    point = WKTElement(f'POINT({lon} {lat})', srid=4326)
    conservation_status = kwargs.get("conservation_status")
    year = kwargs.get("year")
    category = kwargs.get("category")
    is_visible = kwargs.get("is_visible", False)
    updated_at = datetime.now(timezone.utc)

    new_site = Historic_Site(
        name=name,
        short_description=short_description,
        full_description=full_description,
        city=city,
        province=province,
        location=point,
        conservation_status=conservation_status,
        year=year,
        category=category,
        is_visible=is_visible,
        updated_at=updated_at
    )
    db.session.add(new_site)
    db.session.commit()
    return new_site


def get_site(site_id):
    site = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
    return site.to_dict() if site else None


def update_site(site_id, **kwargs):
    site = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
    if not site:
        return None
    
    if kwargs.get("name"):
        site.name = kwargs.get("name")
    if kwargs.get("short_description"):
        site.short_description = kwargs.get("short_description")
    if kwargs.get("full_description"):
        site.full_description = kwargs.get("full_description")
    if kwargs.get("city"):
        site.city = kwargs.get("city")
    if kwargs.get("province"):
        site.province = kwargs.get("province")
    if kwargs.get("latitude") and kwargs.get("longitude"):
        lat = kwargs.get("latitude")
        lon = kwargs.get("longitude")
        site.location = WKTElement(f'POINT({lon} {lat})', srid=4326)
    if kwargs.get("conservation_status"):
        site.conservation_status = kwargs.get("conservation_status")
    if kwargs.get("year"):
        site.year = kwargs.get("year")
    if kwargs.get("category"):
        site.category = kwargs.get("category")
    if "is_visible" in kwargs:
        site.is_visible = kwargs.get("is_visible")
    
    site.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return site


def delete_site(site_id):
    site = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
    if not site:
        return False
    
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
    session = db.session
    query = session.query(Historic_Site)

    if tag_ids:
        query = query.join(Historic_Site.tags).filter(SiteTag.id.in_(tag_ids))
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

# Tags
def list_tags():
    tags = db.session.query(SiteTag).all()
    return [{"id": tag.id, "name": tag.name} for tag in tags]

def create_tag(name):
    new_tag = SiteTag(name=name)
    db.session.add(new_tag)
    db.session.commit()
    return {"id": new_tag.id, "name": new_tag.name}
