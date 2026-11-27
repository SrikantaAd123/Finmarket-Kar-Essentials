
"""
Order tracking and status history models.

Contains:
- OrderTracking

Stores the chronological history of order status changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
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
    from backend.models.order import Order


# =========================================================
# ORDER TRACKING MODEL
# =========================================================

class OrderTracking(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Stores individual order tracking events."""

    __tablename__ = "order_tracking"

    __table_args__ = (
        Index(
            "ix_order_tracking_order_id",
            "order_id",
        ),
        Index(
            "ix_order_tracking_status",
            "status",
        ),
    )

    # -----------------------------------------------------
    # ORDER FOREIGN KEY
    # -----------------------------------------------------

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # -----------------------------------------------------
    # TRACKING STATUS
    # -----------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    # -----------------------------------------------------
    # EVENT INFORMATION
    # -----------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    updated_by: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # -----------------------------------------------------
    # ORDER RELATIONSHIP
    # -----------------------------------------------------

    order: Mapped[Order] = relationship(
        "Order",
        back_populates="tracking_events",
    )

    # -----------------------------------------------------
    # OBJECT REPRESENTATION
    # -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<OrderTracking("
            f"id={self.id}, "
            f"order_id={self.order_id}, "
            f"status={self.status!r}"
            f")>"
        )


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "OrderTracking",
]
