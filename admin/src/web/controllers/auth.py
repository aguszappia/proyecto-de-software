from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, abort, flash
from src.core.database import db
from src.core.users.models import User
from src.core.security.passwords import verify_password
from src.core.flags import service as flags_service

auth_bp = Blueprint("auth", __name__) 

# ----- Decoradores -----
def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Se requiere iniciar sesión", "error")
            return redirect(url_for("auth.login", next=request.url))
        return view(*args, **kwargs)
    return wrapped

def require_roles(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login", next=request.url))
            if session.get("user_role") not in roles:
                # flash de falta de permisos y redirige a la pagina anterior o al home si no hay referrer
                flash("No tenés permisos para acceder a esa sección.", "error")
                return redirect(request.referrer or url_for("home"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

# ----- Rutas -----
@auth_bp.get("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for('home'))  
    return render_template("login.html")

@auth_bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_url = request.args.get("next") or url_for("home")

    user = db.session.query(User).filter(User.email.ilike(email)).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        flash("Credenciales inválidas", "error")
        return redirect(url_for("auth.login", next=next_url))

    maintenance_flag = flags_service.get_flag("admin_maintenance_mode")
    if maintenance_flag and maintenance_flag.enabled:
        user_role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
        if user_role_value != "sysadmin":
            message = maintenance_flag.message or "El panel de administración está en mantenimiento."
            flash(message, "warning")
            return redirect(url_for("auth.login", next=next_url))
        next_url = url_for("featureflags")

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["user_role"] = user.role.value if hasattr(user.role, "value") else str(user.role)

    flash("Sesión iniciada correctamente", "success")
    
    return redirect(next_url)

@auth_bp.get("/logout")
def logout():
    if session.get("user_id"):    
        session.clear()
        flash("Has cerrado sesión", "success")
    else:
        flash("No has iniciado sesión", "error")
    return redirect(url_for("auth.login"))
