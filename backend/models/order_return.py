
"""Order return models for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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
    from backend.models.order import Order


class OrderReturn(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """A customer's return request for an existing order."""

    __tablename__ = "order_returns"

    __table_args__ = (
        UniqueConstraint(
            "return_number",
            name="uq_order_returns_return_number",
        ),
        CheckConstraint(
            "status IN ('requested', 'approved', 'rejected', "
            "'picked_up', 'received', 'refunded', 'cancelled')",
            name="status_valid",
        ),
        CheckConstraint(
            "refund_status IN ('not_required', 'pending', "
            "'processing', 'completed', 'failed')",
            name="refund_status_valid",
        ),
        CheckConstraint(
            "requested_refund_amount >= 0",
            name="refund_amount_nonnegative",
        ),
        Index("ix_order_returns_order_id", "order_id"),
        Index("ix_order_returns_customer_id", "customer_id"),
        Index("ix_order_returns_status", "status"),
        Index("ix_order_returns_created_at", "created_at"),
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    return_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="requested",
        server_default="requested",
    )

    requested_refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    refund_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="not_required",
        server_default="not_required",
    )

    refund_reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    admin_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="returns",
    )

    items: Mapped[list["OrderReturnItem"]] = relationship(
        "OrderReturnItem",
        back_populates="return_request",
        cascade="all, delete-orphan",
        order_by="OrderReturnItem.id",
    )

    def __repr__(self) -> str:
        return (
            f"<OrderReturn("
            f"id={self.id}, "
            f"return_number={self.return_number!r}, "
            f"status={self.status!r}"
            f")>"
        )


class OrderReturnItem(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """An individual order item included in a return request."""

    __tablename__ = "order_return_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="unit_price_nonnegative",
        ),
        CheckConstraint(
            "refund_amount >= 0",
            name="refund_amount_nonnegative",
        ),
        Index("ix_order_return_items_return_id", "return_id"),
        Index(
            "ix_order_return_items_order_item_id",
            "order_item_id",
        ),
    )

    return_id: Mapped[int] = mapped_column(
        ForeignKey("order_returns.id", ondelete="CASCADE"),
        nullable=False,
    )

    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False,
    )

    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    product_sku: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    return_request: Mapped["OrderReturn"] = relationship(
        "OrderReturn",
        back_populates="items",
    )

    def __repr__(self) -> str:
        return (
            f"<OrderReturnItem("
            f"id={self.id}, "
            f"order_item_id={self.order_item_id}, "
            f"quantity={self.quantity}"
            f")>"
        )


__all__ = [
    "OrderReturn",
    "OrderReturnItem",
]
