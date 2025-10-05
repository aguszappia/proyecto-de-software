"""Funciones para gestionar etiquetas de sitios históricos."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import unicodedata

from sqlalchemy import asc, desc, func

from src.core.database import db
from src.core.sites.models import SiteTag
from src.core.pagination import Pagination


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
    ascii_text = "".join(char for char in normalized if char.isascii())

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


def _validate_tag_payload(
    name: str,
    *,
    existing_id: Optional[int] = None,
) -> Tuple[bool, Dict[str, List[str]], str, str]:
    """Valida nombre y slug de la etiqueta."""

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


def create_tag(name: str):
    is_valid, errors, clean_name, slug = _validate_tag_payload(name)
    if not is_valid:
        return False, None, errors

    tag = SiteTag(name=clean_name, slug=slug)
    db.session.add(tag)
    db.session.commit()
    return True, tag, {}


def update_tag(tag: SiteTag, name: str):
    is_valid, errors, clean_name, slug = _validate_tag_payload(name, existing_id=tag.id)
    if not is_valid:
        return False, None, errors

    tag.name = clean_name
    tag.slug = slug
    db.session.add(tag)
    db.session.commit()
    return True, tag, {}


def delete_tag(tag: SiteTag):
    if tag.sites:
        return False, {"delete": ["No se puede eliminar una etiqueta con sitios asociados."]}
    db.session.delete(tag)
    db.session.commit()
    return True, {}
