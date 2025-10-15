"""Funciones auxiliares para el manejo de sitios históricos."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Dict, List, Optional, Tuple, Type

from src.core.sites.models import ConservationStatus, SiteCategory

PROVINCES: List[str] = [
    "Buenos Aires",
    "Ciudad Autónoma de Buenos Aires",
    "Catamarca",
    "Chaco",
    "Chubut",
    "Córdoba",
    "Corrientes",
    "Entre Ríos",
    "Formosa",
    "Jujuy",
    "La Pampa",
    "La Rioja",
    "Mendoza",
    "Misiones",
    "Neuquén",
    "Río Negro",
    "Salta",
    "San Juan",
    "San Luis",
    "Santa Cruz",
    "Santa Fe",
    "Santiago del Estero",
    "Tierra del Fuego, Antártida e Islas del Atlántico Sur",
    "Tucumán",
]


def clean_str(value: Optional[str]) -> str:
    """Limpio la cadena devolviendo vacío si viene None."""

    return (value or "").strip()


def safe_int(value: Optional[str]) -> Optional[int]:
    """Intento convertir el valor a int o devuelvo None si falla."""

    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def safe_float(value: Optional[str]) -> Optional[float]:
    """Intento convertir a float para coordenadas o devuelvo None."""

    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def parse_date(value: str, *, end_of_day: bool = False) -> Optional[datetime]:
    """Transformo una fecha YYYY-MM-DD en datetime UTC."""

    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    chosen_time = time.max if end_of_day else time.min
    return datetime.combine(parsed, chosen_time).replace(tzinfo=timezone.utc)


def parse_enum(value: str, enum_cls: Type) -> Optional[object]:
    """Busco la opción del enum que coincida con nombre o valor."""

    if not value:
        return None
    for option in enum_cls:
        if value == option.value or value == option.name:
            return option
    return None


def parse_tag_ids(raw_values: List[str]) -> List[int]:
    """Convierto la lista de ids en enteros válidos."""

    result: List[int] = []
    for raw in raw_values:
        try:
            result.append(int(raw))
        except (TypeError, ValueError):
            continue
    return result


def empty_site_form() -> Dict[str, object]:
    """Preparo la estructura vacía para renderizar el formulario."""

    return {
        "name": "",
        "short_description": "",
        "full_description": "",
        "city": "",
        "province": "",
        "conservation_status": "",
        "category": "",
        "inaguration_year": "",
        "latitude": "",
        "longitude": "",
        "is_visible": False,
        "tag_ids": [],
    }


def build_site_payload(form) -> Tuple[Dict[str, object], Dict[str, object], List[str]]:
    """Valido los datos del formulario y devuelvo payload, valores y errores."""

    values = {
        "name": clean_str(form.get("name")),
        "short_description": clean_str(form.get("short_description")),
        "full_description": clean_str(form.get("full_description")),
        "city": clean_str(form.get("city")),
        "province": clean_str(form.get("province")),
        "conservation_status": clean_str(form.get("conservation_status")),
        "category": clean_str(form.get("category")),
        "inaguration_year": clean_str(form.get("inaguration_year")),
        "latitude": clean_str(form.get("latitude")),
        "longitude": clean_str(form.get("longitude")),
        "is_visible": form.get("is_visible"),
        "tag_ids": form.getlist("tags"),
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

    year = safe_int(values["inaguration_year"])
    if year is None:
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
        "inaguration_year": year,
        "is_visible": values["is_visible"] == "on",
        "tag_ids": tag_ids,
    }

    form_values = {
        **values,
        "is_visible": values["is_visible"] == "on",
        "tag_ids": tag_ids,
    }

    return payload, form_values, errors
