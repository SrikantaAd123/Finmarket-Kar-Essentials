
"""Customer and address schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from backend.schemas.common import (
    BaseSchema,
    TimestampSchema,
)


# =========================================================
# CUSTOMER PROFILE SCHEMAS
# =========================================================

class CustomerProfileUpdate(BaseSchema):
    """Request schema for updating a customer profile."""

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    phone: str | None = Field(
        default=None,
        min_length=10,
        max_length=25,
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize phone numbers."""
        if value is not None:
            value = value.strip()

            if not value:
                raise ValueError("Phone number cannot be empty.")

        return value


class CustomerProfileResponse(TimestampSchema):
    """Customer profile information returned by the API."""

    id: int = Field(gt=0)

    full_name: str

    email: str

    phone: str | None = None

    is_active: bool


# =========================================================
# CUSTOMER ADDRESS SCHEMAS
# =========================================================

class CustomerAddressBase(BaseSchema):
    """Common customer address fields."""

    label: str = Field(
        default="Home",
        min_length=2,
        max_length=50,
    )

    recipient_name: str = Field(
        min_length=2,
        max_length=150,
    )

    phone: str = Field(
        min_length=10,
        max_length=25,
    )

    address_line1: str = Field(
        min_length=3,
        max_length=255,
    )

    address_line2: str | None = Field(
        default=None,
        max_length=255,
    )

    landmark: str | None = Field(
        default=None,
        max_length=180,
    )

    city: str = Field(
        min_length=2,
        max_length=100,
    )

    state: str = Field(
        min_length=2,
        max_length=100,
    )

    postal_code: str = Field(
        min_length=4,
        max_length=20,
    )

    country: str = Field(
        default="India",
        min_length=2,
        max_length=100,
    )

    @field_validator("phone")
    @classmethod
    def validate_address_phone(cls, value: str) -> str:
        """Normalize address phone numbers."""
        value = value.strip()

        if not value:
            raise ValueError("Phone number cannot be empty.")

        return value

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        """Normalize postal codes."""
        value = value.strip()

        if not value:
            raise ValueError("Postal code cannot be empty.")

        return value


class CustomerAddressCreate(CustomerAddressBase):
    """Request schema for creating a customer address."""

    is_default: bool = False


class CustomerAddressUpdate(BaseSchema):
    """Request schema for partially updating an address."""

    label: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    recipient_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    phone: str | None = Field(
        default=None,
        min_length=10,
        max_length=25,
    )

    address_line1: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
    )

    address_line2: str | None = Field(
        default=None,
        max_length=255,
    )

    landmark: str | None = Field(
        default=None,
        max_length=180,
    )

    city: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    state: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    postal_code: str | None = Field(
        default=None,
        min_length=4,
        max_length=20,
    )

    country: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    is_default: bool | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize an optional phone number."""
        if value is not None:
            value = value.strip()

            if not value:
                raise ValueError("Phone number cannot be empty.")

        return value

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize an optional postal code."""
        if value is not None:
            value = value.strip()

            if not value:
                raise ValueError("Postal code cannot be empty.")

        return value


class CustomerAddressResponse(CustomerAddressBase):
    """Saved customer address returned by the API."""

    id: int = Field(gt=0)

    customer_id: int = Field(gt=0)

    is_default: bool

    created_at: datetime | None = None

    updated_at: datetime | None = None


class CustomerAddressListResponse(BaseSchema):
    """Response containing all customer addresses."""

    items: list[CustomerAddressResponse] = Field(
        default_factory=list,
    )

    total: int = Field(
        default=0,
        ge=0,
    )


__all__ = [
    "CustomerProfileUpdate",
    "CustomerProfileResponse",
    "CustomerAddressBase",
    "CustomerAddressCreate",
    "CustomerAddressUpdate",
    "CustomerAddressResponse",
    "CustomerAddressListResponse",
]
