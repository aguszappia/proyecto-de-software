from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    return db

def reset_db(app):
    from src.core.users.models import User
    from src.core.sites.models import Historic_Site, SiteTag

    print("Resetting database...")
    Base.metadata.drop_all(bind=db.engine)
    Base.metadata.create_all(bind=db.engine)
    print("Database reset complete")

class Base(DeclarativeBase):
    pass
