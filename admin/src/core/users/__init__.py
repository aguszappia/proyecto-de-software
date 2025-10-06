"""Core user domain package."""

from enum import StrEnum


class UserRole(StrEnum):
    PUBLIC = "public"
    EDITOR = "editor"
    ADMIN = "admin"
    SYSADMIN = "sysadmin"


DEFAULT_USER_ROLE = UserRole.PUBLIC


__all__ = ["UserRole", "DEFAULT_USER_ROLE"]
