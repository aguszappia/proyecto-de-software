from dataclasses import dataclass

from flask import Blueprint, flash, redirect, render_template, request, url_for, session

from src.core.users import UserRole
from src.core.users.service import create_user, delete_user, get_allowed_roles_for_admin, get_user, list_users, update_user, activate_user, deactivate_user
from src.web.controllers.auth import require_login, require_permissions

bp = Blueprint("users", __name__, url_prefix="/users")


@dataclass
class UserFilters:
    email: str = ""
    role: str = ""
    active: str = ""
    order: str = "-created_at"
    page: int = 1


def _ensure_admin_access():
    """Lugar reservado para validar permisos reales."""
    return None


def _extract_filters():
    args = request.args
    try:
        page = int(args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    return UserFilters(
        email=args.get("email", "").strip(),
        role=args.get("role", "").strip(),
        active=args.get("active", "").strip(),
        order=args.get("order", "-created_at"),
        page=max(page, 1),
    )


def _parse_active_filter(value):
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _form_payload():
    form = request.form
    is_active = form.get("is_active")
    return {
        "email": form.get("email"),
        "first_name": form.get("first_name"),
        "last_name": form.get("last_name"),
        "password": form.get("password"),
        "is_active": is_active in {"on", "true", "1", "yes", "si"},
        "role": form.get("role"),
    }
 

@bp.get("/")
@require_login
@require_permissions("user_index")
def index():
    _ensure_admin_access()
    filters = _extract_filters()
    pagination = list_users(
        page=filters.page,
        per_page=25,
        search_email=filters.email or None,
        active=_parse_active_filter(filters.active),
        role=filters.role or None,
        order=filters.order, 
    )
    return render_template(
        "users/index.html",
        pagination=pagination,
        filters=filters,
        roles=list(UserRole),
    )


@bp.get("/new")
@require_login
@require_permissions("user_new")
def new():
    _ensure_admin_access()
    return render_template(
        "users/form.html",
        user=None,
        errors={},
        roles=list(get_allowed_roles_for_admin()),
    )


@bp.post("/new")
@require_login
@require_permissions("user_new")
def create():
    _ensure_admin_access()
    success, user, errors = create_user(_form_payload(), allowed_roles=get_allowed_roles_for_admin())
    if not success:
        flash("No se pudo crear el usuario. Revisá los errores.", "error")
        return render_template(
            "users/form.html",
            user=None,
            errors=errors or {},
            form=request.form,
            roles=list(get_allowed_roles_for_admin()),
        ), 400

    flash("Usuario creado correctamente.", "success")
    return redirect(url_for("users.index"))


@bp.get("/me")
@require_login
def me():
    """Vista de perfil para el propio usuario autenticado."""

    user = get_user(session.get("user_id"))
    if not user:
        flash("No se encontró el usuario.", "error")
        return redirect(url_for("auth.logout"))
    return render_template("perfilUsuario.html", user=user)


@bp.get("/<int:user_id>")
@require_login
@require_permissions("user_show")
def show(user_id: int):
    """Muestra información detallada del usuario."""

    _ensure_admin_access()
    user = get_user(user_id)
    if user is None:
        flash("El usuario no existe.", "error")
        return redirect(url_for("users.index"))

    return render_template("users/show.html", user=user)


@bp.get("/<int:user_id>/edit")
@require_login
@require_permissions("user_update")
def edit(user_id: int):
    _ensure_admin_access()
    user = get_user(user_id)
    if user is None:
        flash("El usuario no existe.", "error")
        return redirect(url_for("users.index"))

    return render_template(
        "users/form.html",
        user=user,
        errors={},
        roles=list(get_allowed_roles_for_admin()),
    )


@bp.post("/<int:user_id>/edit")
@require_login
@require_permissions("user_update")
def update(user_id: int):
    _ensure_admin_access()
    user = get_user(user_id)
    if user is None:
        flash("El usuario no existe.", "error")
        return redirect(url_for("users.index"))

    payload = _form_payload()
    if payload.get("is_active") is False and user.role in ("admin", "sysadmin"):
        flash("No se puede desactivar a un usuario con rol Administrador.", "error")
        return render_template(
            "users/form.html",
            user=user,
            errors={"is_active": "No se puede desactivar a un Administrador."},
            form=request.form,
            roles=list(get_allowed_roles_for_admin()),
        ), 400
    
    success, updated_user, errors = update_user(user, _form_payload(), allowed_roles=get_allowed_roles_for_admin())
    if not success:
        flash("No se pudo actualizar el usuario. Revisá los errores.", "error")
        return render_template(
            "users/form.html",
            user=user,
            errors=errors or {},
            form=request.form,
            roles=list(get_allowed_roles_for_admin()),
        ), 400

    flash("Usuario actualizado correctamente.", "success")
    return redirect(url_for("users.index"))


@bp.post("/<int:user_id>/delete")
@require_login
@require_permissions("user_destroy")
def destroy(user_id: int):
    _ensure_admin_access()
    user = get_user(user_id)
    if user is None:
        flash("El usuario no existe.", "error")
        return redirect(url_for("users.index"))

    delete_user(user)
    flash("Usuario eliminado correctamente.", "error")
    return redirect(url_for("users.index"))

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.post("/<int:user_id>/deactivate")
@require_login
@require_permissions("user_update")
def deactivate(user_id: int):
    _ensure_admin_access()
    user = get_user(user_id)
    if user is None:
        flash("El usuario no existe.", "error")
        return redirect(url_for("users.index"))
    
    try:
        # Llama al service que valida "no desactivar Admin"
        deactivate_user(user)
        flash("Usuario desactivado correctamente.", "error")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("users.index"))


@bp.post("/<int:user_id>/activate")
@require_login
@require_permissions("user_update")
def activate(user_id: int):
    _ensure_admin_access()
    user = get_user(user_id)
    if user is None:
        flash("El usuario no existe.", "error")
        return redirect(url_for("users.index"))

    activate_user(user)
    flash("Usuario activado correctamente.", "success")
    return redirect(url_for("users.index"))
 
@admin_bp.get("/")
@require_login
@require_permissions("user_index")
def dashboard():
    return render_template("admin/dashboard.html")

@admin_bp.get("/users")
@require_permissions("user_index")
def users_index():
    return redirect(url_for("users.index"))
