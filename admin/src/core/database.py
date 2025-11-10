"""Configuro la conexión con la base de datos y los helpers de mantenimiento."""

from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

db = SQLAlchemy()

def init_db(app):
    """Inicializo SQLAlchemy con la app"""
    db.init_app(app)
    return db

def reset_db(app):
    """Reseteo las tablas para dejar la base limpia de datos previos."""
    from src.core.users.models import User, Role
    from src.core.sites.models import Historic_Site, SiteTag, SiteImage
    from src.core.permissions.models import Permission, RolePermission
    from src.core.flags.models import FeatureFlag


    print("Resetting database...")
    Base.metadata.drop_all(bind=db.engine)
    Base.metadata.create_all(bind=db.engine)
    print("Database reset complete")

class Base(DeclarativeBase):
    pass
