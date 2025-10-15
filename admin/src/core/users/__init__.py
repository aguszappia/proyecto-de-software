"""Defino roles de usuarios y valores por defecto."""

from enum import StrEnum


class UserRole(StrEnum):
    """Enum donde defino los roles posibles del sistema."""

    PUBLIC = "public"
    EDITOR = "editor"
    ADMIN = "admin"
    SYSADMIN = "sysadmin"


DEFAULT_USER_ROLE = UserRole.PUBLIC


__all__ = ["UserRole", "DEFAULT_USER_ROLE"]
