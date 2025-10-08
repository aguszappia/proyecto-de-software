from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.core.database import db
from src.core.flags.models import FeatureFlag

MAX_MESSAGE_LENGTH = 150


class FeatureFlagError(ValueError):
    """Errores de validación/negocio para flags."""


def _session() -> Session:
    return db.session


def get_flag(key: str) -> Optional[FeatureFlag]:
    """Devuelve el flag por clave o None si no existe."""
    return _session().query(FeatureFlag).filter_by(key=key).one_or_none()


def list_flags() -> list[FeatureFlag]:
    """Lista todos los flags ordenados alfabéticamente."""
    return _session().query(FeatureFlag).order_by(FeatureFlag.key.asc()).all()

def load_flags() -> dict[str, FeatureFlag]:
    return {flag.key: flag for flag in list_flags()}

def ensure_flag(
    *,
    key: str,
    name: str,
    description: str = "",
    enabled: bool = False,
    message: str = "",
) -> FeatureFlag:
    """
    Garantiza que exista un flag con los datos base.
    Si no existe lo crea sin disparar validaciones extra.
    """
    session = _session()
    flag = session.query(FeatureFlag).filter_by(key=key).one_or_none()
    if flag:
        return flag

    flag = FeatureFlag(
        key=key,
        name=name,
        description=description,
        enabled=enabled,
        message=message or "",
    )
    session.add(flag)
    session.commit()
    session.refresh(flag)
    return flag

def set_flag(
    key: str,
    *,
    enabled: bool,
    message: str,
    user_id: Optional[int],
) -> FeatureFlag:
    """
    Actualiza estado + mensaje del flag y registra auditoría.

    - Si enabled es True → el mensaje es obligatorio y <= MAX_MESSAGE_LENGTH.
    - Si enabled es False → se limpia el mensaje (evita valores viejos).
    """
    session = _session()
    flag = session.query(FeatureFlag).filter_by(key=key).one_or_none()
    if flag is None:
        raise FeatureFlagError(f"No existe el flag '{key}'.")

    clean_message = (message or "").strip()
    if enabled:
        if not clean_message:
            raise FeatureFlagError("El mensaje es obligatorio cuando el flag está activo.")
        if len(clean_message) > MAX_MESSAGE_LENGTH:
            raise FeatureFlagError(
                f"El mensaje no puede superar {MAX_MESSAGE_LENGTH} caracteres."
            )
    else:
        clean_message = ""

    flag.enabled = enabled
    flag.message = clean_message
    flag.updated_by_id = user_id
    flag.updated_at = datetime.now(timezone.utc)

    session.add(flag)
    session.commit()
    session.refresh(flag)
    return flag
