from flask import Flask, request, url_for, redirect, session
from flask import render_template
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

    # Middleware para proteger rutas privadas
    @app.before_request
    def protect_private_area():
        path = request.path or ""

        # Rutas públicas (no piden login)
        allowed = (
            path == "/login"
            or path == "/logout"
            or path.startswith("/static/")
            or path == "/"        # home pública
            or path.startswith("/about")
            or path.startswith("/sites/public")
        )

        if not allowed and not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.url)) 
        
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
