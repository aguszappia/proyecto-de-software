from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.core.database import db
from src.core.pagination import Pagination
from src.core.sites.models import SiteHistory
from src.core.users.models import User

ACTIONS: List[str] = [
    "Creación",
    "Edición",
    "Cambio de estado",
    "Cambio de tags",
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
    for event in items:
        item = event.to_dict()
        if event.user_id:
            user = db.session.get(User, event.user_id)
            item["user_email"] = user.email if user else None
        else:
            item["user_email"] = None
        data.append(item)
    return Pagination(data, total, page, per_page)
