
"""
Payment webhook event model for Finmarket Kart Essentials.

Contains:
- PaymentWebhookEvent

Supports:
- Razorpay webhook event storage.
- Duplicate-event prevention.
- Webhook processing status.
- Processing error tracking.
- Original provider payload storage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.database.commerce_base import CommerceBase

from backend.models.mixins import (
    PrimaryKeyMixin,
    TimestampMixin,
)


# =========================================================
# PAYMENT WEBHOOK EVENT MODEL
# =========================================================

class PaymentWebhookEvent(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """
    Stores payment provider webhook events.

    Supports duplicate-event prevention, processing status,
    error tracking, and webhook auditing.
    """

    __tablename__ = "payment_webhook_events"

    __table_args__ = (
        # -------------------------------------------------
        # DUPLICATE EVENT PREVENTION
        # -------------------------------------------------

        UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_payment_webhook_provider_event",
        ),

        # -------------------------------------------------
        # INDEXES
        # -------------------------------------------------

        Index(
            "ix_payment_webhook_events_processed",
            "is_processed",
        ),

        Index(
            "ix_payment_webhook_events_event_type",
            "event_type",
        ),
    )

    # -----------------------------------------------------
    # PAYMENT PROVIDER
    # -----------------------------------------------------

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # -----------------------------------------------------
    # PROVIDER EVENT IDENTIFICATION
    # -----------------------------------------------------

    provider_event_id: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    # -----------------------------------------------------
    # ORIGINAL WEBHOOK PAYLOAD
    # -----------------------------------------------------

    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    # -----------------------------------------------------
    # PROCESSING STATUS
    # -----------------------------------------------------

    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    # -----------------------------------------------------
    # PROCESSING ERROR
    # -----------------------------------------------------

    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -----------------------------------------------------
    # PROCESSING TIMESTAMP
    # -----------------------------------------------------

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -----------------------------------------------------
    # OBJECT REPRESENTATION
    # -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<PaymentWebhookEvent("
            f"id={self.id}, "
            f"provider={self.provider!r}, "
            f"event={self.event_type!r}, "
            f"processed={self.is_processed}"
            f")>"
        )


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "PaymentWebhookEvent",
]
