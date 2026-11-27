
"""
Notification service for Finmarket Kart Essentials.

Responsibilities:
- Create and retrieve notifications.
- Enforce customer notification preferences.
- Process email and in-app notifications.
- Track notification delivery status.
- Handle retries for failed notifications.
- Manage customer notification preferences.

The repository uses flush(), so this service owns
database commit and rollback operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.repositories.notification_repository import (
    NotificationRepository,
)

from backend.models.notification import (
    Notification,
    NotificationPreference,
)


# =========================================================
# TYPES
# =========================================================

EmailSender = Callable[
    [str, str, str],
    Any,
]


# =========================================================
# NOTIFICATION SERVICE
# =========================================================

class NotificationService:
    """Business logic for customer notifications."""

    SUPPORTED_CHANNELS = {
        "email",
        "in_app",
    }

    NOTIFICATION_CATEGORIES = {
        "order": "order_updates_enabled",
        "order_update": "order_updates_enabled",
        "order_confirmation": "order_updates_enabled",
        "order_status": "order_updates_enabled",
        "payment": "payment_updates_enabled",
        "payment_update": "payment_updates_enabled",
        "payment_confirmation": "payment_updates_enabled",
        "delivery": "delivery_updates_enabled",
        "delivery_update": "delivery_updates_enabled",
        "shipping": "delivery_updates_enabled",
        "marketing": "marketing_enabled",
        "promotional": "marketing_enabled",
        "promotion": "marketing_enabled",
    }

    def __init__(
        self,
        db: Session,
        email_sender: EmailSender | None = None,
    ) -> None:
        """
        Initialize the notification service.

        Args:
            db: SQLAlchemy database session.
            email_sender: Optional email delivery function.

        The email sender must accept:
            recipient, subject, message

        Example:
            NotificationService(
                db,
                email_sender=send_email,
            )
        """

        self.db = db
        self.repository = NotificationRepository(db)
        self.email_sender = email_sender

    # =====================================================
    # COMMON HELPERS
    # =====================================================

    def _commit(self) -> None:
        """Commit the current database transaction."""
        self.db.commit()

    def _rollback(self) -> None:
        """Roll back the current database transaction."""
        self.db.rollback()

    @staticmethod
    def _to_dict(data: Any) -> dict[str, Any]:
        """
        Convert a Pydantic schema or dictionary into a dictionary.

        Supports Pydantic v2 and ordinary dictionaries.
        """

        if isinstance(data, dict):
            return data.copy()

        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)

        if hasattr(data, "dict"):
            return data.dict(exclude_unset=True)

        raise TypeError(
            "Expected a dictionary or Pydantic model."
        )

    @staticmethod
    def _validate_id(
        value: int,
        field_name: str = "ID",
    ) -> None:
        """Validate a positive integer ID."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

    @staticmethod
    def _get_notification_id(
        notification: Notification,
    ) -> int:
        """Return the notification primary key."""

        return notification.id

    # =====================================================
    # CUSTOMER PREFERENCE VALIDATION
    # =====================================================

    def _get_preferences(
        self,
        customer_id: int,
    ) -> NotificationPreference:
        """Get existing preferences or create default preferences."""

        return self.repository.get_or_create_customer_preferences(
            customer_id
        )

    def _is_notification_allowed(
        self,
        customer_id: int,
        channel: str,
        notification_type: str,
    ) -> bool:
        """
        Check whether a notification is permitted by preferences.

        Checks:
        - Channel preference.
        - Notification category preference.
        """

        preferences = self._get_preferences(customer_id)

        channel_preferences = {
            "email": preferences.email_enabled,
            "in_app": preferences.in_app_enabled,
        }

        if channel not in channel_preferences:
            raise ValueError(
                f"Unsupported notification channel: {channel}"
            )

        if not channel_preferences[channel]:
            return False

        category_field = self.NOTIFICATION_CATEGORIES.get(
            notification_type.lower()
        )

        if category_field is not None:
            category_enabled = getattr(
                preferences,
                category_field,
                True,
            )

            if not category_enabled:
                return False

        return True

    # =====================================================
    # CREATE NOTIFICATION
    # =====================================================

    def create_notification(
        self,
        data: Any,
    ) -> tuple[Notification, bool]:
        """
        Create a notification.

        Uses the repository's idempotency protection.

        Returns:
            (notification, created)

        created=True:
            A new notification was created.

        created=False:
            A notification with the same idempotency key
            already exists.
        """

        try:
            notification_data = self._to_dict(data)

            channel = notification_data.get("channel")
            notification_type = notification_data.get(
                "notification_type",
                "",
            )
            customer_id = notification_data.get("customer_id")

            if channel not in self.SUPPORTED_CHANNELS:
                raise ValueError(
                    "Channel must be either 'email' or 'in_app'."
                )

            if not notification_data.get("recipient"):
                raise ValueError(
                    "Notification recipient is required."
                )

            if not notification_data.get("message"):
                raise ValueError(
                    "Notification message is required."
                )

            if customer_id is not None:
                self._validate_id(
                    customer_id,
                    "Customer ID",
                )

                allowed = self._is_notification_allowed(
                    customer_id=customer_id,
                    channel=channel,
                    notification_type=notification_type,
                )

                if not allowed:
                    raise ValueError(
                        "This notification is disabled "
                        "in the customer's preferences."
                    )

            notification, created = (
                self.repository.create_notification_if_new(
                    notification_data
                )
            )

            self._commit()

            return notification, created

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # GET NOTIFICATION
    # =====================================================

    def get_notification(
        self,
        notification_id: int,
    ) -> Notification | None:
        """Retrieve a notification using its ID."""

        self._validate_id(
            notification_id,
            "Notification ID",
        )

        return self.repository.get_notification_by_id(
            notification_id
        )

    def get_customer_notification(
        self,
        notification_id: int,
        customer_id: int,
    ) -> Notification | None:
        """Retrieve a notification belonging to a customer."""

        self._validate_id(notification_id, "Notification ID")
        self._validate_id(customer_id, "Customer ID")

        return self.repository.get_customer_notification(
            notification_id=notification_id,
            customer_id=customer_id,
        )

    # =====================================================
    # CUSTOMER NOTIFICATION LIST
    # =====================================================

    def get_customer_notifications(
        self,
        customer_id: int,
        page: int = 1,
        page_size: int = 20,
        channel: str | None = None,
        status: str | None = None,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        """
        Get paginated notifications for a customer.

        Returns:
            notifications, total_count
        """

        self._validate_id(customer_id, "Customer ID")

        return self.repository.get_customer_notifications(
            customer_id=customer_id,
            page=page,
            page_size=page_size,
            channel=channel,
            status=status,
            unread_only=unread_only,
        )

    # =====================================================
    # UPDATE NOTIFICATION
    # =====================================================

    def update_notification(
        self,
        notification_id: int,
        data: Any,
    ) -> Notification | None:
        """Update notification fields."""

        self._validate_id(
            notification_id,
            "Notification ID",
        )

        try:
            update_data = self._to_dict(data)

            notification = self.repository.update_notification(
                notification_id=notification_id,
                data=update_data,
            )

            if notification is None:
                self._rollback()
                return None

            self._commit()

            return notification

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # PROCESS NOTIFICATION
    # =====================================================

    def process_notification(
        self,
        notification_id: int,
    ) -> Notification | None:
        """
        Process a pending or failed notification.

        Email:
            Calls the configured email_sender.

        In-app:
            Marks the notification as sent internally.

        Important:
            This method marks email notifications as sent
            after the email provider function succeeds.
            Actual delivery confirmation must be handled
            separately through mark_notification_delivered().
        """

        self._validate_id(
            notification_id,
            "Notification ID",
        )

        # Keep a local reference. This allows Pylance to
        # verify that the callable is not None before use.
        email_sender = self.email_sender

        notification = self.repository.get_notification_by_id(
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
                "can be processed."
            )

        if notification.scheduled_at is not None:
            scheduled_at = notification.scheduled_at

            # Normalize naive timestamps to UTC for comparison.
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(
                    tzinfo=timezone.utc
                )

            if scheduled_at > datetime.now(timezone.utc):
                raise ValueError(
                    "This notification is scheduled for a future time."
                )

        if notification.channel not in self.SUPPORTED_CHANNELS:
            raise ValueError(
                f"Unsupported channel: {notification.channel}"
            )

        if (
            notification.channel == "email"
            and email_sender is None
        ):
            raise RuntimeError(
                "Email sender is not configured. "
                "Configure the email integration before "
                "processing email notifications."
            )

        try:
            # Step 1: Mark as processing and commit.
            processing_notification = (
                self.repository.mark_notification_processing(
                    notification_id
                )
            )

            if processing_notification is None:
                self._rollback()
                return None

            self._commit()

            # Step 2: Deliver according to channel.
            if processing_notification.channel == "email":

                # Pylance-safe callable check.
                if email_sender is None:
                    raise RuntimeError(
                        "Email sender is not configured."
                    )

                result = email_sender(
                    processing_notification.recipient,
                    (
                        processing_notification.subject
                        or "Finmarket Kart Notification"
                    ),
                    processing_notification.message,
                )

                provider = "email"
                provider_message_id = None

                # Support a provider response dictionary.
                if isinstance(result, dict):
                    provider = result.get(
                        "provider",
                        "email",
                    )
                    provider_message_id = result.get(
                        "message_id"
                    )

                # Support a provider response string.
                elif isinstance(result, str):
                    provider_message_id = result

            elif processing_notification.channel == "in_app":
                provider = "internal"
                provider_message_id = None

            else:
                raise ValueError(
                    "Unsupported notification channel."
                )

            # Step 3: Mark as sent.
            sent_notification = (
                self.repository.mark_notification_sent(
                    notification_id=notification_id,
                    provider=provider,
                    provider_message_id=provider_message_id,
                )
            )

            self._commit()

            return sent_notification

        except Exception as exc:
            # The processing transaction may already have
            # been committed, so start a fresh transaction.
            self._rollback()

            try:
                self.repository.mark_notification_failed(
                    notification_id=notification_id,
                    error_message=str(exc),
                    increment_retry=True,
                )

                self._commit()

            except Exception:
                self._rollback()

            raise

    # =====================================================
    # MARK NOTIFICATION DELIVERED
    # =====================================================

    def mark_notification_delivered(
        self,
        notification_id: int,
    ) -> Notification | None:
        """
        Mark a sent notification as delivered.

        Usually called by an email provider webhook
        or another delivery confirmation mechanism.
        """

        self._validate_id(
            notification_id,
            "Notification ID",
        )

        try:
            notification = (
                self.repository.mark_notification_delivered(
                    notification_id
                )
            )

            if notification is None:
                self._rollback()
                return None

            self._commit()

            return notification

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # CANCEL NOTIFICATION
    # =====================================================

    def cancel_notification(
        self,
        notification_id: int,
    ) -> Notification | None:
        """Cancel a notification that has not been sent."""

        self._validate_id(
            notification_id,
            "Notification ID",
        )

        try:
            notification = self.repository.cancel_notification(
                notification_id
            )

            if notification is None:
                self._rollback()
                return None

            self._commit()

            return notification

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # MARK SINGLE NOTIFICATION AS READ
    # =====================================================

    def mark_notification_read(
        self,
        notification_id: int,
        customer_id: int,
    ) -> Notification | None:
        """Mark a customer's notification as read."""

        self._validate_id(
            notification_id,
            "Notification ID",
        )
        self._validate_id(
            customer_id,
            "Customer ID",
        )

        try:
            notification = (
                self.repository.mark_notification_read(
                    notification_id=notification_id,
                    customer_id=customer_id,
                )
            )

            if notification is None:
                self._rollback()
                return None

            self._commit()

            return notification

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # MARK ALL NOTIFICATIONS AS READ
    # =====================================================

    def mark_all_notifications_read(
        self,
        customer_id: int,
    ) -> int:
        """Mark all unread in-app notifications as read."""

        self._validate_id(
            customer_id,
            "Customer ID",
        )

        try:
            updated_count = (
                self.repository.mark_all_notifications_read(
                    customer_id
                )
            )

            self._commit()

            return updated_count

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # COUNT UNREAD NOTIFICATIONS
    # =====================================================

    def count_unread_notifications(
        self,
        customer_id: int,
    ) -> int:
        """Count unread in-app notifications."""

        self._validate_id(
            customer_id,
            "Customer ID",
        )

        return self.repository.count_unread_notifications(
            customer_id
        )

    # =====================================================
    # CUSTOMER NOTIFICATION PREFERENCES
    # =====================================================

    def get_customer_preferences(
        self,
        customer_id: int,
    ) -> NotificationPreference | None:
        """Retrieve customer notification preferences."""

        self._validate_id(
            customer_id,
            "Customer ID",
        )

        return self.repository.get_customer_preferences(
            customer_id
        )

    def get_or_create_customer_preferences(
        self,
        customer_id: int,
    ) -> NotificationPreference:
        """Get preferences or create default preferences."""

        self._validate_id(
            customer_id,
            "Customer ID",
        )

        try:
            preferences = (
                self.repository.get_or_create_customer_preferences(
                    customer_id
                )
            )

            self._commit()

            return preferences

        except Exception:
            self._rollback()
            raise

    def update_customer_preferences(
        self,
        customer_id: int,
        data: Any,
    ) -> NotificationPreference:
        """Update a customer's notification preferences."""

        self._validate_id(
            customer_id,
            "Customer ID",
        )

        try:
            update_data = self._to_dict(data)

            preferences = (
                self.repository.update_customer_preferences(
                    customer_id=customer_id,
                    data=update_data,
                )
            )

            self._commit()

            return preferences

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # RETRY SINGLE NOTIFICATION
    # =====================================================

    def retry_notification(
        self,
        notification_id: int,
    ) -> Notification | None:
        """
        Retry a failed notification.

        A notification can be retried only if:
        - Its current status is failed.
        - Its retry_count is below max_retries.
        """

        self._validate_id(
            notification_id,
            "Notification ID",
        )

        notification = self.repository.get_notification_by_id(
            notification_id
        )

        if notification is None:
            return None

        if notification.status != "failed":
            raise ValueError(
                "Only failed notifications can be retried."
            )

        if notification.retry_count >= notification.max_retries:
            raise ValueError(
                "Maximum notification retry attempts reached."
            )

        return self.process_notification(
            notification_id
        )

    # =====================================================
    # RETRY FAILED NOTIFICATIONS IN BATCH
    # =====================================================

    def retry_failed_notifications(
        self,
        limit: int = 50,
    ) -> list[Notification]:
        """
        Retry failed notifications that are eligible for retry.

        Returns the successfully processed notification records.
        """

        try:
            notifications = (
                self.repository.get_retryable_notifications(
                    limit=limit
                )
            )

        except Exception:
            self._rollback()
            raise

        processed: list[Notification] = []

        for notification in notifications:
            try:
                result = self.process_notification(
                    notification.id
                )

                if result is not None:
                    processed.append(result)

            except Exception:
                # One failed notification must not stop
                # the remaining notifications from processing.
                continue

        return processed

    # =====================================================
    # PROCESS PENDING NOTIFICATIONS IN BATCH
    # =====================================================

    def process_pending_notifications(
        self,
        limit: int = 50,
    ) -> list[Notification]:
        """
        Process pending notifications that are ready.

        Each notification is processed independently.
        """

        try:
            notifications = (
                self.repository.get_pending_notifications(
                    limit=limit
                )
            )

        except Exception:
            self._rollback()
            raise

        processed: list[Notification] = []

        for notification in notifications:
            try:
                result = self.process_notification(
                    notification.id
                )

                if result is not None:
                    processed.append(result)

            except Exception:
                # Continue processing the remaining records.
                continue

        return processed

    # =====================================================
    # COUNT NOTIFICATIONS BY STATUS
    # =====================================================

    def count_notifications_by_status(
        self,
        status: str,
        channel: str | None = None,
    ) -> int:
        """Count notifications by status and optional channel."""

        return self.repository.count_notifications_by_status(
            status=status,
            channel=channel,
        )

    # =====================================================
    # NOTIFICATION SUMMARY
    # =====================================================

    def get_notification_summary(
        self,
        customer_id: int | None = None,
    ) -> dict[str, int]:
        """Get notification counts grouped by status."""

        if customer_id is not None:
            self._validate_id(
                customer_id,
                "Customer ID",
            )

        return self.repository.get_notification_summary(
            customer_id=customer_id
        )
