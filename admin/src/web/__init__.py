from flask import Flask, request, url_for, redirect, session, g
from flask import render_template, flash
from flask_session import Session
from src.core import database
from src.web.config import config
from src.web.controllers import register_controllers
from src.web.handlers import error
from src.web.controllers.auth import auth_bp
from src.web.controllers.validation import  validation_bp
from src.web.controllers.reviews import  reviews_bp

from src.core import seeds

from src.web.controllers.auth import require_login, require_roles

from src.core.flags import service as flags_service
from src.core.flags.service import FeatureFlagError


DEFAULT_FLAG_MESSAGES = {
    "admin_maintenance_mode": "El panel de administración está en mantenimiento.",
    "portal_maintenance_mode": "El portal público está en mantenimiento.",
    "reviews_enabled": "Las reseñas están disponibles.",
}

ADMIN_MAINTENANCE_FLAG_KEY = "admin_maintenance_mode"
ADMIN_MAINTENANCE_SESSION_KEY = "admin_maintenance_message"

def create_app(env="development", static_folder="../../static"):
    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(config[env])

    # Inicializar base de datos
    database.init_db(app)

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
        return render_template("about.html")

    # bloqueo acceso desde acá hasta crear nuevo index de propuestas
    @app.route('/validacion_propuestas')
    @require_login
    @require_roles("editor", "admin", "sysadmin")
    def validacion_propuestas():
        return render_template("validacionPropuestas.html")
    
    # bloqueo acceso desde acá hasta crear nuevo index de reseñas
    @app.route('/moderacion_reseñas')
    @require_login
    @require_roles("editor", "admin", "sysadmin")
    def moderacion_reseñas():
        return render_template("moderacionReseñas.html")
    
    @app.route('/login')
    def login(): 
        return render_template("login.html")
    
    @app.route('/perfil_usuario')
    @require_login
    def perfil_usuario(): 
        return render_template("perfilUsuario.html")
    
    @app.route('/featureflags', methods=['GET', 'POST'])
    @require_login
    @require_roles("sysadmin")
    def featureflags():
        if request.method == "POST":
            key = request.form.get("flag_key")
            enabled = request.form.get("enabled") == "true"

            if enabled:
                message = (
                    (request.form.get("message") or "")
                    or DEFAULT_FLAG_MESSAGES.get(key, "")
                ).strip()

                if not message:
                    flag = flags_service.get_flag(key)
                    message = (flag.message if flag else "") or ""
            else:
                message = ""

            try:
                flag = flags_service.set_flag(
                    key,
                    enabled=enabled,
                    message=message,
                    user_id=session.get("user_id"),
                )
                flash(
                    f"Flag «{flag.name}» {'activado' if enabled else 'desactivado'}.",
                    "success",
                )
            except FeatureFlagError as exc:
                flash(str(exc), "error")

            return redirect(url_for("featureflags"))

        flags = flags_service.list_flags()
        return render_template(
            "flags/featureflags.html",
            flags=flags,
            default_messages=DEFAULT_FLAG_MESSAGES,
        )
    
    app.register_error_handler(404, error.not_found)

    app.register_error_handler(401, error.unauthorized)

    app.register_error_handler(500, error.internal_server_error)

    app.register_blueprint(auth_bp)

    app.register_blueprint(validation_bp)

    app.register_blueprint(reviews_bp)

    # Register commands
    @app.cli.command("reset-db")
    def reset_db():
        database.reset_db(app)

    @app.cli.command("seed-db")
    def seed_db():
        seeds.run()

    register_controllers(app)

    Session(app)  # inicializa Flask-Session

    @app.context_processor
    def inject_admin_maintenance_message():
        flag = flags_service.get_flag(ADMIN_MAINTENANCE_FLAG_KEY)
        enabled = bool(flag and flag.enabled)
        message = ""
        if enabled:
            message = flag.message or DEFAULT_FLAG_MESSAGES.get(ADMIN_MAINTENANCE_FLAG_KEY, "")
        return {
            "admin_maintenance_enabled": enabled,
            "admin_maintenance_message": message,
        }

    # Middleware para proteger rutas privadas
    @app.before_request
    def protect_private_area():
        path = request.path or ""

        # Rutas públicas (no piden login)
        allowed = (
            path == "/login"
            or path == "/logout"
            or path.startswith("/static/")
            or path.startswith("/about")
            or path.startswith("/sites/public")
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
            if path != "/login":
                return redirect(url_for("auth.login", next=request.url))
        else:
            session.pop(ADMIN_MAINTENANCE_SESSION_KEY, None)

    # Middleware para evitar cache en páginas privadas
    @app.after_request
    def add_no_cache_headers(response):
        try:
            # Solo si HAY sesión, solo en GET, y solo en 200 OK (no en redirects)
            if session.get("user_id") and request.method == "GET" and response.status_code == 200:
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
        finally:
            return response
    return app
