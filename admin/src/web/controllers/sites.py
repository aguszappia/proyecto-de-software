from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import List, Optional

from flask import Blueprint, render_template, request, url_for

from src.core.database import db
from src.core.sites.models import ConservationStatus, Historic_Site
from src.core.sites.service import list_tags, search_sites


bp = Blueprint("sites", __name__, url_prefix="/sites")


@dataclass
class SiteFilters:
    city: str = ""
    province: str = ""
    tags: List[int] = field(default_factory=list)
    conservation_status: str = ""
    created_from: str = ""
    created_to: str = ""
    is_visible: bool = False
    q: str = ""
    sort_by: str = "created_at"
    sort_dir: str = "desc"
    page: int = 1


def _parse_page(value: Optional[str]) -> int:
    try:
        page = int(value) if value is not None else 1
    except (TypeError, ValueError):
        page = 1
    return max(page, 1)


def _parse_tag_ids(values: List[str]) -> List[int]:
    result: List[int] = []
    for value in values:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


def _parse_date(value: str, *, end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

    target_time = time.max if end_of_day else time.min
    combined = datetime.combine(parsed_date, target_time)
    return combined.replace(tzinfo=timezone.utc)


def _parse_conservation_status(value: str) -> Optional[ConservationStatus]:
    if not value:
        return None
    for status in ConservationStatus:
        if value == status.value or value == status.name:
            return status
    return None


def _should_filter_visible(raw_value: Optional[str]) -> bool:
    return raw_value in {"on", "true", "1", "yes", "si"}


def _available_provinces() -> List[str]:
    rows = (
        db.session.query(Historic_Site.province)
        .distinct()
        .order_by(Historic_Site.province.asc())
        .all()
    )
    return [province for (province,) in rows if province]


@bp.get("/")
def index():
    args = request.args

    city = args.get("city", "").strip()
    province = args.get("province", "").strip()
    raw_tags = _parse_tag_ids(args.getlist("tags"))
    conservation_status_value = args.get("conservation_status", "").strip()
    created_from_raw = args.get("created_from", "").strip()
    created_to_raw = args.get("created_to", "").strip()
    show_only_visible = _should_filter_visible(args.get("is_visible"))
    search_text = args.get("q", "").strip()
    sort_by = args.get("sort_by", "created_at").strip() or "created_at"
    sort_dir = args.get("sort_dir", "desc").strip() or "desc"
    page = _parse_page(args.get("page"))

    created_from_dt = _parse_date(created_from_raw)
    if created_from_raw and created_from_dt is None:
        created_from_raw = ""

    created_to_dt = _parse_date(created_to_raw, end_of_day=True)
    if created_to_raw and created_to_dt is None:
        created_to_raw = ""

    conservation_status_enum = _parse_conservation_status(conservation_status_value)
    if conservation_status_value and conservation_status_enum is None:
        conservation_status_value = ""

    filters = SiteFilters(
        city=city,
        province=province,
        tags=raw_tags,
        conservation_status=conservation_status_value,
        created_from=created_from_raw,
        created_to=created_to_raw,
        is_visible=show_only_visible,
        q=search_text,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
    )

    pagination = search_sites(
        city=city or None,
        province=province or None,
        tag_ids=raw_tags or None,
        conservation_status=conservation_status_enum,
        created_from=created_from_dt,
        created_to=created_to_dt,
        is_visible=True if show_only_visible else None,
        q=search_text or None,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        per_page=25,
    )

    provinces = _available_provinces()
    tags = list_tags()
    query_args = {
        "city": city or None,
        "province": province or None,
        "tags": raw_tags,
        "conservation_status": conservation_status_value or None,
        "created_from": created_from_raw or None,
        "created_to": created_to_raw or None,
        "q": search_text or None,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
    }
    if show_only_visible:
        query_args["is_visible"] = "on"

    def _normalized_params():
        params = {}
        for key, value in query_args.items():
            if value is None or value == "":
                continue
            if isinstance(value, list):
                if not value:
                    continue
                params[key] = value
            else:
                params[key] = value
        return params

    normalized_params = _normalized_params()
    prev_url = (
        url_for("sites.index", page=pagination.page - 1, **normalized_params)
        if pagination.page > 1
        else None
    )
    next_url = (
        url_for("sites.index", page=pagination.page + 1, **normalized_params)
        if pagination.page < pagination.pages
        else None
    )

    return render_template(
        "sites/index.html",
        pagination=pagination,
        filters=filters,
        tags=tags,
        provinces=provinces,
        conservation_statuses=list(ConservationStatus),
        query_args=query_args,
        prev_url=prev_url,
        next_url=next_url,
    )
