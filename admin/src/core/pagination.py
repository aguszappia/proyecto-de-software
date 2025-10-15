"""Defino un contenedor genérico para resultados paginados."""

from __future__ import annotations

from typing import Generic, Sequence, TypeVar


T = TypeVar("T")


class Pagination(Generic[T]):
    """Guardo la página actual, el total y los ítems que ya busqué."""

    def __init__(self, items: Sequence[T], total: int, page: int, per_page: int) -> None:
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page

    @property
    def pages(self) -> int:
        """Calculo cuántas páginas completas tengo disponibles."""
        if self.per_page <= 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_prev(self) -> bool:
        """Indico si puedo ir a la página anterior."""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """Indico si queda una página siguiente."""
        return self.page < self.pages
