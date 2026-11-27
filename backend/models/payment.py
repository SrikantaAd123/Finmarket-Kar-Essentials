
"""
Payment management models for Finmarket Kart Essentials.

Contains:
- PaymentTransaction
- PaymentRefund

Supports:
- Razorpay payments.
- Cash on delivery.
- Payment attempts and status tracking.
- Full and partial refunds.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
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
    from backend.models.order import Order


# =========================================================
# PAYMENT TRANSACTION MODEL
# =========================================================

class PaymentTransaction(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Stores payment attempts and provider information."""

    __tablename__ = "payment_transactions"

    __table_args__ = (
        # -------------------------------------------------
        # CHECK CONSTRAINTS
        # -------------------------------------------------

        CheckConstraint(
            "amount > 0",
            name="amount_positive",
        ),

        CheckConstraint(
            "status IN ("
            "'created', 'pending', 'authorized', "
            "'captured', 'failed', 'cancelled', "
            "'refunded', 'partially_refunded'"
            ")",
            name="status",
        ),

        CheckConstraint(
            "payment_method IN ('razorpay', 'cod')",
            name="method",
        ),

        # -------------------------------------------------
        # INDEXES
        # -------------------------------------------------

        Index(
            "ix_payment_transactions_order_id",
            "order_id",
        ),

        Index(
            "ix_payment_transactions_status",
            "status",
        ),

        Index(
            "ix_payment_transactions_provider_order_id",
            "provider_order_id",
        ),
    )

    # -----------------------------------------------------
    # ORDER FOREIGN KEY
    # -----------------------------------------------------

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    # -----------------------------------------------------
    # PAYMENT METHOD
    # -----------------------------------------------------

    payment_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # -----------------------------------------------------
    # PAYMENT PROVIDER
    # -----------------------------------------------------

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="razorpay",
        server_default="razorpay",
    )

    provider_order_id: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    provider_payment_id: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # -----------------------------------------------------
    # IDEMPOTENCY
    # -----------------------------------------------------

    idempotency_key: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        unique=True,
    )

    # -----------------------------------------------------
    # PAYMENT AMOUNT
    # -----------------------------------------------------

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR",
    )

    # -----------------------------------------------------
    # PAYMENT STATUS
    # -----------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="created",
        server_default="created",
    )

    # -----------------------------------------------------
    # PAYMENT FAILURE INFORMATION
    # -----------------------------------------------------

    failure_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -----------------------------------------------------
    # PAYMENT TIMESTAMPS
    # -----------------------------------------------------

    authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -----------------------------------------------------
    # ORDER RELATIONSHIP
    # -----------------------------------------------------

    order: Mapped[Order] = relationship(
        "Order",
        back_populates="payments",
    )

    # -----------------------------------------------------
    # REFUND RELATIONSHIP
    # -----------------------------------------------------

    refunds: Mapped[list[PaymentRefund]] = relationship(
        "PaymentRefund",
        back_populates="payment",
        cascade="all, delete-orphan",
    )

    # -----------------------------------------------------
    # OBJECT REPRESENTATION
    # -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<PaymentTransaction("
            f"id={self.id}, "
            f"order_id={self.order_id}, "
            f"status={self.status!r}"
            f")>"
        )


# =========================================================
# PAYMENT REFUND MODEL
# =========================================================

class PaymentRefund(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Stores full and partial payment refund records."""

    __tablename__ = "payment_refunds"

    __table_args__ = (
        # -------------------------------------------------
        # CHECK CONSTRAINTS
        # -------------------------------------------------

        CheckConstraint(
            "amount > 0",
            name="amount_positive",
        ),

        CheckConstraint(
            "status IN ('pending', 'processed', 'failed')",
            name="status",
        ),

        # -------------------------------------------------
        # UNIQUE CONSTRAINT
        # -------------------------------------------------

        UniqueConstraint(
            "provider_refund_id",
            name="uq_payment_refunds_provider_refund_id",
        ),

        # -------------------------------------------------
        # INDEXES
        # -------------------------------------------------

        Index(
            "ix_payment_refunds_payment_id",
            "payment_id",
        ),
    )

    # -----------------------------------------------------
    # PAYMENT FOREIGN KEY
    # -----------------------------------------------------

    payment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "payment_transactions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    # -----------------------------------------------------
    # PROVIDER REFUND IDENTIFICATION
    # -----------------------------------------------------

    provider_refund_id: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # -----------------------------------------------------
    # REFUND AMOUNT
    # -----------------------------------------------------

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR",
    )

    # -----------------------------------------------------
    # REFUND REASON
    # -----------------------------------------------------

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -----------------------------------------------------
    # REFUND STATUS
    # -----------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    # -----------------------------------------------------
    # REFUND PROCESSING TIMESTAMP
    # -----------------------------------------------------

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -----------------------------------------------------
    # PAYMENT RELATIONSHIP
    # -----------------------------------------------------

    payment: Mapped[PaymentTransaction] = relationship(
        "PaymentTransaction",
        back_populates="refunds",
    )

    # -----------------------------------------------------
    # OBJECT REPRESENTATION
    # -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<PaymentRefund("
            f"id={self.id}, "
            f"payment_id={self.payment_id}, "
            f"status={self.status!r}"
            f")>"
        )


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "PaymentTransaction",
    "PaymentRefund",
]
