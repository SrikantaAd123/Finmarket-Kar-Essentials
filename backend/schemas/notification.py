
"""Notification schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from backend.schemas.common import BaseSchema


# =========================================================
# NOTIFICATION TYPES
# =========================================================

NotificationChannel = Literal[
    "email",
    "in_app",
]

NotificationStatus = Literal[
    "pending",
    "processing",
    "sent",
    "delivered",
    "failed",
    "cancelled",
]

NotificationType = Literal[
    "order_confirmation",
    "order_status",
    "payment_success",
    "payment_failed",
    "refund_update",
    "shipment_update",
    "delivery_update",
    "account_update",
    "promotional",
    "general",
]


# =========================================================
# NOTIFICATION CREATION
# =========================================================

class NotificationCreate(BaseSchema):
    """Request to create a customer notification."""

    customer_id: int | None = Field(
        default=None,
        gt=0,
    )

    channel: NotificationChannel

    notification_type: NotificationType

    recipient: str = Field(
        min_length=3,
        max_length=255,
    )

    subject: str | None = Field(
        default=None,
        max_length=255,
    )

    message: str = Field(
        min_length=1,
        max_length=10000,
    )

    template_name: str | None = Field(
        default=None,
        max_length=150,
    )

    template_data: dict[str, Any] | None = None

    scheduled_at: datetime | None = None

    idempotency_key: str | None = Field(
        default=None,
        max_length=180,
    )


# =========================================================
# NOTIFICATION UPDATE
# =========================================================

class NotificationUpdate(BaseSchema):
    """Request to update notification processing information."""

    status: NotificationStatus | None = None

    provider: str | None = Field(
        default=None,
        max_length=80,
    )

    provider_message_id: str | None = Field(
        default=None,
        max_length=180,
    )

    last_error: str | None = Field(
        default=None,
        max_length=5000,
    )


# =========================================================
# NOTIFICATION RESPONSE
# =========================================================

class NotificationResponse(BaseSchema):
    """Notification information returned by the API."""

    id: int = Field(gt=0)

    customer_id: int | None = Field(
        default=None,
        gt=0,
    )

    channel: NotificationChannel

    notification_type: NotificationType

    recipient: str

    subject: str | None = None

    message: str

    template_name: str | None = None

    status: NotificationStatus

    provider: str | None = None

    provider_message_id: str | None = None

    retry_count: int = Field(ge=0)

    max_retries: int = Field(ge=0)

    scheduled_at: datetime | None = None

    sent_at: datetime | None = None

    delivered_at: datetime | None = None

    read_at: datetime | None = None

    last_error: str | None = None

    created_at: datetime | None = None

    updated_at: datetime | None = None


# =========================================================
# NOTIFICATION LIST
# =========================================================

class NotificationListResponse(BaseSchema):
    """List of notifications returned to a customer or admin."""

    items: list[NotificationResponse] = Field(
        default_factory=list,
    )

    total: int = Field(
        default=0,
        ge=0,
    )


# =========================================================
# NOTIFICATION PREFERENCES
# =========================================================

class NotificationPreferenceUpdate(BaseSchema):
    """Request to update customer notification preferences."""

    email_enabled: bool | None = None

    in_app_enabled: bool | None = None

    order_updates_enabled: bool | None = None

    payment_updates_enabled: bool | None = None

    delivery_updates_enabled: bool | None = None

    marketing_enabled: bool | None = None


class NotificationPreferenceResponse(BaseSchema):
    """Customer notification preferences returned by the API."""

    id: int = Field(gt=0)

    customer_id: int = Field(gt=0)

    email_enabled: bool

    in_app_enabled: bool

    order_updates_enabled: bool

    payment_updates_enabled: bool

    delivery_updates_enabled: bool

    marketing_enabled: bool

    created_at: datetime | None = None

    updated_at: datetime | None = None


# =========================================================
# NOTIFICATION OPERATION RESPONSE
# =========================================================

class NotificationOperationResponse(BaseSchema):
    """Response after a notification operation."""

    success: bool = True

    message: str

    notification_id: int | None = Field(
        default=None,
        gt=0,
    )


# =========================================================
# NOTIFICATION RETRY
# =========================================================

class NotificationRetryRequest(BaseSchema):
    """Request to retry a failed notification."""

    notification_id: int = Field(gt=0)


class NotificationRetryResponse(BaseSchema):
    """Result of a notification retry operation."""

    success: bool

    message: str

    notification_id: int = Field(gt=0)

    retry_count: int = Field(ge=0)

    status: NotificationStatus


__all__ = [
    "NotificationChannel",
    "NotificationStatus",
    "NotificationType",
    "NotificationCreate",
    "NotificationUpdate",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationPreferenceUpdate",
    "NotificationPreferenceResponse",
    "NotificationOperationResponse",
    "NotificationRetryRequest",
    "NotificationRetryResponse",
]
