"""Blueprint para administrar etiquetas de sitios históricos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from flask import Blueprint, flash, redirect, render_template, request, url_for

from src.core.pagination import Pagination
from src.core.sites.models import SiteTag
from src.core.sites.service import (
    create_tag,
    delete_tag,
    get_tag,
    paginate_tags,
    update_tag,
)
from src.web.controllers.auth import require_login, require_roles


bp = Blueprint("tags", __name__, url_prefix="/tags")


@dataclass
class TagFilters:
    q: str = ""
    order_by: str = "name"
    order_dir: str = "asc"
    page: int = 1


def _extract_filters() -> TagFilters:
    args = request.args
    try:
        page = int(args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    order_by = args.get("order_by", "name") or "name"
    if order_by not in {"name", "created_at"}:
        order_by = "name"
    order_dir = args.get("order_dir", "asc") or "asc"
    if order_dir not in {"asc", "desc"}:
        order_dir = "asc"
    return TagFilters(
        q=(args.get("q") or "").strip(),
        order_by=order_by,
        order_dir=order_dir,
        page=max(page, 1),
    )


@bp.get("/")
@require_login
@require_roles("editor", "admin", "sysadmin")
def index():
    filters = _extract_filters()
    pagination: Pagination[SiteTag] = paginate_tags(
        page=filters.page,
        per_page=25,
        search=filters.q or None,
        order_by=filters.order_by,
        order_dir=filters.order_dir,
    )

    params: Dict[str, str] = {}
    if filters.q:
        params["q"] = filters.q
    if filters.order_by != "name":
        params["order_by"] = filters.order_by
    if filters.order_dir != "asc":
        params["order_dir"] = filters.order_dir

    prev_url = None
    next_url = None
    if pagination.page > 1:
        prev_url = url_for("tags.index", page=pagination.page - 1, **params)
    if pagination.page < pagination.pages:
        next_url = url_for("tags.index", page=pagination.page + 1, **params)

    return render_template(
        "tags/index.html",
        pagination=pagination,
        filters=filters,
        prev_url=prev_url,
        next_url=next_url,
    )


@bp.get("/new")
@require_login
@require_roles("editor", "admin", "sysadmin")
def new():
    return render_template("tags/form.html", form_values={"name": ""}, errors={}, is_edit=False)


@bp.post("/new")
@require_login
@require_roles("editor", "admin", "sysadmin")
def create():
    name = (request.form.get("name") or "").strip()
    success, tag, errors = create_tag(name)
    if not success:
        flash("No se pudo crear la etiqueta. Revisá los errores.", "error")
        return (
            render_template(
                "tags/form.html",
                form_values={"name": name},
                errors=errors,
                is_edit=False,
            ),
            400,
        )

    flash("Etiqueta creada correctamente.", "success")
    return redirect(url_for("tags.index"))


@bp.get("/<int:tag_id>/edit")
@require_login
@require_roles("editor", "admin", "sysadmin")
def edit(tag_id: int):
    tag = get_tag(tag_id)
    if tag is None:
        flash("La etiqueta no existe.", "error")
        return redirect(url_for("tags.index"))

    return render_template(
        "tags/form.html",
        form_values={"name": tag.name},
        current_slug=tag.slug,
        errors={},
        is_edit=True,
        tag_id=tag.id,
    )


@bp.post("/<int:tag_id>/edit")
@require_login
@require_roles("editor", "admin", "sysadmin")
def update(tag_id: int):
    tag = get_tag(tag_id)
    if tag is None:
        flash("La etiqueta no existe.", "error")
        return redirect(url_for("tags.index"))

    name = (request.form.get("name") or "").strip()
    success, updated_tag, errors = update_tag(tag, name)
    if not success:
        flash("No se pudo actualizar la etiqueta. Revisá los errores.", "error")
        return (
            render_template(
                "tags/form.html",
                form_values={"name": name},
                current_slug=tag.slug,
                errors=errors,
                is_edit=True,
                tag_id=tag.id,
            ),
            400,
        )

    flash("Etiqueta actualizada correctamente.", "success")
    return redirect(url_for("tags.index"))


@bp.post("/<int:tag_id>/delete")
@require_login
@require_roles("editor", "admin", "sysadmin")
def destroy(tag_id: int):
    tag = get_tag(tag_id)
    if tag is None:
        flash("La etiqueta no existe.", "error")
        return redirect(url_for("tags.index"))

    success, errors = delete_tag(tag)
    if not success:
        message = errors.get("delete", ["No se pudo eliminar la etiqueta."])[0]
        flash(message, "error")
        return redirect(url_for("tags.index"))

    flash("Etiqueta eliminada correctamente.", "success")
    return redirect(url_for("tags.index"))
