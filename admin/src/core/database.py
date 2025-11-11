"""Configuro la conexión con la base de datos y los helpers de mantenimiento."""

from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

db = SQLAlchemy()


def _load_models():
    """Importo los modelos para registrar todas las tablas en el metadata."""
    from src.core.users import models as users_models  # noqa: F401
    from src.core.sites import models as sites_models  # noqa: F401
    from src.core.permissions import models as permissions_models  # noqa: F401
    from src.core.flags import models as flags_models  # noqa: F401

    return users_models, sites_models, permissions_models, flags_models


def init_db(app):
    """Inicializo SQLAlchemy con la app y creo tablas faltantes."""
    db.init_app(app)
    _load_models()
    with app.app_context():
        Base.metadata.create_all(bind=db.engine)
    return db


def reset_db(app):
    """Reseteo las tablas para dejar la base limpia de datos previos."""
    _load_models()
    with app.app_context():
        print("Resetting database...")
        with db.engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS site_images CASCADE"))
        Base.metadata.drop_all(bind=db.engine)
        Base.metadata.create_all(bind=db.engine)
        print("Database reset complete")


class Base(DeclarativeBase):
    pass
