"""Servicios para crear, asignar y listar permisos."""

from __future__ import annotations

from typing import Iterable, Sequence

from src.core.database import db
from src.core.permissions.models import Permission, RolePermission
from src.core.users import UserRole
from src.core.users.models import Role


class PermissionError(Exception):
    """Uso esta excepción para comunicar errores con permisos."""


def list_permissions(*, module: str | None = None) -> Sequence[Permission]:
    """Devuelvo los permisos filtrando por módulo si hace falta."""
    query = db.session.query(Permission)
    if module:
        query = query.filter(Permission.module == module)
    return query.order_by(Permission.code).all()


def ensure_permission(code: str, *, description: str | None = None) -> Permission:
    """Creo el permiso si falta y normalizo módulo y acción."""
    module, _, action = code.partition("_")
    if not module or not action:
        raise PermissionError("El código de permiso debe seguir el formato modulo_accion.")

    permission = db.session.query(Permission).filter_by(code=code).one_or_none()
    if permission:
        if description is not None and permission.description != description:
            permission.description = description
            db.session.add(permission)
            db.session.commit()
        return permission

    permission = Permission(code=code, module=module, action=action, description=description)
    db.session.add(permission)
    db.session.commit()
    return permission


def assign_permission(role: UserRole | str | Role, permission_code: str, *, assigned_by_id: int | None = None) -> RolePermission:
    """Asigno el permiso al rol evitando duplicados y guardo auditoría básica."""
    permission = db.session.query(Permission).filter_by(code=permission_code).one_or_none()
    if not permission:
        raise PermissionError(f"No existe el permiso «{permission_code}».")

    role_obj = _resolve_role(role)
    existing = (
        db.session.query(RolePermission)
        .filter(RolePermission.role_id == role_obj.id, RolePermission.permission_id == permission.id)
        .one_or_none()
    )
    if existing:
        return existing

    link = RolePermission(role_id=role_obj.id, permission_id=permission.id, assigned_by_id=assigned_by_id)
    db.session.add(link)
    db.session.commit()
    return link


def revoke_permission(role: UserRole | str | Role, permission_code: str) -> bool:
    """Quito el permiso del rol y devuelvo True si existía."""
    permission = db.session.query(Permission).filter_by(code=permission_code).one_or_none()
    if not permission:
        raise PermissionError(f"No existe el permiso «{permission_code}».")

    role_obj = _resolve_role(role)
    deleted = (
        db.session.query(RolePermission)
        .filter(RolePermission.role_id == role_obj.id, RolePermission.permission_id == permission.id)
        .delete()
    )
    if deleted:
        db.session.commit()
        return True
    return False


def list_role_permissions(role: UserRole | str | Role) -> Sequence[Permission]:
    """Obtengo la lista de permisos asociados al rol dado."""
    role_obj = _resolve_role(role)
    query = (
        db.session.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role_obj.id)
        .order_by(Permission.code)
    )
    return query.all()


def bulk_assign(role: UserRole | str | Role, permission_codes: Iterable[str], *, assigned_by_id: int | None = None) -> None:
    """Recorro los códigos recibidos y los asigno en lote al rol."""
    for code in permission_codes:
        assign_permission(role, code, assigned_by_id=assigned_by_id)


def _resolve_role(role: UserRole | str | Role) -> Role:
    """Resuelvo el objeto Role a partir del slug o enum recibido."""
    if isinstance(role, Role):
        return role
    slug = role.value if isinstance(role, UserRole) else str(role)
    role_obj = db.session.query(Role).filter_by(slug=slug).one_or_none()
    if not role_obj:
        raise PermissionError(f"No existe el rol «{slug}».")
    return role_obj
