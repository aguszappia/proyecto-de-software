"""Valido y normalizo los datos que recibo para usuarios."""

import re

from src.core.users import UserRole, DEFAULT_USER_ROLE
from src.core.users.models import User

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _add_error(errors, field, message):
    """Acumulo el mensaje de error en el campo indicado."""
    errors.setdefault(field, []).append(message)


def _normalize_bool(value):
    """Convierto distintos formatos a booleano estándar."""
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "si", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    raise ValueError


def _normalize_role(value, allowed_roles):
    """Confirmo que el rol esté permitido y devuelvo su slug."""
    if value is None:
        return DEFAULT_USER_ROLE.value
    role_value = value.strip().lower()
    if role_value in allowed_roles:
        return role_value
    raise ValueError


def validate_user_payload(payload, session, existing_user=None, require_password=True, allowed_roles=None):
    """Valido campos del usuario."""
    errors = {}
    clean = {}

    email = (payload.get("email") or "").strip().lower()
    if not email:
        _add_error(errors, "email", "El email es obligatorio.")
    elif not _EMAIL_REGEX.match(email):
        _add_error(errors, "email", "El formato de email no es válido.")
    else:
        clean["email"] = email

    first_name = (payload.get("first_name") or "").strip()
    if not first_name:
        _add_error(errors, "first_name", "El nombre es obligatorio.")
    else:
        clean["first_name"] = first_name

    last_name = (payload.get("last_name") or "").strip()
    if not last_name:
        _add_error(errors, "last_name", "El apellido es obligatorio.")
    else:
        clean["last_name"] = last_name

    password = payload.get("password")
    if password:
        password_text = str(password)
        if len(password_text) < 8:
            _add_error(errors, "password", "La contraseña debe tener al menos 8 caracteres.")
        else:
            clean["password"] = password_text
    elif require_password:
        _add_error(errors, "password", "La contraseña es obligatoria.")

    try:
        clean["is_active"] = _normalize_bool(payload.get("is_active"))
    except ValueError:
        _add_error(errors, "is_active", "El estado activo no es válido.")

    allowed = {role.value for role in (allowed_roles or UserRole)}
    try:
        clean["role"] = _normalize_role(payload.get("role"), allowed)
    except ValueError:
        _add_error(errors, "role", f"El rol debe ser uno de: {', '.join(sorted(allowed))}.")

    if "email" in clean:
        query = session.query(User.id).filter_by(email=clean["email"])
        if existing_user is not None:
            query = query.filter(User.id != existing_user.id)
        if query.first() is not None:
            _add_error(errors, "email", "El email ya está registrado.")

    is_valid = not errors
    return is_valid, errors, clean
