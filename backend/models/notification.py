
"""Customer notification models for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.commerce_base import CommerceBase
from backend.models.mixins import PrimaryKeyMixin, TimestampMixin


class Notification(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Stores customer email and in-app notifications."""

    __tablename__ = "notifications"

    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'in_app')",
            name="channel",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', "
            "'delivered', 'failed', 'cancelled')",
            name="status",
        ),
        CheckConstraint(
            "retry_count >= 0",
            name="retry_count_nonnegative",
        ),
        Index(
            "ix_notifications_customer_id",
            "customer_id",
        ),
        Index(
            "ix_notifications_status",
            "status",
        ),
        Index(
            "ix_notifications_scheduled_at",
            "scheduled_at",
        ),
        Index(
            "ix_notifications_created_at",
            "created_at",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_notifications_idempotency_key",
        ),
    )

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    template_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    template_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    provider: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    provider_message_id: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )

    max_retries: Mapped[int] = mapped_column(
        nullable=False,
        default=3,
        server_default="3",
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Notification("
            f"id={self.id}, "
            f"channel={self.channel!r}, "
            f"status={self.status!r}"
            f")>"
        )


class NotificationPreference(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Stores customer email, in-app and marketing preferences."""

    __tablename__ = "notification_preferences"

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            name="uq_notification_preferences_customer",
        ),
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )

    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    in_app_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    order_updates_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    payment_updates_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    delivery_updates_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    marketing_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationPreference("
            f"id={self.id}, "
            f"customer_id={self.customer_id}"
            f")>"
        )


__all__ = [
    "Notification",
    "NotificationPreference",
]
