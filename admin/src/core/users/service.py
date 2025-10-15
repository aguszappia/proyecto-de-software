"""Servicios CRUD simples para usuarios y roles."""

from sqlalchemy import asc, desc
from sqlalchemy.orm import joinedload

from src.core.database import db
from src.core.pagination import Pagination
from src.core.security.passwords import hash_password
from src.core.users import UserRole
from src.core.users.models import Role, User
from src.core.users.validators import validate_user_payload


def list_users(page=1, per_page=25, search_email=None, active=None, role=None, order="-created_at"):
    """Armo la consulta paginada con filtros de email, estado y rol."""
    session = db.session
    query = session.query(User).options(joinedload(User.role_rel))

    if search_email:
        query = query.filter(User.email.ilike(f"%{search_email.lower()}%"))
    if active is not None:
        query = query.filter(User.is_active.is_(active))
    if role:
        query = query.join(User.role_rel).filter(Role.slug == role)

    total = query.count()

    if order == "created_at":
        query = query.order_by(asc(User.created_at))
    else:
        query = query.order_by(desc(User.created_at))

    page = max(page, 1)
    per_page = max(min(per_page, 50), 1)
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return Pagination(items, total, page, per_page)


def find_user_by_email(email: str) -> User | None:
    """Busco el usuario por email sin importar mayúsculas."""
    if not email:
        return None
    clean_email = email.strip().lower()
    return db.session.query(User).filter(User.email.ilike(clean_email)).first()


def get_user(user_id):
    """Recupero el usuario por id desde la base."""
    return db.session.get(User, user_id)


def create_user(payload, allowed_roles=None):
    """Valido el payload, hasheo la contraseña y creo el usuario."""
    session = db.session
    is_valid, errors, data = validate_user_payload(payload, session, allowed_roles=allowed_roles)
    if not is_valid:
        return False, None, errors
    
    role_slug = data.pop("role")
    role = _get_role_by_slug(session, role_slug)
    if not role:
        return False, None, {"role": "El rol seleccionado no existe."}
    
    password = data.pop("password")
    user = User(**data, password_hash=hash_password(password), role_rel=role)
    session.add(user)
    session.commit()
    return True, user, {}


def update_user(user, payload, allowed_roles=None):
    """Actualizo datos del usuario respetando validaciones de rol y estado."""
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
    
    # No permitir desactivar un usuario con rol Administrador o System Admin
    if "is_active" in data and data["is_active"] is False and (
        user.role in {UserRole.ADMIN.value, UserRole.SYSADMIN.value}
    ):
        errors = {"is_active": "No se puede desactivar a un usuario con rol Administrador."}
        return False, None, errors
    
    role_slug = data.pop("role", None)
    password = data.pop("password", None)
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.password_hash = hash_password(password)
    if role_slug:
        role = _get_role_by_slug(session, role_slug)
        if not role:
            return False, None, {"role": "El rol seleccionado no existe."}
        user.role_rel = role

    session.add(user)
    session.commit()
    return True, user, {}


def delete_user(user) -> bool:
    """Borro al usuario salvo que sea admin o sysadmin."""
    if user.role in {UserRole.ADMIN.value, UserRole.SYSADMIN.value}:
        return False
    session = db.session
    session.delete(user)
    session.commit()
    return True

def deactivate_user(user):
    """Desactivo al usuario salvo que sea admin o sysadmin."""
    if user.role in {UserRole.ADMIN.value, UserRole.SYSADMIN.value}:
        raise ValueError("No se puede desactivar a un usuario con rol Administrador o System Admin.")
    user.is_active = False
    db.session.add(user)
    db.session.commit()
    return user


def activate_user(user):
    """Activo nuevamente al usuario elegido."""
    user.is_active = True
    db.session.add(user)
    db.session.commit()
    return user

def get_allowed_roles_for_admin():
    """Expongo los roles que puede asignar un admin."""
    return (UserRole.PUBLIC, UserRole.EDITOR, UserRole.ADMIN)


def _get_role_by_slug(session, slug):
    """Resuelvo el rol por slug dentro de la sesión dada."""
    return session.query(Role).filter(Role.slug == slug).one_or_none()


def ensure_role(slug: str, name: str) -> Role:
    """Creo el rol si falta o actualizo el nombre guardado."""
    session = db.session
    role = session.query(Role).filter(Role.slug == slug).one_or_none()
    if role:
        if name and role.name != name:
            role.name = name
            session.add(role)
            session.commit()
        return role

    role = Role(slug=slug, name=name)
    session.add(role)
    session.commit()
    return role


def get_role_by_slug(slug: str) -> Role | None:
    """Busco el rol por slug usando la sesión global."""
    return db.session.query(Role).filter(Role.slug == slug).one_or_none()


def list_roles():
    """Devuelvo todos los roles ordenados por slug."""
    return db.session.query(Role).order_by(Role.slug).all()