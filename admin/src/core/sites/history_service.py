from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Optional

from src.core.database import db
from src.core.pagination import Pagination
from src.core.sites.models import SiteHistory
from src.core.users.models import User

ACTIONS: List[str] = [
    "Creación",
    "Edición",
    "Cambio de estado",
    "Cambio de tags",
    "Eliminación",
]


def record_event(site_id: int, user_id: Optional[int], action_type: str, details: Optional[str]):
    """Registra historial para sitio"""

    event = SiteHistory(
        site_id=site_id,
        user_id=user_id,
        action_type=action_type,
        details=details,
    )
    db.session.add(event)
    db.session.commit()


def list_history(
    site_id: int,
    user_email: Optional[str] = None,
    action_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 25,
) -> Pagination[dict]:
    """Lista historial de sitio con filtros y paginación (25)"""

    query = db.session.query(SiteHistory).filter(SiteHistory.site_id == site_id)

    if user_email:
        like = f"%{user_email}%"
        user_ids = [user.id for user in db.session.query(User).filter(User.email.ilike(like)).all()]
        if user_ids:
            query = query.filter(SiteHistory.user_id.in_(user_ids))
        else:
            query = query.filter(False)
    if action_type:
        query = query.filter(SiteHistory.action_type == action_type)
    if date_from:
        query = query.filter(SiteHistory.created_at >= date_from)
    if date_to:
        query = query.filter(SiteHistory.created_at <= date_to)

    query = query.order_by(SiteHistory.created_at.desc())

    total = query.order_by(None).count()

    page = max(page, 1)
    per_page = max(1, min(per_page, 25))

    items = (
        query.limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    data = []
    user_cache: Dict[int, Optional[User]] = {}
    for event in items:
        item = event.to_dict()
        parsed_details = None
        if event.details:
            try:
                parsed_details = json.loads(event.details)
            except json.JSONDecodeError:
                parsed_details = None

        if parsed_details and isinstance(parsed_details, dict):
            message = parsed_details.get("message")
            if message:
                item["details"] = message
            item["metadata"] = parsed_details
        else:
            item["metadata"] = None

        if event.user_id:
            if event.user_id in user_cache:
                user = user_cache[event.user_id]
            else:
                user = db.session.get(User, event.user_id)
                user_cache[event.user_id] = user
            item["user_email"] = user.email if user else None
        else:
            item["user_email"] = None
        data.append(item)
    return Pagination(data, total, page, per_page)


def list_deleted_sites() -> List[Dict[str, object]]:
    """Devuelve los eventos de eliminación con la metadata asociada."""

    events = (
        db.session.query(SiteHistory)
        .filter(SiteHistory.action_type == "Eliminación")
        .order_by(SiteHistory.created_at.desc())
        .all()
    )

    deleted_sites: List[Dict[str, object]] = []
    user_cache: Dict[int, Optional[User]] = {}

    for event in events:
        metadata: Dict[str, Optional[str]] = {}
        if event.details:
            try:
                parsed = json.loads(event.details)
                if isinstance(parsed, dict):
                    metadata = {key: parsed.get(key) for key in parsed.keys()}
            except json.JSONDecodeError:
                metadata = {"message": event.details}

        if event.user_id:
            if event.user_id in user_cache:
                user = user_cache[event.user_id]
            else:
                user = db.session.get(User, event.user_id)
                user_cache[event.user_id] = user
            deleted_by = user.email if user else None
        else:
            deleted_by = None

        deleted_sites.append(
            {
                "site_id": event.site_id,
                "name": metadata.get("name"),
                "city": metadata.get("city"),
                "province": metadata.get("province"),
                "category": metadata.get("category"),
                "conservation_status": metadata.get("conservation_status"),
                "deleted_at": event.created_at,
                "deleted_by": deleted_by,
                "message": metadata.get("message") or "Sitio eliminado",
            }
        )

    return deleted_sites
