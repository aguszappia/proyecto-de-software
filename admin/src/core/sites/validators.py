"""Validadores y normalizadores para sitios históricos."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Type

from src.core.sites.models import ConservationStatus, SiteCategory


def clean_str(value: Any) -> str:
    """Elimino espacios extra y transformo None en cadena vacía."""
    return (value or "").strip()


def safe_int(value: Any) -> Optional[int]:
    """Intento convertir el valor a int; devuelvo None si falla."""
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def safe_float(value: Any) -> Optional[float]:
    """Intento convertir el valor a float; devuelvo None si falla."""
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def parse_enum(value: str, enum_cls: Type) -> Optional[object]:
    """Busco la opción del enum que coincida con nombre o valor."""
    if not value:
        return None
    for option in enum_cls:
        if value == option.value or value == option.name:
            return option
    return None


def parse_tag_ids(raw_values: Iterable[Any]) -> List[int]:
    """Convierto una colección de ids en enteros válidos."""
    result: List[int] = []
    for raw in raw_values:
        try:
            result.append(int(raw))
        except (TypeError, ValueError):
            continue
    return result


def build_site_payload(form_data: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    """Valido datos de sitios y devuelvo payload limpio junto con errores."""
    get = form_data.get
    getlist = getattr(form_data, "getlist", None)

    if callable(getlist):
        raw_tag_ids = getlist("tags")
    else:
        candidate = get("tags", [])
        if isinstance(candidate, (list, tuple, set)):
            raw_tag_ids = list(candidate)
        elif candidate in (None, ""):
            raw_tag_ids = []
        else:
            raw_tag_ids = [candidate]

    values = {
        "name": clean_str(get("name")),
        "short_description": clean_str(get("short_description")),
        "full_description": clean_str(get("full_description")),
        "city": clean_str(get("city")),
        "province": clean_str(get("province")),
        "conservation_status": clean_str(get("conservation_status")),
        "category": clean_str(get("category")),
        "inaguration_year": clean_str(get("inaguration_year")),
        "latitude": clean_str(get("latitude")),
        "longitude": clean_str(get("longitude")),
        "is_visible": get("is_visible"),
        "tag_ids": list(raw_tag_ids),
    }

    errors: List[str] = []
    required_messages = {
        "name": "El nombre es obligatorio.",
        "short_description": "La descripción breve es obligatoria.",
        "full_description": "La descripción completa es obligatoria.",
        "city": "La ciudad es obligatoria.",
        "province": "La provincia es obligatoria.",
    }
    for field, message in required_messages.items():
        if not values[field]:
            errors.append(message)

    latitude = safe_float(values["latitude"])
    longitude = safe_float(values["longitude"])
    if latitude is None or longitude is None:
        errors.append("Seleccioná una ubicación en el mapa.")

    status_enum = parse_enum(values["conservation_status"], ConservationStatus)
    if status_enum is None:
        errors.append("Elegí un estado de conservación válido.")

    category_enum = parse_enum(values["category"], SiteCategory)
    if category_enum is None:
        errors.append("Elegí una categoría válida.")

    inaguration_year = safe_int(values["inaguration_year"])
    if inaguration_year is None:
        errors.append("Ingresá un año de inauguración válido.")

    tag_ids = parse_tag_ids(values["tag_ids"])

    payload = {
        "name": values["name"],
        "short_description": values["short_description"],
        "full_description": values["full_description"],
        "city": values["city"],
        "province": values["province"],
        "latitude": latitude,
        "longitude": longitude,
        "conservation_status": status_enum,
        "category": category_enum,
        "inaguration_year": inaguration_year,
        "is_visible": values["is_visible"] == "on",
        "tag_ids": tag_ids,
    }

    form_values = {
        **values,
        "is_visible": values["is_visible"] == "on",
        "tag_ids": tag_ids,
    }

    return payload, form_values, errors


__all__ = [
    "build_site_payload",
    "clean_str",
    "parse_enum",
    "parse_tag_ids",
    "safe_float",
    "safe_int",
]
