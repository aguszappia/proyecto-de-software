"""Utilidades de presentación para vistas de sitios históricos."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Dict, List, Optional

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
        "cover_image_preview": "",
    }
