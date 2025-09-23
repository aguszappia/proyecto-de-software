"""Funciones sencillas para manejar usuarios."""

from sqlalchemy import asc, desc

from src.core.database import db
from src.core.security.passwords import hash_password
from src.core.users import UserRole
from src.core.users.models import User
from src.core.users.validators import validate_user_payload


class Pagination:
    def __init__(self, items, total, page, per_page):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page

    @property
    def pages(self):
        if self.per_page == 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page


def list_users(page=1, per_page=25, search_email=None, active=None, role=None, order="-created_at"):
    session = db.session
    query = session.query(User)

    if search_email:
        query = query.filter(User.email.ilike(f"%{search_email.lower()}%"))
    if active is not None:
        query = query.filter(User.is_active.is_(active))
    if role:
        query = query.filter(User.role == role)

    total = query.count()

    if order == "created_at":
        query = query.order_by(asc(User.created_at))
    else:
        query = query.order_by(desc(User.created_at))

    page = max(page, 1)
    per_page = max(min(per_page, 50), 1)
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return Pagination(items, total, page, per_page)


def get_user(user_id):
    return db.session.get(User, user_id)


def create_user(payload, allowed_roles=None):
    session = db.session
    is_valid, errors, data = validate_user_payload(payload, session, allowed_roles=allowed_roles)
    if not is_valid:
        return False, None, errors

    password = data.pop("password")
    user = User(**data, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    return True, user, {}


def update_user(user, payload, allowed_roles=None):
    session = db.session
    is_valid, errors, data = validate_user_payload(
        payload,
        session,
        existing_user=user,
        require_password=False,
        allowed_roles=allowed_roles,
    )
    if not is_valid:
        return False, None, errors

    password = data.pop("password", None)
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.password_hash = hash_password(password)

    session.add(user)
    session.commit()
    return True, user, {}


def delete_user(user):
    session = db.session
    session.delete(user)
    session.commit()


def get_allowed_roles_for_admin():
    return (UserRole.PUBLIC, UserRole.EDITOR, UserRole.ADMIN)

# Funcion para crear en seeds
def create_user(**kgwargs):
    user = User(**kgwargs)
    db.session.add(user)
    db.session.commit() 

    return user