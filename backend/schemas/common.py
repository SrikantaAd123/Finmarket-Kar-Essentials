
"""Common Pydantic schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base configuration shared by API schemas."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class TimestampSchema(BaseSchema):
    """Common creation and update timestamps."""

    created_at: datetime | None = None
    updated_at: datetime | None = None


class IDSchema(BaseSchema):
    """Common integer identifier."""

    id: int = Field(gt=0)


class PaginationParams(BaseSchema):
    """Parameters for paginated API requests."""

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class PaginationMetadata(BaseSchema):
    """Pagination information returned by APIs."""

    page: int = Field(ge=1)

    page_size: int = Field(
        ge=1,
        le=100,
    )

    total_items: int = Field(ge=0)

    total_pages: int = Field(ge=0)

    has_next: bool

    has_previous: bool


class PaginatedResponse(BaseSchema, Generic[T]):
    """Reusable paginated API response."""

    items: list[T]

    pagination: PaginationMetadata


class MessageResponse(BaseSchema):
    """Simple success or informational response."""

    message: str

    success: bool = True


class ErrorDetail(BaseSchema):
    """Structured API error information."""

    code: str

    message: str

    field: str | None = None


class ErrorResponse(BaseSchema):
    """Standard API error response."""

    success: bool = False

    message: str

    errors: list[ErrorDetail] = Field(
        default_factory=list,
    )


class HealthResponse(BaseSchema):
    """Application health response."""

    status: str

    service: str

    version: str | None = None


__all__ = [
    "BaseSchema",
    "TimestampSchema",
    "IDSchema",
    "PaginationParams",
    "PaginationMetadata",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
]
