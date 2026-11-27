
"""Shopping cart schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from backend.schemas.common import BaseSchema


# =========================================================
# CART REQUEST SCHEMAS
# =========================================================

class AddToCartRequest(BaseSchema):
    """Request schema for adding a product to the cart."""

    product_id: int = Field(gt=0)

    quantity: int = Field(
        default=1,
        ge=1,
        le=100,
    )


class UpdateCartItemRequest(BaseSchema):
    """Request schema for updating cart item quantity."""

    quantity: int = Field(
        ge=1,
        le=100,
    )


class RemoveCartItemRequest(BaseSchema):
    """Request schema for removing an item from the cart."""

    cart_item_id: int = Field(gt=0)


# =========================================================
# CART PRODUCT SCHEMAS
# =========================================================

class CartProductSummary(BaseSchema):
    """Basic product information displayed in the cart."""

    id: int = Field(gt=0)

    name: str

    sku: str

    slug: str

    price: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    currency: str = "INR"

    unit: str

    image_url: str | None = None

    is_active: bool


# =========================================================
# CART ITEM SCHEMAS
# =========================================================

class CartItemResponse(BaseSchema):
    """Individual cart item response."""

    id: int = Field(gt=0)

    cart_id: int = Field(gt=0)

    product_id: int = Field(gt=0)

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

    product: CartProductSummary


# =========================================================
# CART RESPONSE SCHEMAS
# =========================================================

class CartResponse(BaseSchema):
    """Complete shopping cart response."""

    id: int = Field(gt=0)

    customer_id: int | None = Field(
        default=None,
        gt=0,
    )

    status: Literal[
        "active",
        "converted",
        "abandoned",
    ]

    currency: str = "INR"

    items: list[CartItemResponse] = Field(
        default_factory=list,
    )

    item_count: int = Field(
        default=0,
        ge=0,
    )

    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )


class CartSummaryResponse(BaseSchema):
    """Compact cart summary for website navigation."""

    cart_id: int = Field(gt=0)

    item_count: int = Field(ge=0)

    subtotal: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    currency: str = "INR"


# =========================================================
# CART OPERATION RESPONSE
# =========================================================

class CartOperationResponse(BaseSchema):
    """Response after a cart operation."""

    success: bool = True

    message: str

    cart: CartResponse | None = None


__all__ = [
    "AddToCartRequest",
    "UpdateCartItemRequest",
    "RemoveCartItemRequest",
    "CartProductSummary",
    "CartItemResponse",
    "CartResponse",
    "CartSummaryResponse",
    "CartOperationResponse",
]
