from flask import Flask, request, url_for
from flask import render_template
from src.core import database
from src.web.config import config
from src.web.controllers import register_controllers
from src.web.handlers import error

def create_app(env="development", static_folder="../../static"):
    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(config[env])

    # Inicializar base de datos
    database.init_db(app)

    @app.route('/')
    def home():
        return render_template("home.html")

    @app.route('/about')
    def about():
        return render_template("about.html")

    # falta completar
    @app.route('/gestion_sitios')
    def gestion_sitios(): 
        return render_template("gestionSitios.html")

    @app.route('/validacion_propuestas')
    def validacion_propuestas():
        return render_template("validacionPropuestas.html")
    
    @app.route('/moderacion_reseñas')
    def moderacion_reseñas():
        return render_template("moderacionReseñas.html")
    
    @app.route('/gestion_usuarios')
    def gestion_usuarios(): 
        return render_template("gestionUsuarios.html")
    
    @app.route('/login')
    def login(): 
        return render_template("login.html")
    
    @app.route('/perfil_usuario')
    def perfil_usuario(): 
        return render_template("perfilUsuario.html")
    
    app.register_error_handler(404, error.not_found)

    app.register_error_handler(401, error.unauthorized)

    app.register_error_handler(500, error.internal_server_error)

    # Register commands
    @app.cli.command("reset-db")
    def reset_db():
        database.reset_db(app)

    register_controllers(app)

    return app
