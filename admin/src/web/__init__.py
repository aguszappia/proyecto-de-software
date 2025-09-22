from flask import Flask
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

    app.register_error_handler(404, error.not_found)

    app.register_error_handler(401, error.unauthorized)

    app.register_error_handler(500, error.internal_server_error)

    # Register commands
    @app.cli.command("reset-db")
    def reset_db():
        database.reset_db(app)

    register_controllers(app)

    return app
