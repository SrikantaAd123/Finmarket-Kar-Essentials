
"""Notification repository for Finmarket Kart Essentials.

Manages customer notifications, delivery status, retries
and customer notification preferences.

Uses flush() rather than commit(). Transaction management
belongs to the service layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session


from backend.models.notification import (
    Notification,
    NotificationPreference,
)


class NotificationRepository:
    """Database operations for customer notifications."""

    CHANNELS = {
        "email",
        "in_app",
    }

    NOTIFICATION_STATUSES = {
        "pending",
        "processing",
        "sent",
        "delivered",
        "failed",
        "cancelled",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    # =====================================================
    # VALIDATION HELPERS
    # =====================================================

    @staticmethod
    def _validate_pagination(
        page: int,
        page_size: int,
    ) -> None:
        if isinstance(page, bool) or page < 1:
            raise ValueError("Page must be at least 1.")

        if isinstance(page_size, bool) or page_size < 1:
            raise ValueError("Page size must be at least 1.")

        if page_size > 100:
            raise ValueError(
                "Page size cannot exceed 100."
            )

    def _validate_channel(
        self,
        channel: str,
    ) -> None:
        if channel not in self.CHANNELS:
            raise ValueError(
                f"Invalid notification channel: {channel}"
            )

    def _validate_status(
        self,
        status: str,
    ) -> None:
        if status not in self.NOTIFICATION_STATUSES:
            raise ValueError(
                f"Invalid notification status: {status}"
            )

    # =====================================================
    # CREATE NOTIFICATION
    # =====================================================

    def create_notification(
        self,
        data: dict[str, Any],
    ) -> Notification:
        """Create a customer notification."""

        notification_data = data.copy()

        channel = notification_data.get("channel")

        if not channel:
            raise ValueError(
                "Notification channel is required."
            )

        self._validate_channel(channel)

        status = notification_data.get(
            "status",
            "pending",
        )

        self._validate_status(status)

        if notification_data.get("retry_count", 0) < 0:
            raise ValueError(
                "Retry count cannot be negative."
            )

        if notification_data.get("max_retries", 3) < 0:
            raise ValueError(
                "Maximum retries cannot be negative."
            )

        notification = Notification(
            **notification_data
        )

        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)

        return notification

    def create_notification_if_new(
        self,
        data: dict[str, Any],
    ) -> tuple[Notification, bool]:
        """Create a notification if its idempotency key is unused.

        Returns:
            (notification, created)

        A None idempotency key allows normal non-idempotent
        notification creation.
        """

        notification_data = data.copy()

        idempotency_key = notification_data.get(
            "idempotency_key"
        )

        if idempotency_key:
            existing = self.get_by_idempotency_key(
                idempotency_key
            )

            if existing is not None:
                return existing, False

        notification = self.create_notification(
            notification_data
        )

        return notification, True

    # =====================================================
    # NOTIFICATION RETRIEVAL
    # =====================================================

    def get_notification_by_id(
        self,
        notification_id: int,
    ) -> Notification | None:
        """Retrieve a notification by primary key."""

        return self.db.get(
            Notification,
            notification_id,
        )

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Notification | None:
        """Retrieve a notification using its idempotency key."""

        statement = select(Notification).where(
            Notification.idempotency_key == idempotency_key
        )

        return self.db.scalars(statement).first()

    def get_customer_notification(
        self,
        notification_id: int,
        customer_id: int,
    ) -> Notification | None:
        """Retrieve a notification belonging to a customer."""

        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.customer_id == customer_id,
        )

        return self.db.scalars(statement).first()

    def get_customer_notifications(
        self,
        customer_id: int,
        page: int = 1,
        page_size: int = 20,
        channel: str | None = None,
        status: str | None = None,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        """Retrieve paginated notification history for a customer."""

        self._validate_pagination(page, page_size)

        filters = [
            Notification.customer_id == customer_id
        ]

        if channel is not None:
            self._validate_channel(channel)
            filters.append(
                Notification.channel == channel
            )

        if status is not None:
            self._validate_status(status)
            filters.append(
                Notification.status == status
            )

        if unread_only:
            filters.append(
                Notification.read_at.is_(None)
            )

        count_statement = (
            select(func.count(Notification.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            select(Notification)
            .where(*filters)
            .order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        notifications = list(
            self.db.scalars(statement).all()
        )

        return notifications, int(total)

    # =====================================================
    # UPDATE NOTIFICATION
    # =====================================================

    def update_notification(
        self,
        notification_id: int,
        data: dict[str, Any],
    ) -> Notification | None:
        """Update notification information."""

        notification = self.get_notification_by_id(
            notification_id
        )

        if notification is None:
            return None

        update_data = data.copy()

        protected = {
            "id",
            "created_at",
            "customer_id",
        }

        for field in protected:
            update_data.pop(field, None)

        valid_fields = {
            attribute.key
            for attribute in Notification.__mapper__.column_attrs
        }

        invalid = set(update_data) - valid_fields

        if invalid:
            raise ValueError(
                "Invalid notification fields: "
                + ", ".join(sorted(invalid))
            )

        if "channel" in update_data:
            self._validate_channel(
                update_data["channel"]
            )

        if "status" in update_data:
            self._validate_status(
                update_data["status"]
            )

        for field, value in update_data.items():
            setattr(notification, field, value)

        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)

        return notification

    # =====================================================
    # NOTIFICATION DELIVERY STATUS
    # =====================================================

    def mark_notification_processing(
        self,
        notification_id: int,
    ) -> Notification | None:
        """Mark a notification as being processed."""

        notification = self.get_notification_by_id(
            notification_id
        )

        if notification is None:
            return None

        if notification.status not in {
            "pending",
            "failed",
        }:
            raise ValueError(
                "Only pending or failed notifications "
                "can enter processing."
            )

        notification.status = "processing"
        notification.last_error = None

        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)

        return notification

    def mark_notification_sent(
        self,
        notification_id: int,
        provider: str | None = None,
        provider_message_id: str | None = None,
    ) -> Notification | None:
        """Mark a notification as successfully sent."""

        notification = self.get_notification_by_id(
            notification_id
        )

        if notification is None:
            return None

        if notification.status != "processing":
            raise ValueError(
                "Only processing notifications can be marked sent."
            )

        notification.status = "sent"
        notification.sent_at = datetime.now(timezone.utc)
        notification.last_error = None

        if provider is not None:
            notification.provider = provider

        if provider_message_id is not None:
            notification.provider_message_id = (
                provider_message_id
            )

        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)

        return notification

    def mark_notification_delivered(
        self,
        notification_id: int,
    ) -> Notification | None:
        """Mark a sent notification as delivered."""

        notification = self.get_notification_by_id(
            notification_id
        )

        if notification is None:
            return None

        if notification.status not in {
            "sent",
            "delivered",
        }:
            raise ValueError(
                "Only sent notifications can be delivered."
            )

        notification.status = "delivered"

        if notification.delivered_at is None:
            notification.delivered_at = (
                datetime.now(timezone.utc)
            )

        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)

        return notification

    def mark_notification_failed(
        self,
        notification_id: int,
        error_message: str,
        increment_retry: bool = True,
    ) -> Notification | None:
        """Mark a notification as failed and optionally increment retries."""

        notification = self.get_notification_by_id(
            notification_id
        )

        if notification is None:
            return None

        if notification.status in {
            "delivered",
            "cancelled",
        }:
            raise ValueError(
                "Delivered or cancelled notifications "
                "cannot be marked failed."
            )

        notification.status = "failed"
        notification.last_error = error_message

        if increment_retry:
            notification.retry_count += 1

        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)

        return notification

    def cancel_notification(
        self,
        notification_id: int,
    ) -> Notification | None:
        """Cancel a notification that has not been sent."""

        notification = self.get_notification_by_id(
            notification_id
        )

        if notification is None:
            return None

        if notification.status in {
            "sent",
            "delivered",
        }:
            raise ValueError(
                "Sent or delivered notifications cannot be cancelled."
            )

        notification.status = "cancelled"

        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)

        return notification

    # =====================================================
    # CUSTOMER READ STATUS
    # =====================================================

    def mark_notification_read(
        self,
        notification_id: int,
        customer_id: int,
    ) -> Notification | None:
        """Mark a customer's notification as read."""

        notification = self.get_customer_notification(
            notification_id,
            customer_id,
        )

        if notification is None:
            return None

        if notification.read_at is None:
            notification.read_at = datetime.now(timezone.utc)

            self.db.add(notification)
            self.db.flush()
            self.db.refresh(notification)

        return notification

    def mark_all_notifications_read(
        self,
        customer_id: int,
    ) -> int:
        """Mark all unread customer notifications as read."""

        statement = select(Notification).where(
            Notification.customer_id == customer_id,
            Notification.read_at.is_(None),
            Notification.channel == "in_app",
        )

        notifications = list(
            self.db.scalars(statement).all()
        )

        now = datetime.now(timezone.utc)

        for notification in notifications:
            notification.read_at = now

        if notifications:
            self.db.flush()

        return len(notifications)

    def count_unread_notifications(
        self,
        customer_id: int,
    ) -> int:
        """Count unread in-app notifications for a customer."""

        statement = select(
            func.count(Notification.id)
        ).where(
            Notification.customer_id == customer_id,
            Notification.channel == "in_app",
            Notification.read_at.is_(None),
        )

        return int(self.db.scalar(statement) or 0)

    # =====================================================
    # PENDING AND FAILED NOTIFICATIONS
    # =====================================================

    def get_pending_notifications(
        self,
        limit: int = 50,
    ) -> list[Notification]:
        """Retrieve notifications ready for processing."""

        if limit < 1 or limit > 500:
            raise ValueError(
                "Limit must be between 1 and 500."
            )

        now = datetime.now(timezone.utc)

        statement = (
            select(Notification)
            .where(
                Notification.status == "pending",
                (
                    Notification.scheduled_at.is_(None)
                    | (Notification.scheduled_at <= now)
                ),
            )
            .order_by(
                Notification.created_at.asc(),
                Notification.id.asc(),
            )
            .limit(limit)
        )

        return list(self.db.scalars(statement).all())

    def get_retryable_notifications(
        self,
        limit: int = 50,
    ) -> list[Notification]:
        """Retrieve failed notifications that can be retried."""

        if limit < 1 or limit > 500:
            raise ValueError(
                "Limit must be between 1 and 500."
            )

        now = datetime.now(timezone.utc)

        statement = (
            select(Notification)
            .where(
                Notification.status == "failed",
                Notification.retry_count < Notification.max_retries,
                (
                    Notification.scheduled_at.is_(None)
                    | (Notification.scheduled_at <= now)
                ),
            )
            .order_by(
                Notification.created_at.asc(),
                Notification.id.asc(),
            )
            .limit(limit)
        )

        return list(self.db.scalars(statement).all())

    # =====================================================
    # NOTIFICATION STATISTICS
    # =====================================================

    def count_notifications_by_status(
        self,
        status: str,
        channel: str | None = None,
    ) -> int:
        """Count notifications by status and optional channel."""

        self._validate_status(status)

        statement = select(
            func.count(Notification.id)
        ).where(
            Notification.status == status
        )

        if channel is not None:
            self._validate_channel(channel)
            statement = statement.where(
                Notification.channel == channel
            )

        return int(self.db.scalar(statement) or 0)

    def get_notification_summary(
        self,
        customer_id: int | None = None,
    ) -> dict[str, int]:
        """Retrieve notification counts grouped by status."""

        statement = (
            select(
                Notification.status,
                func.count(Notification.id),
            )
            .group_by(Notification.status)
        )

        if customer_id is not None:
            statement = statement.where(
                Notification.customer_id == customer_id
            )

        rows = self.db.execute(statement).all()

        summary = {
            status: 0
            for status in self.NOTIFICATION_STATUSES
        }

        for status, count in rows:
            summary[status] = int(count)

        return summary

    # =====================================================
    # CUSTOMER NOTIFICATION PREFERENCES
    # =====================================================

    def get_customer_preferences(
        self,
        customer_id: int,
    ) -> NotificationPreference | None:
        """Retrieve a customer's notification preferences."""

        statement = select(NotificationPreference).where(
            NotificationPreference.customer_id == customer_id
        )

        return self.db.scalars(statement).first()

    def create_customer_preferences(
        self,
        customer_id: int,
        data: dict[str, Any] | None = None,
    ) -> NotificationPreference:
        """Create notification preferences for a customer."""

        existing = self.get_customer_preferences(
            customer_id
        )

        if existing is not None:
            raise ValueError(
                "Notification preferences already exist."
            )

        preference_data = (data or {}).copy()

        preference_data.pop("id", None)
        preference_data.pop("customer_id", None)
        preference_data.pop("created_at", None)
        preference_data.pop("updated_at", None)

        valid_fields = {
            attribute.key
            for attribute in NotificationPreference.__mapper__.column_attrs
        }

        invalid = set(preference_data) - valid_fields

        if invalid:
            raise ValueError(
                "Invalid preference fields: "
                + ", ".join(sorted(invalid))
            )

        preferences = NotificationPreference(
            customer_id=customer_id,
            **preference_data,
        )

        self.db.add(preferences)
        self.db.flush()
        self.db.refresh(preferences)

        return preferences

    def get_or_create_customer_preferences(
        self,
        customer_id: int,
    ) -> NotificationPreference:
        """Retrieve preferences or create default preferences."""

        existing = self.get_customer_preferences(
            customer_id
        )

        if existing is not None:
            return existing

        return self.create_customer_preferences(
            customer_id
        )

    def update_customer_preferences(
        self,
        customer_id: int,
        data: dict[str, Any],
    ) -> NotificationPreference:
        """Update customer notification preferences."""

        preferences = self.get_or_create_customer_preferences(
            customer_id
        )

        update_data = data.copy()

        protected = {
            "id",
            "customer_id",
            "created_at",
            "updated_at",
        }

        for field in protected:
            update_data.pop(field, None)

        valid_fields = {
            attribute.key
            for attribute in NotificationPreference.__mapper__.column_attrs
        }

        invalid = set(update_data) - valid_fields

        if invalid:
            raise ValueError(
                "Invalid preference fields: "
                + ", ".join(sorted(invalid))
            )

        boolean_fields = {
            "email_enabled",
            "in_app_enabled",
            "order_updates_enabled",
            "payment_updates_enabled",
            "delivery_updates_enabled",
            "marketing_enabled",
        }

        for field, value in update_data.items():
            if field in boolean_fields and not isinstance(value, bool):
                raise ValueError(
                    f"{field} must be a boolean value."
                )

            setattr(preferences, field, value)

        self.db.add(preferences)
        self.db.flush()
        self.db.refresh(preferences)

        return preferences
