"""Blueprint para la moderación de reseñas de sitios históricos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from flask import Blueprint, flash, redirect, render_template, request, url_for

from src.core.pagination import Pagination
from src.core.sites.models import ReviewStatus
from src.core.sites.reviews_service import (
    MAX_REJECTION_LENGTH,
    ReviewPresenter,
    approve_review,
    delete_review,
    get_review,
    get_review_presenter,
    list_sites_for_filter,
    paginate_reviews,
    reject_review,
)
from src.web.controllers.auth import require_login, require_permissions
from src.web.controllers.sites.sites_utils import parse_date

bp = Blueprint("reviews", __name__, url_prefix="/moderacion_reseñas")

STATUS_CHIP_CLASSES: Dict[str, str] = {
    ReviewStatus.PENDING.value: "status-chip status-chip--pending",
    ReviewStatus.APPROVED.value: "status-chip status-chip--approved",
    ReviewStatus.REJECTED.value: "status-chip status-chip--rejected",
}


@dataclass
class ReviewFilters:
    """Agrupo los filtros del listado para reutilizarlos en los templates."""

    status: str = ""
    site_id: Optional[int] = None
    rating_min: Optional[int] = None
    rating_max: Optional[int] = None
    created_from: str = ""
    created_to: str = ""
    user_query: str = ""
    order_by: str = "created_at"
    order_dir: str = "desc"
    page: int = 1


def _safe_positive_int(raw_value: Optional[str]) -> Optional[int]:
    """Intento parsear un entero positivo, devolviendo None si falla."""
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _parse_rating(raw_value: Optional[str]) -> Optional[int]:
    """Convierto la calificación a un entero entre 1 y 5."""
    value = _safe_positive_int(raw_value)
    if value is None:
        return None
    if 1 <= value <= 5:
        return value
    return None


def _extract_filters() -> Tuple[ReviewFilters, Optional[ReviewStatus], Optional[datetime], Optional[datetime]]:
    """Normalizo los filtros provenientes del query string."""
    args = request.args
    filters = ReviewFilters()

    filters.status = (args.get("status") or "").strip()
    filters.site_id = _safe_positive_int(args.get("site_id"))
    filters.rating_min = _parse_rating(args.get("rating_min"))
    filters.rating_max = _parse_rating(args.get("rating_max"))
    if (
        filters.rating_min is not None
        and filters.rating_max is not None
        and filters.rating_min > filters.rating_max
    ):
        filters.rating_min, filters.rating_max = filters.rating_max, filters.rating_min

    filters.created_from = (args.get("created_from") or "").strip()
    filters.created_to = (args.get("created_to") or "").strip()
    filters.user_query = (args.get("user") or "").strip()

    raw_order_by = (args.get("order_by") or "created_at").strip()
    filters.order_by = raw_order_by if raw_order_by in {"created_at", "rating"} else "created_at"
    raw_order_dir = (args.get("order_dir") or "desc").strip()
    filters.order_dir = raw_order_dir if raw_order_dir in {"asc", "desc"} else "desc"

    filters.page = _safe_positive_int(args.get("page")) or 1

    status_enum = None
    if filters.status:
        for status_option in ReviewStatus:
            if filters.status in {status_option.value, status_option.name}:
                status_enum = status_option
                filters.status = status_option.value
                break
        else:
            filters.status = ""

    created_from_dt = parse_date(filters.created_from)
    created_to_dt = parse_date(filters.created_to, end_of_day=True)

    return filters, status_enum, created_from_dt, created_to_dt


def _current_full_path() -> str:
    """Devuelvo la ruta actual con query parameters para volver tras acciones."""
    full_path = request.full_path or request.path or "/"
    if full_path.endswith("?"):
        full_path = full_path[:-1]
    return full_path


def _safe_return_path(raw_value: Optional[str]) -> Optional[str]:
    """Acepto solo rutas internas iniciando con / para evitar redirecciones externas."""
    if not raw_value:
        return None
    if raw_value.startswith("/"):
        return raw_value
    return None


def _redirect_back(default_url: Optional[str] = None):
    """Redirijo al origen cuando esté disponible."""
    target = _safe_return_path(request.form.get("return_to"))
    if target:
        return redirect(target)
    if default_url:
        return redirect(default_url)
    return redirect(url_for("reviews.index"))


@bp.get("/")
@require_login
@require_permissions("reviews_moderate")
def index():
    """Listo las reseñas aplicando los filtros seleccionados."""
    filters, status_enum, created_from_dt, created_to_dt = _extract_filters()
    pagination: Pagination[ReviewPresenter] = paginate_reviews(
        page=filters.page,
        per_page=25,
        status=status_enum,
        site_id=filters.site_id,
        rating_min=filters.rating_min,
        rating_max=filters.rating_max,
        created_from=created_from_dt,
        created_to=created_to_dt,
        user_query=filters.user_query or None,
        order_by=filters.order_by,
        order_dir=filters.order_dir,
    )

    params: Dict[str, object] = {}
    if filters.status:
        params["status"] = filters.status
    if filters.site_id:
        params["site_id"] = filters.site_id
    if filters.rating_min is not None:
        params["rating_min"] = filters.rating_min
    if filters.rating_max is not None:
        params["rating_max"] = filters.rating_max
    if filters.created_from:
        params["created_from"] = filters.created_from
    if filters.created_to:
        params["created_to"] = filters.created_to
    if filters.user_query:
        params["user"] = filters.user_query
    if filters.order_by != "created_at":
        params["order_by"] = filters.order_by
    if filters.order_dir != "desc":
        params["order_dir"] = filters.order_dir

    prev_url = (
        url_for("reviews.index", page=pagination.page - 1, **params)
        if pagination.page > 1
        else None
    )
    next_url = (
        url_for("reviews.index", page=pagination.page + 1, **params)
        if pagination.page < pagination.pages
        else None
    )

    return render_template(
        "reviews/index.html",
        pagination=pagination,
        filters=filters,
        status_options=list(ReviewStatus),
        status_chip_classes=STATUS_CHIP_CLASSES,
        sites=list_sites_for_filter(),
        rating_values=[1, 2, 3, 4, 5],
        prev_url=prev_url,
        next_url=next_url,
        return_path=_current_full_path(),
        max_reason_length=MAX_REJECTION_LENGTH,
    )


@bp.get("/<int:review_id>")
@require_login
@require_permissions("reviews_moderate")
def detail(review_id: int):
    """Muestro la información completa de la reseña."""
    presenter = get_review_presenter(review_id)
    if not presenter:
        flash("La reseña solicitada no existe.", "error")
        return redirect(url_for("reviews.index"))

    return_url = _safe_return_path(request.args.get("return_to")) or url_for("reviews.index")

    return render_template(
        "reviews/detail.html",
        presenter=presenter,
        status_chip_classes=STATUS_CHIP_CLASSES,
        return_url=return_url,
        ReviewStatus=ReviewStatus,
        max_reason_length=MAX_REJECTION_LENGTH,
    )


def _load_review_or_redirect(review_id: int):
    """Busco la reseña y manejo el caso inexistente."""
    review = get_review(review_id)
    if not review:
        flash("La reseña solicitada no existe.", "error")
        return None, redirect(url_for("reviews.index"))
    return review, None


@bp.post("/<int:review_id>/approve")
@require_login
@require_permissions("reviews_moderate")
def approve(review_id: int):
    """Cambio el estado a aprobado."""
    review, redirect_response = _load_review_or_redirect(review_id)
    if redirect_response:
        return redirect_response

    if review.status == ReviewStatus.APPROVED:
        flash("La reseña ya estaba aprobada.", "info")
    else:
        approve_review(review)
        flash("La reseña fue aprobada correctamente.", "success")

    return _redirect_back(url_for("reviews.detail", review_id=review_id))


@bp.post("/<int:review_id>/reject")
@require_login
@require_permissions("reviews_moderate")
def reject(review_id: int):
    """Marco la reseña como rechazada exigiendo un motivo."""
    review, redirect_response = _load_review_or_redirect(review_id)
    if redirect_response:
        return redirect_response

    if review.status == ReviewStatus.REJECTED:
        flash("La reseña ya estaba rechazada.", "info")
        return _redirect_back(url_for("reviews.detail", review_id=review_id))

    reason = (request.form.get("reason") or "").strip()
    success, errors = reject_review(review, reason)
    if not success:
        message = errors.get("reason", ["No se pudo rechazar la reseña."])[0]
        flash(message, "error")
        return _redirect_back(url_for("reviews.detail", review_id=review_id))

    flash("La reseña fue rechazada y se registró el motivo.", "success")
    return _redirect_back(url_for("reviews.detail", review_id=review_id))


@bp.post("/<int:review_id>/delete")
@require_login
@require_permissions("reviews_moderate")
def destroy(review_id: int):
    """Elimino la reseña de forma permanente."""
    review, redirect_response = _load_review_or_redirect(review_id)
    if redirect_response:
        return redirect_response

    delete_review(review)
    flash("La reseña fue eliminada correctamente.", "success")
    return _redirect_back(url_for("reviews.index"))
