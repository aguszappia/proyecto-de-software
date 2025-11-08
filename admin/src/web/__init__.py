"""Construyo y configuro la aplicación Flask del panel."""

from flask import Flask, request, url_for, redirect, session, g
from flask import render_template, flash
from flask_session import Session
from src.core import database
from src.web.config import config
from src.web.controllers import register_controllers
from src.web.handlers import error
from src.web.controllers.auth import auth_bp
from src.web.controllers.reviews import reviews_bp
from flask_cors import CORS

from src.core import seeds
# from src.web.storage import storage

from src.web.controllers.auth import require_login
from src.web.controllers.featureflags import (
    ADMIN_MAINTENANCE_FLAG_KEY,
    ADMIN_MAINTENANCE_SESSION_KEY,
    DEFAULT_FLAG_MESSAGES,
)

from src.core.flags import service as flags_service
from src.core.users.service import get_user
from src.core.permissions import models as permissions_models  # noqa: F401
from src.core.permissions import service as permissions_service


def create_app(env="development", static_folder="../../static"):
    """Armo la app con configuración, blueprints, seeds y middlewares."""
    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(config[env])

    # Inicializar base de datos
    database.init_db(app)
    # storage.init_app(app)
    CORS(app)

    @app.route("/")
    def home():
        # Si el usuario ya inició sesión → va a home
        if session.get("user_id"):
            return render_template("home.html")
        # Si no tiene sesión → va al login
        return redirect(url_for("auth.login"))

    @app.route('/about')
    @require_login
    def about():
        """Muestro la página informativa solo para usuarios logueados."""
        return render_template("about.html")

    app.register_error_handler(404, error.not_found)

    app.register_error_handler(401, error.unauthorized)

    app.register_error_handler(500, error.internal_server_error)

    app.register_blueprint(auth_bp)

    app.register_blueprint(reviews_bp)

    # Register commands
    @app.cli.command("reset-db")
    def reset_db():
        """Reinicio la base usando los modelos actuales."""
        database.reset_db(app)

    @app.cli.command("seed-db")
    def seed_db():
        """Ejecuto las seeds registradas para poblar datos."""
        seeds.run()

    with app.app_context():
        if env == "production":
            from src.core.database import reset_db
            from src.core.seeds import run as seed_db

            #Resetea la base de datos
            reset_db(app)

            #Corre las seeds
            seed_db()

    register_controllers(app)

    Session(app)  # inicializa Flask-Session

    @app.before_request
    def load_user_permissions():
        """Cargo los permisos del usuario en sesión antes de cada request."""
        user_id = session.get("user_id")
        perms = session.get("permissions")
        if user_id and perms is None:
            user = get_user(user_id)
            if user:
                perms = [perm.code for perm in permissions_service.list_role_permissions(user.role)]
                session["permissions"] = perms
            else:
                perms = []
        g.permissions = set(perms or []) if user_id else set()

    @app.context_processor
    def inject_admin_maintenance_message():
        """Inyecto en templates el estado del flag de mantenimiento."""
        flag = flags_service.get_flag(ADMIN_MAINTENANCE_FLAG_KEY)
        enabled = bool(flag and flag.enabled)
        message = ""
        if enabled:
            message = flag.message or DEFAULT_FLAG_MESSAGES.get(ADMIN_MAINTENANCE_FLAG_KEY, "")
        return {
            "admin_maintenance_enabled": enabled,
            "admin_maintenance_message": message,
        }

    @app.context_processor
    def inject_permission_helpers():
        """Expongo helpers en templates para consultar permisos."""
        permissions = getattr(g, "permissions", set())

        def has_permission(code: str) -> bool:
            return code in permissions

        return {
            "has_permission": has_permission,
            "current_permissions": permissions,
        }

    # Middleware para proteger rutas privadas
    @app.before_request
    def protect_private_area():
        """Bloqueo rutas privadas y aplico el modo mantenimiento."""
        path = request.path or ""

        # Rutas públicas (no piden login)
        allowed = (
            path == "/login"
            or path == "/logout"
            or path.startswith("/static/")
        )

        if allowed:
            return None

        if not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.url))

        if session.get("user_role") == "sysadmin":
            return None

        if not hasattr(g, "feature_flags"):
            g.feature_flags = flags_service.load_flags()

        maintenance_flag = g.feature_flags.get(ADMIN_MAINTENANCE_FLAG_KEY)
        if maintenance_flag and maintenance_flag.enabled:
            message = maintenance_flag.message or DEFAULT_FLAG_MESSAGES.get(ADMIN_MAINTENANCE_FLAG_KEY, "")
            if message:
                flash(message, "warning")
            session[ADMIN_MAINTENANCE_SESSION_KEY] = message
            # nuevo control: solo redirigir si NO estamos ya en login
            if not path.startswith("/login"):
                # Limpia la sesión pública para evitar que el login reenvíe al home
                session.clear()
                return redirect(url_for("auth.login", next=request.url))
        else:
            session.pop(ADMIN_MAINTENANCE_SESSION_KEY, None)

    # Middleware para evitar cache en páginas privadas
    @app.after_request
    def add_no_cache_headers(response):
        """Agrego headers para evitar cachear vistas privadas."""
        try:
            # Solo si HAY sesión, solo en GET, y solo en 200 OK (no en redirects)
            if session.get("user_id") and request.method == "GET" and response.status_code == 200:
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
        finally:
            return response
    return app
