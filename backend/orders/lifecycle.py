
"""
Order lifecycle management.

Responsibilities:
- Validate order and payment statuses.
- Enforce allowed order-status transitions.
- Update order and payment statuses.
- Record order tracking events.
- Retrieve tracking history and lifecycle summaries.

Transaction handling:
This module does not commit or roll back transactions.
The calling service or API endpoint owns the transaction.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.order_repository import OrderRepository


class OrderLifecycleError(ValueError):
    """Raised when an order lifecycle operation is invalid."""


class OrderLifecycle:
    """Manage order status transitions and tracking history."""

    ORDER_STATUSES = {
        "pending",
        "confirmed",
        "processing",
        "packed",
        "shipped",
        "out_for_delivery",
        "delivered",
        "cancelled",
        "returned",
    }

    PAYMENT_STATUSES = {
        "pending",
        "paid",
        "failed",
        "refunded",
        "partially_refunded",
    }

    # Cancellation is restricted to pending and confirmed orders.
    # This matches the cancellation workflow.
    ALLOWED_TRANSITIONS = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"processing", "cancelled"},
        "processing": {"packed"},
        "packed": {"shipped"},
        "shipped": {"out_for_delivery"},
        "out_for_delivery": {"delivered"},
        "delivered": {"returned"},
        "cancelled": set(),
        "returned": set(),
    }

    TERMINAL_STATUSES = {
        "cancelled",
        "returned",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OrderRepository(db)

    # ---------------------------------------------------------
    # VALIDATION HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _validate_id(value: int, field_name: str = "ID") -> int:
        """Validate a positive integer identifier."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise OrderLifecycleError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise OrderLifecycleError(
                f"{field_name} must be greater than zero."
            )

        return value

    @staticmethod
    def _validate_text(
        value: str | None,
        field_name: str,
        *,
        required: bool = False,
        max_length: int | None = None,
    ) -> str | None:
        """Validate and normalize required or optional text."""

        if value is None:
            if required:
                raise OrderLifecycleError(
                    f"{field_name} is required."
                )
            return None

        if not isinstance(value, str):
            raise OrderLifecycleError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if required and not normalized:
            raise OrderLifecycleError(
                f"{field_name} cannot be empty."
            )

        if max_length is not None and len(normalized) > max_length:
            raise OrderLifecycleError(
                f"{field_name} cannot exceed "
                f"{max_length} characters."
            )

        return normalized or None

    # ---------------------------------------------------------
    # STATUS VALIDATION
    # ---------------------------------------------------------

    @classmethod
    def validate_order_status(cls, status: str) -> str:
        """Validate an order status."""

        normalized = cls._validate_text(
            status,
            "Order status",
            required=True,
            max_length=50,
        )

        if normalized is None:
            raise OrderLifecycleError(
                "Order status is required."
            )

        normalized = normalized.lower()

        if normalized not in cls.ORDER_STATUSES:
            raise OrderLifecycleError(
                f"Invalid order status: {normalized}. "
                f"Allowed statuses: {sorted(cls.ORDER_STATUSES)}"
            )

        return normalized

    @classmethod
    def validate_payment_status(cls, status: str) -> str:
        """Validate a payment status."""

        normalized = cls._validate_text(
            status,
            "Payment status",
            required=True,
            max_length=50,
        )

        if normalized is None:
            raise OrderLifecycleError(
                "Payment status is required."
            )

        normalized = normalized.lower()

        if normalized not in cls.PAYMENT_STATUSES:
            raise OrderLifecycleError(
                f"Invalid payment status: {normalized}. "
                f"Allowed statuses: {sorted(cls.PAYMENT_STATUSES)}"
            )

        return normalized

    # ---------------------------------------------------------
    # ORDER RETRIEVAL
    # ---------------------------------------------------------

    def get_order(self, order_id: int) -> Any:
        """Retrieve an order by its ID."""

        order_id = self._validate_id(order_id, "Order ID")

        order = self.repository.get_order_by_id(order_id)

        if order is None:
            raise OrderLifecycleError(
                f"Order with ID {order_id} was not found."
            )

        return order

    # ---------------------------------------------------------
    # TRANSITION VALIDATION
    # ---------------------------------------------------------

    @classmethod
    def can_transition(
        cls,
        current_status: str,
        new_status: str,
    ) -> bool:
        """Return whether a status transition is permitted."""

        current = cls.validate_order_status(current_status)
        new = cls.validate_order_status(new_status)

        if current == new:
            return False

        return new in cls.ALLOWED_TRANSITIONS.get(current, set())

    @classmethod
    def validate_transition(
        cls,
        current_status: str,
        new_status: str,
    ) -> None:
        """Raise an error if an order transition is not permitted."""

        current = cls.validate_order_status(current_status)
        new = cls.validate_order_status(new_status)

        if current == new:
            raise OrderLifecycleError(
                f"Order is already in '{current}' status."
            )

        allowed = cls.ALLOWED_TRANSITIONS.get(current, set())

        if new not in allowed:
            raise OrderLifecycleError(
                f"Cannot change order status from "
                f"'{current}' to '{new}'. "
                f"Allowed next statuses: {sorted(allowed)}"
            )

    # ---------------------------------------------------------
    # TRACKING EVENTS
    # ---------------------------------------------------------

    def add_tracking_event(
        self,
        order_id: int,
        status: str,
        title: str,
        description: str | None = None,
        location: str | None = None,
        updated_by: str | None = None,
    ) -> Any:
        """Create a tracking event for an order."""

        order_id = self._validate_id(order_id, "Order ID")
        normalized_status = self.validate_order_status(status)

        normalized_title = self._validate_text(
            title,
            "Tracking title",
            required=True,
            max_length=255,
        )

        if normalized_title is None:
            raise OrderLifecycleError(
                "Tracking title is required."
            )

        normalized_description = self._validate_text(
            description,
            "Tracking description",
            max_length=2000,
        )

        normalized_location = self._validate_text(
            location,
            "Tracking location",
            max_length=255,
        )

        normalized_updated_by = self._validate_text(
            updated_by,
            "Updated by",
            max_length=255,
        )

        # Confirm that the order exists before adding its event.
        self.get_order(order_id)

        return self.repository.add_tracking_event(
            order_id=order_id,
            status=normalized_status,
            title=normalized_title,
            description=normalized_description,
            location=normalized_location,
            updated_by=normalized_updated_by,
        )

    # ---------------------------------------------------------
    # UPDATE ORDER STATUS
    # ---------------------------------------------------------

    def update_order_status(
        self,
        order_id: int,
        new_status: str,
        *,
        updated_by: str = "admin",
        description: str | None = None,
        location: str | None = None,
    ) -> Any:
        """Validate and update an order status, then record tracking."""

        order_id = self._validate_id(order_id, "Order ID")
        normalized_status = self.validate_order_status(new_status)

        normalized_updated_by = self._validate_text(
            updated_by,
            "Updated by",
            required=True,
            max_length=255,
        )

        if normalized_updated_by is None:
            raise OrderLifecycleError(
                "Updated by is required."
            )

        normalized_description = self._validate_text(
            description,
            "Description",
            max_length=2000,
        )

        normalized_location = self._validate_text(
            location,
            "Location",
            max_length=255,
        )

        order = self.get_order(order_id)

        # Preserve the old status before the repository updates it.
        previous_status = str(order.status).lower()

        self.validate_transition(
            previous_status,
            normalized_status,
        )

        updated_order = self.repository.update_order_status(
            order_id,
            normalized_status,
        )

        if updated_order is None:
            raise OrderLifecycleError(
                f"Unable to update order with ID {order_id}."
            )

        # Create a useful description if the caller did not provide one.
        tracking_description = normalized_description

        if tracking_description is None:
            tracking_description = (
                f"Order status changed from "
                f"'{previous_status}' to '{normalized_status}'."
            )

        tracking_title = (
            f"Order {normalized_status.replace('_', ' ').title()}"
        )

        self.repository.add_tracking_event(
            order_id=order_id,
            status=normalized_status,
            title=tracking_title,
            description=tracking_description,
            location=normalized_location,
            updated_by=normalized_updated_by,
        )

        # Return the latest order state.
        return self.repository.get_order_by_id(order_id)

    # ---------------------------------------------------------
    # UPDATE PAYMENT STATUS
    # ---------------------------------------------------------

    def update_payment_status(
        self,
        order_id: int,
        new_payment_status: str,
    ) -> Any:
        """Validate and update an order's payment status."""

        order_id = self._validate_id(order_id, "Order ID")

        normalized_payment_status = self.validate_payment_status(
            new_payment_status
        )

        self.get_order(order_id)

        updated_order = self.repository.update_payment_status(
            order_id,
            normalized_payment_status,
        )

        if updated_order is None:
            raise OrderLifecycleError(
                f"Unable to update payment status for "
                f"order ID {order_id}."
            )

        return updated_order

    # ---------------------------------------------------------
    # TRACKING HISTORY
    # ---------------------------------------------------------

    def get_tracking_history(self, order_id: int) -> list[Any]:
        """Retrieve tracking events for an order."""

        order_id = self._validate_id(order_id, "Order ID")

        self.get_order(order_id)

        events = self.repository.get_order_tracking(order_id)

        return list(events or [])

    # ---------------------------------------------------------
    # LIFECYCLE SUMMARY
    # ---------------------------------------------------------

    def get_lifecycle_summary(self, order_id: int) -> dict[str, Any]:
        """Return a summary of an order's current lifecycle state."""

        order_id = self._validate_id(order_id, "Order ID")

        order = self.get_order(order_id)
        tracking_history = self.get_tracking_history(order_id)

        current_status = str(order.status).lower()
        current_payment_status = str(order.payment_status).lower()

        allowed_next_statuses = sorted(
            self.ALLOWED_TRANSITIONS.get(current_status, set())
        )

        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "order_status": current_status,
            "payment_status": current_payment_status,
            "is_terminal": (
                current_status in self.TERMINAL_STATUSES
            ),
            "allowed_next_statuses": allowed_next_statuses,
            "tracking_event_count": len(tracking_history),
            "tracking_history": tracking_history,
        }
