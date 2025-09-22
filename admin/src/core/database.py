from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    return db

def reset_db(app):
    from src.core.board.issue import Issue
    from src.core.users.models import User

    print("Resetting database...")
    Base.metadata.drop_all(bind=db.engine)
    Base.metadata.create_all(bind=db.engine)
    print("Database reset complete")

class Base(DeclarativeBase):
    pass
