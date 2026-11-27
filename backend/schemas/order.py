
"""Order management schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from backend.schemas.common import (
    BaseSchema,
    TimestampSchema,
)


# =========================================================
# ORDER ENUMERATIONS
# =========================================================

OrderStatus = Literal[
    "pending",
    "confirmed",
    "processing",
    "packed",
    "shipped",
    "out_for_delivery",
    "delivered",
    "cancelled",
    "returned",
]

PaymentStatus = Literal[
    "pending",
    "paid",
    "failed",
    "refunded",
    "partially_refunded",
]

PaymentMethod = Literal[
    "razorpay",
    "cod",
]


# =========================================================
# CHECKOUT REQUEST
# =========================================================

class OrderCheckoutRequest(BaseSchema):
    """Customer checkout request.

    The frontend supplies address selections and payment method.
    The backend calculates all monetary amounts independently.
    """

    shipping_address_id: int = Field(gt=0)

    billing_address_id: int | None = Field(
        default=None,
        gt=0,
    )

    payment_method: PaymentMethod

    customer_notes: str | None = Field(
        default=None,
        max_length=2000,
    )


# =========================================================
# ORDER ITEM SCHEMAS
# =========================================================

class OrderItemResponse(BaseSchema):
    """Individual product purchased in an order."""

    id: int = Field(gt=0)

    product_id: int | None = Field(
        default=None,
        gt=0,
    )

    product_name: str

    product_sku: str

    quantity: int = Field(ge=1)

    unit_price: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    line_total: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )


# =========================================================
# ORDER ADDRESS SNAPSHOT
# =========================================================

class OrderAddressResponse(BaseSchema):
    """Address snapshot stored at checkout."""

    recipient_name: str

    phone: str

    address_line1: str

    address_line2: str | None = None

    city: str

    state: str

    postal_code: str

    country: str


# =========================================================
# ORDER TRACKING SCHEMAS
# =========================================================

class OrderTrackingResponse(BaseSchema):
    """Individual order status history event."""

    id: int = Field(gt=0)

    status: OrderStatus

    title: str

    description: str | None = None

    location: str | None = None

    updated_by: str | None = None

    created_at: datetime | None = None


# =========================================================
# ORDER RESPONSE
# =========================================================

class OrderResponse(TimestampSchema):
    """Complete order information returned to the customer."""

    id: int = Field(gt=0)

    order_number: str

    customer_id: int = Field(gt=0)

    status: OrderStatus

    payment_status: PaymentStatus

    payment_method: PaymentMethod

    currency: str = "INR"

    subtotal: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    tax_amount: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    delivery_fee: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    discount_amount: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    total_amount: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    customer_notes: str | None = None

    cancellation_reason: str | None = None

    shipping_address: OrderAddressResponse

    billing_address: OrderAddressResponse | None = None

    items: list[OrderItemResponse] = Field(
        default_factory=list,
    )

    tracking_events: list[OrderTrackingResponse] = Field(
        default_factory=list,
    )


# =========================================================
# ORDER LIST RESPONSE
# =========================================================

class OrderListResponse(BaseSchema):
    """Customer order listing response."""

    items: list[OrderResponse] = Field(
        default_factory=list,
    )

    total: int = Field(
        default=0,
        ge=0,
    )


# =========================================================
# ORDER CANCELLATION
# =========================================================

class OrderCancellationRequest(BaseSchema):
    """Customer request to cancel an order."""

    reason: str = Field(
        min_length=5,
        max_length=1000,
    )


class OrderCancellationResponse(BaseSchema):
    """Response after an order cancellation request."""

    success: bool

    message: str

    order_id: int = Field(gt=0)

    status: OrderStatus


__all__ = [
    "OrderStatus",
    "PaymentStatus",
    "PaymentMethod",
    "OrderCheckoutRequest",
    "OrderItemResponse",
    "OrderAddressResponse",
    "OrderTrackingResponse",
    "OrderResponse",
    "OrderListResponse",
    "OrderCancellationRequest",
    "OrderCancellationResponse",
]
