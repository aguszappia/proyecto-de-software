from __future__ import annotations

from typing import Generic, Sequence, TypeVar


T = TypeVar("T")


class Pagination(Generic[T]):
    def __init__(self, items: Sequence[T], total: int, page: int, per_page: int) -> None:
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page

    @property
    def pages(self) -> int:
        if self.per_page <= 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages
