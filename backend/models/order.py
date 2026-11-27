
"""Order management models for Finmarket Kart Essentials."""

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
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.commerce_base import CommerceBase
from backend.models.mixins import (
    PrimaryKeyMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    from backend.models.customer import Customer
    from backend.models.catalog import Product
    from backend.models.order_tracking import OrderTracking
    from backend.models.payment import PaymentTransaction
    from backend.models.delivery import Shipment
    from backend.models.order_return import OrderReturn


class Order(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Represents a customer's complete purchase order."""

    __tablename__ = "orders"

    __table_args__ = (
        UniqueConstraint(
            "order_number",
            name="uq_orders_order_number",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="subtotal_nonnegative",
        ),
        CheckConstraint(
            "tax_amount >= 0",
            name="tax_nonnegative",
        ),
        CheckConstraint(
            "delivery_fee >= 0",
            name="delivery_fee_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="discount_nonnegative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="total_nonnegative",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'processing', "
            "'packed', 'shipped', 'out_for_delivery', "
            "'delivered', 'cancelled', 'returned')",
            name="status_valid",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'paid', 'failed', "
            "'refunded', 'partially_refunded')",
            name="payment_status_valid",
        ),
        Index(
            "ix_orders_customer_id",
            "customer_id",
        ),
        Index(
            "ix_orders_status",
            "status",
        ),
        Index(
            "ix_orders_payment_status",
            "payment_status",
        ),
        Index(
            "ix_orders_created_at",
            "created_at",
        ),
    )

    # =====================================================
    # ORDER IDENTIFICATION
    # =====================================================

    order_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    # =====================================================
    # ORDER STATUS
    # =====================================================

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    payment_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    payment_method: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="cod",
        server_default="cod",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR",
    )

    # =====================================================
    # ORDER AMOUNTS
    # =====================================================

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    delivery_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # =====================================================
    # CUSTOMER NOTES
    # =====================================================

    customer_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =====================================================
    # SHIPPING ADDRESS SNAPSHOT
    # =====================================================

    shipping_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    shipping_phone: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
    )

    shipping_address_line1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    shipping_address_line2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    shipping_city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    shipping_state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    shipping_postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    shipping_country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="India",
        server_default="India",
    )

    # =====================================================
    # BILLING ADDRESS SNAPSHOT
    # =====================================================

    billing_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    billing_phone: Mapped[str | None] = mapped_column(
        String(25),
        nullable=True,
    )

    billing_address_line1: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    billing_address_line2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    billing_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    billing_state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    billing_postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    billing_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="orders",
    )

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    shipment: Mapped["Shipment | None"] = relationship(
        "Shipment",
        back_populates="order",
        uselist=False,
    )

    payments: Mapped[list["PaymentTransaction"]] = relationship(
        "PaymentTransaction",
        back_populates="order",
    )

    tracking_events: Mapped[list["OrderTracking"]] = relationship(
        "OrderTracking",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderTracking.created_at",
    )

    returns: Mapped[list["OrderReturn"]] = relationship(
        "OrderReturn",
        back_populates="order",
        order_by="OrderReturn.created_at",
    )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<Order("
            f"id={self.id}, "
            f"number={self.order_number!r}, "
            f"status={self.status!r}"
            f")>"
        )


class OrderItem(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """A product purchased as part of an order."""

    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="price_nonnegative",
        ),
        CheckConstraint(
            "line_total >= 0",
            name="total_nonnegative",
        ),
        Index(
            "ix_order_items_order_id",
            "order_id",
        ),
        Index(
            "ix_order_items_product_id",
            "product_id",
        ),
    )

    # =====================================================
    # ORDER RELATION
    # =====================================================

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # =====================================================
    # PRODUCT RELATION
    # =====================================================

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    product_sku: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    # =====================================================
    # QUANTITY AND PRICE
    # =====================================================

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )

    product: Mapped["Product | None"] = relationship(
        "Product",
    )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"<OrderItem("
            f"id={self.id}, "
            f"product={self.product_name!r}, "
            f"quantity={self.quantity}"
            f")>"
        )


__all__ = [
    "Order",
    "OrderItem",
]
