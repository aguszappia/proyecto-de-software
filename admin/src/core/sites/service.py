from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import unicodedata
import re

from geoalchemy2 import WKTElement
from sqlalchemy import asc, desc, or_, func
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
    return new_site


def get_site(site_id):
    site = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
    if not site:
        return None
    data = site.to_dict()
    data["tag_ids"] = [tag.id for tag in site.tags]
    return data


def update_site(site_id, **kwargs):
    site = db.session.query(Historic_Site).filter(Historic_Site.id == site_id).first()
    if not site:
        return None
    
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

# Tags
def clean_tag_name(raw_name: str) -> str:
    if raw_name is None:
        return ""

    text = str(raw_name).strip()
    if not text:
        return ""

    pieces = []
    for part in text.split(" "):
        if part:
            pieces.append(part)

    return " ".join(pieces)


def slugify(text: str) -> str:
    if text is None:
        return "tag"

    normalized = unicodedata.normalize("NFKD", text)

    ascii_chars = []
    for char in normalized:
        if ord(char) < 128:
            ascii_chars.append(char)
    ascii_text = "".join(ascii_chars)

    lower_text = ascii_text.lower()

    slug_chars: List[str] = []
    last_was_dash = False
    for char in lower_text:
        if char.isalnum():
            slug_chars.append(char)
            last_was_dash = False
        elif char in (" ", "-", "_"):
            if slug_chars and not last_was_dash:
                slug_chars.append("-")
                last_was_dash = True
        else:
            continue

    slug = "".join(slug_chars).strip("-")
    return slug or "tag"


def validate_tag_payload(name: str, *, existing_id: Optional[int] = None) -> Tuple[bool, Dict[str, List[str]], str, str]:
    """Valida nombre y slug de la etiqueta.

    Devuelve una tupla con:
    - si el payload es válido
    - los errores encontrados
    - el nombre limpio
    - el slug definitivo
    """

    errors: Dict[str, List[str]] = {}

    clean_name = clean_tag_name(name)

    if not clean_name:
        errors.setdefault("name", []).append("El nombre es obligatorio.")
    elif len(clean_name) < 3 or len(clean_name) > 50:
        errors.setdefault("name", []).append("El nombre debe tener entre 3 y 50 caracteres.")

    max_slug_length = 60
    slug = slugify(clean_name)
    if len(slug) > max_slug_length:
        slug = slug[:max_slug_length]

    if not errors.get("name"):
        name_query = db.session.query(SiteTag.id).filter(func.lower(SiteTag.name) == clean_name.lower())
        if existing_id is not None:
            name_query = name_query.filter(SiteTag.id != existing_id)
        if name_query.first() is not None:
            errors.setdefault("name", []).append("Ya existe una etiqueta con ese nombre.")

    if not errors.get("name"):
        slug_query = db.session.query(SiteTag.id).filter(SiteTag.slug == slug)
        if existing_id is not None:
            slug_query = slug_query.filter(SiteTag.id != existing_id)
        if slug_query.first() is not None:
            base_slug = slug
            counter = 2
            unique_slug_found = False
            while not unique_slug_found:
                suffix = f"-{counter}"
                candidate = f"{base_slug}{suffix}"
                if len(candidate) > max_slug_length:
                    available = max_slug_length - len(suffix)
                    candidate = f"{base_slug[:available]}{suffix}"
                candidate_query = db.session.query(SiteTag.id).filter(SiteTag.slug == candidate)
                if existing_id is not None:
                    candidate_query = candidate_query.filter(SiteTag.id != existing_id)
                if candidate_query.first() is None:
                    slug = candidate
                    unique_slug_found = True
                else:
                    counter += 1

    is_valid = not errors
    return is_valid, errors, clean_name, slug


def list_tags() -> List[Dict[str, Any]]:
    tags = db.session.query(SiteTag).order_by(SiteTag.name.asc()).all()
    return [{"id": tag.id, "name": tag.name} for tag in tags]


def paginate_tags(
    *,
    page: int = 1,
    per_page: int = 25,
    search: Optional[str] = None,
    order_by: str = "name",
    order_dir: str = "asc",
) -> Pagination:
    session = db.session
    query = session.query(SiteTag)

    if search:
        query = query.filter(SiteTag.name.ilike(f"%{search.strip()}%"))

    allowed_order = {"name": SiteTag.name, "created_at": SiteTag.created_at}
    order_column = allowed_order.get(order_by, SiteTag.name)
    order_fn = asc if order_dir == "asc" else desc
    query = query.order_by(order_fn(order_column))

    total = query.count()
    page = max(page, 1)
    per_page = max(1, min(per_page, 25))
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return Pagination(items, total, page, per_page)


def get_tag(tag_id: int) -> Optional[SiteTag]:
    return db.session.get(SiteTag, tag_id)


def create_tag(name: str) -> Tuple[bool, Optional[SiteTag], Dict[str, List[str]]]:
    is_valid, errors, clean_name, slug = validate_tag_payload(name)
    if not is_valid:
        return False, None, errors

    tag = SiteTag(name=clean_name, slug=slug)
    db.session.add(tag)
    db.session.commit()
    return True, tag, {}


def update_tag(tag: SiteTag, name: str) -> Tuple[bool, Optional[SiteTag], Dict[str, List[str]]]:
    is_valid, errors, clean_name, slug = validate_tag_payload(name, existing_id=tag.id)
    if not is_valid:
        return False, None, errors

    tag.name = clean_name
    tag.slug = slug
    db.session.add(tag)
    db.session.commit()
    return True, tag, {}


def delete_tag(tag: SiteTag) -> Tuple[bool, Dict[str, List[str]]]:
    if tag.sites:
        return False, {"delete": ["No se puede eliminar una etiqueta con sitios asociados."]}
    db.session.delete(tag)
    db.session.commit()
    return True, {}
