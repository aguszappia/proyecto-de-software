from flask import Flask, request, url_for
from flask import render_template
from src.web.config import config
from src.web.handlers import error
from src.core import database

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

    # búsqueda avanzada de sitios
    @app.route('/gestion_sitios')
    def gestion_sitios():
        # Leer filtros desde querystring
        q = request.args
        filters = {
            "city": q.get("city", "").strip() or None,
            "province": q.get("province") or None,
            "tags": [t for t in q.get("tags","").split(",") if t] if q.get("tags") else None,
            "state": q.get("state") or None,           # values: Bueno|Regular|Malo
            "date_from": q.get("date_from") or None,
            "date_to": q.get("date_to") or None,
            "visible": None if q.get("visible") is None else q.get("visible") == "1",
            "text": q.get("text","").strip() or None
        }

    # Orden y paginación
        order_by = q.get("order_by", "date")  # date | name | city
        order_dir = q.get("order_dir", "desc")  # asc | desc
        try:
            page = max(1, int(q.get("page", 1)))
        except ValueError:
            page = 1
        per_page = 25

        # Llamada a la capa de datos (si la DB no está lista, devolver vacío para probar la vista)
        try:
            items, total = database.search_sites(filters=filters, page=page, per_page=per_page,
                                                order_by=order_by, order_dir=order_dir)
        except Exception as e:
            # Cuando la base de datos no está inicializada o la función no existe,
            # devolvemos lista vacía y total 0 para poder renderizar la plantilla.
            app.logger.warning("search_sites no disponible: %s", e)
            items, total = [], 0

        return render_template("gestionSitios.html",
                               results=items,
                               total=total,
                               page=page,
                               per_page=per_page,
                               filters=filters,
                               order_by=order_by,
                               order_dir=order_dir)


    app.register_error_handler(404, error.not_found)

    app.register_error_handler(401, error.unauthorized)

    app.register_error_handler(500, error.internal_server_error)

    # Register commands
    @app.cli.command("reset-db")
    def reset_db():
        database.reset_db(app)

    return app