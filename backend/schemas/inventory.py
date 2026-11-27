
"""Inventory management schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from backend.schemas.common import BaseSchema


# =========================================================
# INVENTORY TYPES
# =========================================================

StockReservationStatus = Literal[
    "active",
    "confirmed",
    "released",
    "expired",
]

StockMovementType = Literal[
    "purchase",
    "sale",
    "return",
    "adjustment",
    "transfer_in",
    "transfer_out",
    "damage",
    "reservation",
    "release",
]

StockDirection = Literal[
    "IN",
    "OUT",
]


# =========================================================
# WAREHOUSE SCHEMAS
# =========================================================

class WarehouseCreate(BaseSchema):
    """Request to register a warehouse."""

    warehouse_code: str = Field(
        min_length=2,
        max_length=60,
    )

    name: str = Field(
        min_length=2,
        max_length=180,
    )

    address_line1: str = Field(
        min_length=3,
        max_length=255,
    )

    address_line2: str | None = Field(
        default=None,
        max_length=255,
    )

    city: str = Field(
        min_length=2,
        max_length=100,
    )

    state: str = Field(
        min_length=2,
        max_length=100,
    )

    pincode: str = Field(
        min_length=4,
        max_length=10,
    )

    country: str = Field(
        default="India",
        max_length=100,
    )

    contact_person: str | None = Field(
        default=None,
        max_length=150,
    )

    contact_phone: str | None = Field(
        default=None,
        max_length=25,
    )


class WarehouseUpdate(BaseSchema):
    """Request to update warehouse information."""

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=180,
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

    pincode: str | None = Field(
        default=None,
        min_length=4,
        max_length=10,
    )

    contact_person: str | None = Field(
        default=None,
        max_length=150,
    )

    contact_phone: str | None = Field(
        default=None,
        max_length=25,
    )

    is_active: bool | None = None


class WarehouseResponse(BaseSchema):
    """Warehouse information returned by the API."""

    id: int = Field(gt=0)

    warehouse_code: str

    name: str

    address_line1: str

    address_line2: str | None = None

    city: str

    state: str

    pincode: str

    country: str

    contact_person: str | None = None

    contact_phone: str | None = None

    is_active: bool

    created_at: datetime | None = None


# =========================================================
# INVENTORY STOCK SCHEMAS
# =========================================================

class InventoryStockCreate(BaseSchema):
    """Request to initialize product stock in a warehouse."""

    product_id: int = Field(gt=0)

    warehouse_id: int = Field(gt=0)

    quantity_on_hand: Decimal = Field(
        default=Decimal("0.000"),
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    reorder_level: Decimal = Field(
        default=Decimal("5.000"),
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )


class InventoryStockResponse(BaseSchema):
    """Current stock information."""

    id: int = Field(gt=0)

    product_id: int = Field(gt=0)

    warehouse_id: int = Field(gt=0)

    quantity_on_hand: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    quantity_reserved: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    reorder_level: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    quantity_available: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    is_low_stock: bool

    created_at: datetime | None = None

    updated_at: datetime | None = None


class StockAdjustmentRequest(BaseSchema):
    """Request to adjust warehouse stock."""

    product_id: int = Field(gt=0)

    warehouse_id: int = Field(gt=0)

    direction: StockDirection

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    reason: str = Field(
        min_length=5,
        max_length=1000,
    )


# =========================================================
# STOCK RESERVATION SCHEMAS
# =========================================================

class StockReservationCreate(BaseSchema):
    """Request to reserve stock for an order."""

    stock_id: int = Field(gt=0)

    warehouse_id: int = Field(gt=0)

    order_id: int | None = Field(
        default=None,
        gt=0,
    )

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    expires_at: datetime | None = None


class StockReservationUpdate(BaseSchema):
    """Request to change a stock reservation's state."""

    status: StockReservationStatus


class StockReservationResponse(BaseSchema):
    """Stock reservation details."""

    id: int = Field(gt=0)

    stock_id: int = Field(gt=0)

    warehouse_id: int = Field(gt=0)

    order_id: int | None = Field(
        default=None,
        gt=0,
    )

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    status: StockReservationStatus

    expires_at: datetime | None = None

    confirmed_at: datetime | None = None

    released_at: datetime | None = None

    created_at: datetime | None = None


# =========================================================
# STOCK MOVEMENT SCHEMAS
# =========================================================

class StockMovementCreate(BaseSchema):
    """Request to record an inventory movement."""

    product_id: int = Field(gt=0)

    warehouse_id: int = Field(gt=0)

    movement_type: StockMovementType

    direction: StockDirection

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    reference_type: str | None = Field(
        default=None,
        max_length=50,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )


class StockMovementResponse(BaseSchema):
    """Inventory movement history record."""

    id: int = Field(gt=0)

    product_id: int = Field(gt=0)

    warehouse_id: int = Field(gt=0)

    movement_type: StockMovementType

    direction: StockDirection

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    reference_type: str | None = None

    reference_id: str | None = None

    notes: str | None = None

    performed_by: str | None = None

    created_at: datetime | None = None


# =========================================================
# INVENTORY REPORT SCHEMAS
# =========================================================

class LowStockItemResponse(BaseSchema):
    """Products whose available stock reached reorder level."""

    product_id: int = Field(gt=0)

    warehouse_id: int = Field(gt=0)

    quantity_on_hand: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    quantity_reserved: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    quantity_available: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )

    reorder_level: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=12,
        decimal_places=3,
    )


class InventorySummaryResponse(BaseSchema):
    """Warehouse inventory summary."""

    warehouse_id: int = Field(gt=0)

    total_products: int = Field(ge=0)

    low_stock_products: int = Field(ge=0)

    total_quantity_available: Decimal = Field(
        ge=Decimal("0.000"),
        max_digits=14,
        decimal_places=3,
    )

    low_stock_items: list[LowStockItemResponse] = Field(
        default_factory=list,
    )


__all__ = [
    "StockReservationStatus",
    "StockMovementType",
    "StockDirection",
    "WarehouseCreate",
    "WarehouseUpdate",
    "WarehouseResponse",
    "InventoryStockCreate",
    "InventoryStockResponse",
    "StockAdjustmentRequest",
    "StockReservationCreate",
    "StockReservationUpdate",
    "StockReservationResponse",
    "StockMovementCreate",
    "StockMovementResponse",
    "LowStockItemResponse",
    "InventorySummaryResponse",
]
