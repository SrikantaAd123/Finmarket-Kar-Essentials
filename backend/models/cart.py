
"""
Shopping cart models for Finmarket Kart Essentials.

Contains:
- Cart
- CartItem

Supports:
- Customer shopping carts.
- Guest shopping carts.
- Multiple products in a cart.
- Product quantity and price tracking.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.database.commerce_base import CommerceBase

from backend.models.mixins import (
    PrimaryKeyMixin,
    TimestampMixin,
)


if TYPE_CHECKING:
    from backend.models.customer import Customer
    from backend.models.catalog import Product


# =========================================================
# CART MODEL
# =========================================================

class Cart(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Shopping cart belonging to a customer or guest."""

    __tablename__ = "carts"

    __table_args__ = (
        # -------------------------------------------------
        # INDEXES
        # -------------------------------------------------

        Index(
            "ix_carts_customer_id",
            "customer_id",
        ),

        Index(
            "ix_carts_guest_token_hash",
            "guest_token_hash",
        ),

        # -------------------------------------------------
        # CHECK CONSTRAINTS
        # -------------------------------------------------

        CheckConstraint(
            "customer_id IS NOT NULL "
            "OR guest_token_hash IS NOT NULL",
            name="customer_or_guest",
        ),

        CheckConstraint(
            "status IN ('active', 'converted', 'abandoned')",
            name="status",
        ),
    )

    # -----------------------------------------------------
    # CUSTOMER FOREIGN KEY
    # -----------------------------------------------------

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="CASCADE",
        ),
        nullable=True,
    )

    # -----------------------------------------------------
    # GUEST CART IDENTIFICATION
    # -----------------------------------------------------

    guest_token_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # -----------------------------------------------------
    # CART STATUS
    # -----------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        server_default="active",
    )

    # -----------------------------------------------------
    # CURRENCY
    # -----------------------------------------------------

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR",
    )

    # -----------------------------------------------------
    # CUSTOMER RELATIONSHIP
    # -----------------------------------------------------

    customer: Mapped[Customer | None] = relationship(
        "Customer",
        back_populates="carts",
    )

    # -----------------------------------------------------
    # CART ITEMS RELATIONSHIP
    # -----------------------------------------------------

    items: Mapped[list[CartItem]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        order_by="CartItem.created_at",
    )

    # -----------------------------------------------------
    # OBJECT REPRESENTATION
    # -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<Cart("
            f"id={self.id}, "
            f"status={self.status!r}, "
            f"customer_id={self.customer_id}"
            f")>"
        )


# =========================================================
# CART ITEM MODEL
# =========================================================

class CartItem(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Individual product inside a shopping cart."""

    __tablename__ = "cart_items"

    __table_args__ = (
        # -------------------------------------------------
        # UNIQUE CONSTRAINT
        # -------------------------------------------------

        UniqueConstraint(
            "cart_id",
            "product_id",
            name="uq_cart_items_cart_product",
        ),

        # -------------------------------------------------
        # CHECK CONSTRAINTS
        # -------------------------------------------------

        CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        ),

        CheckConstraint(
            "unit_price >= 0",
            name="unit_price_nonnegative",
        ),

        # -------------------------------------------------
        # INDEXES
        # -------------------------------------------------

        Index(
            "ix_cart_items_product_id",
            "product_id",
        ),
    )

    # -----------------------------------------------------
    # CART FOREIGN KEY
    # -----------------------------------------------------

    cart_id: Mapped[int] = mapped_column(
        ForeignKey(
            "carts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # -----------------------------------------------------
    # PRODUCT FOREIGN KEY
    # -----------------------------------------------------

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    # -----------------------------------------------------
    # PRODUCT QUANTITY
    # -----------------------------------------------------

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # -----------------------------------------------------
    # PRODUCT PRICE SNAPSHOT
    # -----------------------------------------------------

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # -----------------------------------------------------
    # CART RELATIONSHIP
    # -----------------------------------------------------

    cart: Mapped[Cart] = relationship(
        "Cart",
        back_populates="items",
    )

    # -----------------------------------------------------
    # PRODUCT RELATIONSHIP
    # -----------------------------------------------------

    product: Mapped[Product] = relationship(
        "Product",
    )

    # -----------------------------------------------------
    # COMPUTED LINE TOTAL
    # -----------------------------------------------------

    @property
    def line_total(self) -> Decimal:
        """Calculate the total price for this cart item."""

        return self.unit_price * self.quantity

    # -----------------------------------------------------
    # OBJECT REPRESENTATION
    # -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<CartItem("
            f"id={self.id}, "
            f"product_id={self.product_id}, "
            f"quantity={self.quantity}, "
            f"unit_price={self.unit_price}"
            f")>"
        )


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "Cart",
    "CartItem",
]
