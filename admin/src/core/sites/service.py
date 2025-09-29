from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from geoalchemy2 import WKTElement
from src.core.sites.models import Historic_Site, SiteTag, ConservationStatus, SiteCategory
from src.core.sites.crud import SiteCRUD, TagCRUD
from src.core.sites.schemas import SiteCreateSchema, SiteUpdateSchema, TagCreateSchema
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

# Tags
def list_tags():
    tags = db.session.query(SiteTag).all()
    return [{"id": tag.id, "name": tag.name} for tag in tags]

def create_tag(name):
    new_tag = SiteTag(name=name)
    db.session.add(new_tag)
    db.session.commit()
    return {"id": new_tag.id, "name": new_tag.name}