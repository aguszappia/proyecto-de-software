"""Envuelvo el hashing y la verificación de contraseñas con bcrypt."""

from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """Genero el hash bcrypt para la contraseña enviada."""
    if not plain:
        raise ValueError("Password must not be empty")
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Comparo la contraseña plana con el hash guardado."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False
