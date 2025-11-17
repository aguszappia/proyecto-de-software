"""Gestiono las reseñas de sitios históricos para moderación."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy import asc, and_, desc, func, or_
from sqlalchemy.orm import joinedload

from src.core.database import db
from src.core.pagination import Pagination
from src.core.sites.models import Historic_Site, ReviewStatus, SiteImage, SiteReview
from src.core.users.models import User

MAX_REJECTION_LENGTH = 200


@dataclass
class ReviewPresenter:
    """Contenedor simple para mostrar reseñas junto a datos asociados."""

    review: SiteReview
    site_id: int
    site_name: str
    user_email: Optional[str]
    user_name: str
    site_cover_url: Optional[str] = None
    site_cover_title: Optional[str] = None

    @property
    def user_display(self) -> str:
        """Muestro alias o el email en caso de faltar datos."""
        clean_name = self.user_name.strip()
        if clean_name:
            return clean_name
        return self.user_email or "Usuario desconocido"


def list_sites_for_filter() -> List[Dict[str, object]]:
    """Obtengo los sitios visibles para poblar el selector de filtros."""
    sites = (
        db.session.query(Historic_Site.id, Historic_Site.name)
        .order_by(Historic_Site.name.asc())
        .all()
    )
    return [{"id": site_id, "name": site_name} for site_id, site_name in sites]


def _base_query():
    """Armo el query principal con joins para reutilizar en listados."""
    session = db.session
    return (
        session.query(
            SiteReview,
            Historic_Site.id.label("site_id"),
            Historic_Site.name.label("site_name"),
            User.email.label("user_email"),
            User.first_name.label("user_first_name"),
            User.last_name.label("user_last_name"),
            SiteImage.url.label("site_cover_url"),
            SiteImage.title.label("site_cover_title"),
        )
        .join(Historic_Site, SiteReview.site_id == Historic_Site.id)
        .outerjoin(
            SiteImage,
            and_(SiteImage.site_id == Historic_Site.id, SiteImage.is_cover.is_(True)),
        )
        .outerjoin(User, User.id == SiteReview.user_id)
    )


def paginate_reviews(
    *,
    page: int = 1,
    per_page: int = 25,
    status: Optional[ReviewStatus] = None,
    site_id: Optional[int] = None,
    rating_min: Optional[int] = None,
    rating_max: Optional[int] = None,
    created_from=None,
    created_to=None,
    user_query: Optional[str] = None,
    order_by: str = "created_at",
    order_dir: str = "desc",
) -> Pagination[ReviewPresenter]:
    """Listo las reseñas aplicando filtros y devolviendo una paginación."""

    query = _base_query()

    if status:
        query = query.filter(SiteReview.status == status)
    if site_id:
        query = query.filter(SiteReview.site_id == site_id)
    if rating_min is not None:
        query = query.filter(SiteReview.rating >= rating_min)
    if rating_max is not None:
        query = query.filter(SiteReview.rating <= rating_max)
    if created_from:
        query = query.filter(SiteReview.created_at >= created_from)
    if created_to:
        query = query.filter(SiteReview.created_at <= created_to)
    if user_query:
        like = f"%{user_query.strip()}%"
        query = query.filter(
            or_(
                User.email.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
            )
        )

    total = query.order_by(None).count()

    allowed_order = {
        "created_at": SiteReview.created_at,
        "rating": SiteReview.rating,
    }
    order_column = allowed_order.get(order_by, SiteReview.created_at)
    order_fn = asc if order_dir == "asc" else desc
    query = query.order_by(order_fn(order_column))

    page = max(page, 1)
    per_page = max(1, min(per_page, 25))
    items = query.limit(per_page).offset((page - 1) * per_page).all()

    presenters: List[ReviewPresenter] = []
    for (
        review,
        site_id,
        site_name,
        user_email,
        first_name,
        last_name,
        cover_url,
        cover_title,
    ) in items:
        full_name = " ".join(part for part in [first_name or "", last_name or ""] if part).strip()
        presenters.append(
            ReviewPresenter(
                review=review,
                site_id=site_id,
                site_name=site_name,
                user_email=user_email,
                user_name=full_name,
                site_cover_url=cover_url,
                site_cover_title=cover_title,
            )
        )

    return Pagination(presenters, total, page, per_page)


def get_review(review_id: int) -> Optional[SiteReview]:
    """Busco una reseña por id con el sitio asociado."""
    row = (
        db.session.query(SiteReview, User.first_name, User.last_name)
        .options(joinedload(SiteReview.site))
        .outerjoin(User, User.id == SiteReview.user_id)
        .filter(SiteReview.id == review_id)
        .first()
    )
    if not row:
        return None
    review, first_name, last_name = row
    return _attach_author(review, first_name, last_name)


def get_review_presenter(review_id: int) -> Optional[ReviewPresenter]:
    """Devuelvo la reseña formateada para la vista de detalle."""
    row = _base_query().filter(SiteReview.id == review_id).first()
    if not row:
        return None
    review, site_id, site_name, user_email, first_name, last_name, cover_url, cover_title = row
    full_name = " ".join(part for part in [first_name or "", last_name or ""] if part).strip()
    return ReviewPresenter(
        review=review,
        site_id=site_id,
        site_name=site_name,
        user_email=user_email,
        user_name=full_name,
        site_cover_url=cover_url,
        site_cover_title=cover_title,
    )


def _format_author_name(first_name: Optional[str], last_name: Optional[str]) -> str:
    parts = [part.strip() for part in [first_name or "", last_name or ""] if part]
    display = " ".join(parts).strip()
    return display or "Visitante"


def _attach_author(review: SiteReview, first_name: Optional[str], last_name: Optional[str]) -> SiteReview:
    review.author_name = _format_author_name(first_name, last_name)
    return review


def list_public_reviews_for_site(site_id: int) -> List[SiteReview]:
    """Devuelvo las reseñas aprobadas de un sitio para el portal público."""
    reviews: List[SiteReview] = []
    query = (
        db.session.query(SiteReview, User.first_name, User.last_name)
        .outerjoin(User, User.id == SiteReview.user_id)
        .filter(
            SiteReview.site_id == site_id,
            SiteReview.status == ReviewStatus.APPROVED,
        )
        .order_by(SiteReview.created_at.desc())
    )
    for review, first_name, last_name in query.all():
        reviews.append(_attach_author(review, first_name, last_name))
    return reviews


def get_public_review_stats(site_id: int) -> Dict[str, object]:
    """Calculo cantidad y promedio sólo de reseñas aprobadas."""
    avg_rating, total = (
        db.session.query(func.avg(SiteReview.rating), func.count(SiteReview.id))
        .filter(SiteReview.site_id == site_id, SiteReview.status == ReviewStatus.APPROVED)
        .first()
    )
    average = float(avg_rating) if avg_rating is not None else None
    return {
        "average_rating": average,
        "total_reviews": int(total or 0),
    }


def find_review_by_user(site_id: int, user_id: int) -> Optional[SiteReview]:
    """Busco la reseña existente para un usuario específico."""
    row = (
        db.session.query(SiteReview, User.first_name, User.last_name)
        .outerjoin(User, User.id == SiteReview.user_id)
        .filter(SiteReview.site_id == site_id, SiteReview.user_id == user_id)
        .first()
    )
    if not row:
        return None
    review, first_name, last_name = row
    return _attach_author(review, first_name, last_name)


def create_site_review(*, site_id: int, user_id: int, rating: int, comment: str) -> SiteReview:
    """Creo una reseña pendiente para el portal público."""
    review = SiteReview(
        site_id=site_id,
        user_id=user_id,
        rating=rating,
        comment=comment.strip(),
        status=ReviewStatus.PENDING,
        rejection_reason=None,
    )
    db.session.add(review)
    db.session.commit()
    return review


def update_site_review(review: SiteReview, *, rating: int, comment: str) -> SiteReview:
    """Actualizo una reseña y la vuelvo a estado pendiente."""
    review.rating = rating
    review.comment = comment.strip()
    review.status = ReviewStatus.PENDING
    review.rejection_reason = None
    db.session.add(review)
    db.session.commit()
    return review


def approve_review(review: SiteReview):
    """Apruebo la reseña y limpio el motivo de rechazo anterior."""
    review.status = ReviewStatus.APPROVED
    review.rejection_reason = None
    db.session.add(review)
    db.session.commit()


def validate_rejection_reason(reason: str) -> Tuple[bool, Dict[str, List[str]], str]:
    """Valido el motivo obligando contenido y longitud máxima."""
    clean_reason = (reason or "").strip()
    errors: Dict[str, List[str]] = {}

    if not clean_reason:
        errors.setdefault("reason", []).append("El motivo de rechazo es obligatorio.")
    elif len(clean_reason) > MAX_REJECTION_LENGTH:
        errors.setdefault("reason", []).append(
            f"El motivo no puede superar los {MAX_REJECTION_LENGTH} caracteres."
        )

    return not errors, errors, clean_reason


def reject_review(review: SiteReview, reason: str) -> Tuple[bool, Dict[str, List[str]]]:
    """Rechazo la reseña guardando el motivo validado."""
    is_valid, errors, clean_reason = validate_rejection_reason(reason)
    if not is_valid:
        return False, errors

    review.status = ReviewStatus.REJECTED
    review.rejection_reason = clean_reason
    db.session.add(review)
    db.session.commit()
    return True, {}


def delete_review(review: SiteReview):
    """Elimino la reseña definitivamente."""
    db.session.delete(review)
    db.session.commit()


def list_reviews_for_user(user_id: int) -> List[Dict[str, object]]:
    """Devuelve las reseñas del usuario junto con datos básicos del sitio."""
    query = (
        db.session.query(
            SiteReview,
            Historic_Site,
            User.first_name,
            User.last_name,
        )
        .join(Historic_Site, SiteReview.site_id == Historic_Site.id)
        .outerjoin(User, User.id == SiteReview.user_id)
        .filter(SiteReview.user_id == user_id, Historic_Site.is_visible.is_(True))
        .order_by(SiteReview.created_at.desc())
    )
    reviews: List[Dict[str, object]] = []
    for review, site, first_name, last_name in query.all():
        reviews.append(
            {
                "review": _attach_author(review, first_name, last_name),
                "site": site,
            }
        )
    return reviews
