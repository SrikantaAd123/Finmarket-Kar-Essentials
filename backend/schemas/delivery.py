
"""Delivery management schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from backend.schemas.common import BaseSchema


# =========================================================
# DELIVERY STATUS TYPES
# =========================================================

ShipmentStatus = Literal[
    "created",
    "assigned",
    "picked_up",
    "in_transit",
    "out_for_delivery",
    "delivered",
    "failed",
    "returned",
    "cancelled",
]


# =========================================================
# DELIVERY PARTNER SCHEMAS
# =========================================================

class DeliveryPartnerCreate(BaseSchema):
    """Request to register a delivery partner."""

    partner_code: str = Field(min_length=2, max_length=60)

    full_name: str = Field(min_length=2, max_length=150)

    phone: str = Field(min_length=10, max_length=25)

    email: str | None = Field(default=None, max_length=255)

    vehicle_number: str | None = Field(default=None, max_length=30)

    vehicle_type: str | None = Field(default=None, max_length=50)


class DeliveryPartnerUpdate(BaseSchema):
    """Request to update delivery partner information."""

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

    email: str | None = Field(
        default=None,
        max_length=255,
    )

    vehicle_number: str | None = Field(
        default=None,
        max_length=30,
    )

    vehicle_type: str | None = Field(
        default=None,
        max_length=50,
    )

    is_available: bool | None = None

    is_active: bool | None = None


class DeliveryPartnerResponse(BaseSchema):
    """Delivery partner information returned by the API."""

    id: int = Field(gt=0)

    partner_code: str

    full_name: str

    phone: str

    email: str | None = None

    vehicle_number: str | None = None

    vehicle_type: str | None = None

    is_available: bool

    is_active: bool

    rating: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        le=Decimal("5.00"),
        max_digits=4,
        decimal_places=2,
    )

    created_at: datetime | None = None


# =========================================================
# SERVICEABLE PINCODE SCHEMAS
# =========================================================

class ServiceablePincodeCreate(BaseSchema):
    """Request to configure a serviceable delivery pincode."""

    pincode: str = Field(
        min_length=4,
        max_length=10,
    )

    city: str = Field(
        min_length=2,
        max_length=100,
    )

    state: str = Field(
        min_length=2,
        max_length=100,
    )

    country: str = Field(
        default="India",
        max_length=100,
    )

    delivery_fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    minimum_order_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    estimated_delivery_days: int = Field(
        default=1,
        ge=0,
        le=90,
    )

    is_cod_available: bool = True


class ServiceablePincodeUpdate(BaseSchema):
    """Request to update pincode serviceability."""

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

    delivery_fee: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    minimum_order_amount: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    estimated_delivery_days: int | None = Field(
        default=None,
        ge=0,
        le=90,
    )

    is_cod_available: bool | None = None

    is_active: bool | None = None


class ServiceablePincodeResponse(BaseSchema):
    """Pincode serviceability information."""

    id: int = Field(gt=0)

    pincode: str

    city: str

    state: str

    country: str

    delivery_fee: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    minimum_order_amount: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    estimated_delivery_days: int = Field(
        ge=0,
        le=90,
    )

    is_cod_available: bool

    is_active: bool


class PincodeCheckRequest(BaseSchema):
    """Customer request to check delivery availability."""

    pincode: str = Field(
        min_length=4,
        max_length=10,
    )


class PincodeCheckResponse(BaseSchema):
    """Delivery availability result."""

    pincode: str

    is_serviceable: bool

    estimated_delivery_days: int | None = Field(
        default=None,
        ge=0,
        le=90,
    )

    delivery_fee: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    minimum_order_amount: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    is_cod_available: bool = False

    message: str


# =========================================================
# DELIVERY SLOT SCHEMAS
# =========================================================

class DeliverySlotCreate(BaseSchema):
    """Request to create a delivery time slot."""

    delivery_date: date

    start_time: time

    end_time: time

    capacity: int = Field(
        gt=0,
        le=10000,
    )

    @model_validator(mode="after")
    def validate_slot(self):
        if self.end_time <= self.start_time:
            raise ValueError(
                "Delivery slot end time must be after start time."
            )

        return self


class DeliverySlotUpdate(BaseSchema):
    """Request to update a delivery slot."""

    start_time: time | None = None

    end_time: time | None = None

    capacity: int | None = Field(
        default=None,
        gt=0,
        le=10000,
    )

    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_slot_times(self):
        # Validate when both times are supplied.
        # When only one is supplied, the service must compare
        # it against the existing database value.
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError(
                "Delivery slot end time must be after start time."
            )

        return self


class DeliverySlotResponse(BaseSchema):
    """Delivery slot information."""

    id: int = Field(gt=0)

    delivery_date: date

    start_time: time

    end_time: time

    capacity: int = Field(ge=1)

    reserved_count: int = Field(ge=0)

    is_active: bool

    @property
    def available_capacity(self) -> int:
        """Return remaining delivery slot capacity."""
        return max(0, self.capacity - self.reserved_count)


# =========================================================
# SHIPMENT SCHEMAS
# =========================================================

class ShipmentCreate(BaseSchema):
    """Request to create a shipment for an order."""

    order_id: int = Field(gt=0)

    shipment_number: str = Field(
        min_length=2,
        max_length=60,
    )

    delivery_partner_id: int | None = Field(
        default=None,
        gt=0,
    )

    delivery_slot_id: int | None = Field(
        default=None,
        gt=0,
    )

    estimated_delivery_at: datetime | None = None

    delivery_notes: str | None = Field(
        default=None,
        max_length=2000,
    )


class ShipmentAssignmentRequest(BaseSchema):
    """Request to assign a delivery partner to a shipment."""

    delivery_partner_id: int = Field(gt=0)


class ShipmentStatusUpdate(BaseSchema):
    """Request to update shipment status."""

    status: ShipmentStatus

    description: str = Field(
        min_length=3,
        max_length=2000,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )


class ShipmentResponse(BaseSchema):
    """Shipment details returned by the API."""

    id: int = Field(gt=0)

    shipment_number: str

    order_id: int = Field(gt=0)

    delivery_partner_id: int | None = Field(
        default=None,
        gt=0,
    )

    delivery_slot_id: int | None = Field(
        default=None,
        gt=0,
    )

    status: ShipmentStatus

    tracking_number: str | None = None

    estimated_delivery_at: datetime | None = None

    picked_up_at: datetime | None = None

    delivered_at: datetime | None = None

    delivery_notes: str | None = None

    delivery_proof_url: str | None = None

    failure_reason: str | None = None

    created_at: datetime | None = None


# =========================================================
# SHIPMENT TRACKING SCHEMAS
# =========================================================

class ShipmentTrackingCreate(BaseSchema):
    """Request to add a shipment tracking event."""

    status: ShipmentStatus

    description: str = Field(
        min_length=3,
        max_length=2000,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    updated_by: str | None = Field(
        default=None,
        max_length=150,
    )

    event_time: datetime | None = None


class ShipmentTrackingResponse(BaseSchema):
    """Shipment tracking event returned by the API."""

    id: int = Field(gt=0)

    shipment_id: int = Field(gt=0)

    status: ShipmentStatus

    description: str

    location: str | None = None

    updated_by: str | None = None

    event_time: datetime | None = None

    created_at: datetime | None = None


class ShipmentTrackingListResponse(BaseSchema):
    """Complete shipment tracking history."""

    shipment_id: int = Field(gt=0)

    events: list[ShipmentTrackingResponse] = Field(
        default_factory=list,
    )

    total: int = Field(
        default=0,
        ge=0,
    )


__all__ = [
    "ShipmentStatus",
    "DeliveryPartnerCreate",
    "DeliveryPartnerUpdate",
    "DeliveryPartnerResponse",
    "ServiceablePincodeCreate",
    "ServiceablePincodeUpdate",
    "ServiceablePincodeResponse",
    "PincodeCheckRequest",
    "PincodeCheckResponse",
    "DeliverySlotCreate",
    "DeliverySlotUpdate",
    "DeliverySlotResponse",
    "ShipmentCreate",
    "ShipmentAssignmentRequest",
    "ShipmentStatusUpdate",
    "ShipmentResponse",
    "ShipmentTrackingCreate",
    "ShipmentTrackingResponse",
    "ShipmentTrackingListResponse",
]
