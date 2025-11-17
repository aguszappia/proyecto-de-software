from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.core.database import db
from src.core.flags.models import FeatureFlag

MAX_MESSAGE_LENGTH = 150


class FeatureFlagError(ValueError):
    """Uso esta excepción para avisar errores con flags."""


def _session() -> Session:
    """Obtengo la sesión actual para operar sobre los flags."""
    return db.session


def get_flag(key: str) -> Optional[FeatureFlag]:
    """Busco un flag por clave y devuelvo None si no lo encuentro."""
    return _session().query(FeatureFlag).filter_by(key=key).one_or_none()


def list_flags() -> list[FeatureFlag]:
    """Listo todos los flags ordenados alfabéticamente por clave."""
    return _session().query(FeatureFlag).order_by(FeatureFlag.key.asc()).all()

def load_flags() -> dict[str, FeatureFlag]:
    """Armo un diccionario clave-flag para cachearlo en memoria."""
    return {flag.key: flag for flag in list_flags()}

def ensure_flag(
    *,
    key: str,
    name: str,
    description: str = "",
    enabled: bool = False,
    message: str = "",
) -> FeatureFlag:
    """Creo el flag si falta y devuelvo la instancia persistida."""
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
    preserve_message_when_disabled: bool = False,
    require_message_when_enabled: bool = True,
) -> FeatureFlag:
    """Actualizo estado, mensaje y auditoría del flag indicado."""
    session = _session()
    flag = session.query(FeatureFlag).filter_by(key=key).one_or_none()
    if flag is None:
        raise FeatureFlagError(f"No existe el flag '{key}'.")

    clean_message = (message or "").strip()
    if enabled:
        if require_message_when_enabled and not clean_message:
            raise FeatureFlagError("El mensaje es obligatorio cuando el flag está activo.")
        if clean_message and len(clean_message) > MAX_MESSAGE_LENGTH:
            raise FeatureFlagError(
                f"El mensaje no puede superar {MAX_MESSAGE_LENGTH} caracteres."
            )
    else:
        if not preserve_message_when_disabled:
            clean_message = ""
        elif len(clean_message) > MAX_MESSAGE_LENGTH:
            raise FeatureFlagError(
                f"El mensaje no puede superar {MAX_MESSAGE_LENGTH} caracteres."
            )

    flag.enabled = enabled
    flag.message = clean_message
    flag.updated_by_id = user_id
    flag.updated_at = datetime.now(timezone.utc)

    session.add(flag)
    session.commit()
    session.refresh(flag)
    return flag
