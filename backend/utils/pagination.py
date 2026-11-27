
"""Pagination utilities."""

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def normalize_pagination(
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> Pagination:
    """Validate and normalize pagination parameters."""
    if page < 1:
        raise ValueError("Page must be at least 1.")

    if page_size < 1:
        raise ValueError("Page size must be at least 1.")

    if max_page_size < 1:
        raise ValueError("Maximum page size must be at least 1.")

    return Pagination(
        page=page,
        page_size=min(page_size, max_page_size),
    )


def build_pagination_metadata(
    total_items: int,
    pagination: Pagination,
) -> dict:
    """Build pagination metadata for API responses."""
    if total_items < 0:
        raise ValueError("Total items cannot be negative.")

    total_pages = ceil(total_items / pagination.page_size)

    return {
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": pagination.page < total_pages,
        "has_previous": pagination.page > 1 and total_pages > 0,
    }
