"""Vistas de autenticación y helpers de permisos del panel."""

from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from src.core.security.passwords import verify_password
from src.core.flags import service as flags_service
from src.core.permissions import service as permissions_service
from src.core.users import service as users_service
from src.core.users.models import User
from src.core.users import UserRole

auth_bp = Blueprint("auth", __name__) 

# ----- Decoradores -----
def require_login(view):
    """Obligo a que la vista tenga un usuario logueado."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Se requiere iniciar sesión", "error")
            return redirect(url_for("auth.login", next=request.url))
        return view(*args, **kwargs)
    return wrapped

def require_permissions(*required):
    """Valido que el usuario tenga todos los permisos pedidos."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login", next=request.url))
            if session.get("user_role") == UserRole.SYSADMIN.value:
                return view(*args, **kwargs)
            permissions = set(session.get("permissions") or [])
            if not permissions.issuperset(required):
                flash("No tenés permisos para acceder a esa sección.", "error")
                return redirect(request.referrer or url_for("home"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def _load_permissions_for_user(user: User) -> list[str]:
    """Cargo los códigos de permisos asociados al usuario."""
    permissions = permissions_service.list_role_permissions(user.role)
    return [perm.code for perm in permissions]


# ----- Rutas -----
@auth_bp.get("/login")
def login():
    """Muestro el formulario de login o redirijo si ya hay sesión."""
    if session.get("user_id"):
        return redirect(url_for('home'))
    return render_template("login.html")

@auth_bp.post("/login")
def login_post():
    """Proceso el login, valido credenciales y armo la sesión."""
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_url = request.args.get("next") or url_for("home")

    user = users_service.find_user_by_email(email)

    if not user:
        flash("Credenciales inválidas.", "error")
        return redirect(url_for("auth.login", next=next_url))

    if not user.is_active:
        flash("Tu cuenta se encuentra inactiva. Contactá a un administrador para reactivarla.", "error")
        return redirect(url_for("auth.login", next=next_url))

    if not verify_password(password, user.password_hash):
        flash("Credenciales inválidas.", "error")
        return redirect(url_for("auth.login", next=next_url))

    maintenance_flag = flags_service.get_flag("admin_maintenance_mode")
    if maintenance_flag and maintenance_flag.enabled:
        user_role_value = user.role
        if user_role_value != "sysadmin":
            message = maintenance_flag.message or "El panel de administración está en mantenimiento."
            flash(message, "warning")
            return redirect(url_for("auth.login", next=next_url))
        next_url = url_for("featureflags.manage")

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["user_role"] = user.role
    session["permissions"] = _load_permissions_for_user(user)

    flash("Sesión iniciada correctamente", "success")
    
    return redirect(next_url)

@auth_bp.get("/logout")
def logout():
    """Cierro la sesión activa y vuelvo al login."""
    if session.get("user_id"):
        session.clear()
        flash("Has cerrado sesión", "success")
    else:
        flash("No has iniciado sesión", "error")
    return redirect(url_for("auth.login"))
