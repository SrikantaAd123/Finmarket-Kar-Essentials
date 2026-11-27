
"""Order cancellation workflow for Finmarket Kart Essentials.

Responsibilities:
- Validate cancellation requests.
- Verify order ownership.
- Enforce cancellation eligibility.
- Cancel an order.
- Record a cancellation tracking event.

Payment refunds, inventory restoration and notifications
are handled by their respective modules.

Database commits are controlled by the caller.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.models.order import Order
from backend.repositories.order_repository import OrderRepository


class OrderCancellationError(ValueError):
    """Raised when an order cancellation operation fails."""


class OrderCancellation:
    """Business logic for customer and administrative cancellations."""

    CANCELLABLE_STATUSES = {
        "pending",
        "confirmed",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OrderRepository(db)

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def _validate_id(
        value: int,
        field_name: str,
    ) -> None:
        """Validate a positive integer identifier."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise OrderCancellationError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise OrderCancellationError(
                f"{field_name} must be greater than zero."
            )

    @staticmethod
    def _validate_reason(reason: str) -> str:
        """Validate and normalize the cancellation reason."""

        if not isinstance(reason, str):
            raise OrderCancellationError(
                "Cancellation reason must be a string."
            )

        normalized = reason.strip()

        if not normalized:
            raise OrderCancellationError(
                "A cancellation reason is required."
            )

        if len(normalized) > 2000:
            raise OrderCancellationError(
                "Cancellation reason cannot exceed 2000 characters."
            )

        return normalized

    @staticmethod
    def _validate_actor(actor: str) -> str:
        """Validate the identity of the cancellation requester."""

        if not isinstance(actor, str) or not actor.strip():
            raise OrderCancellationError(
                "Cancellation requester is required."
            )

        return actor.strip()[:255]

    # =====================================================
    # ORDER RETRIEVAL
    # =====================================================

    def get_order(
        self,
        order_id: int,
        customer_id: int | None = None,
    ) -> Order:
        """Retrieve an order and optionally verify its owner."""

        self._validate_id(order_id, "Order ID")

        if customer_id is not None:
            self._validate_id(customer_id, "Customer ID")

        order = self.repository.get_order_by_id(order_id)

        if order is None:
            raise OrderCancellationError(
                "Order not found."
            )

        if (
            customer_id is not None
            and order.customer_id != customer_id
        ):
            # Do not reveal whether another customer's order exists.
            raise OrderCancellationError(
                "Order not found."
            )

        return order

    # =====================================================
    # CANCELLATION ELIGIBILITY
    # =====================================================

    @classmethod
    def is_cancellable(cls, order: Order) -> bool:
        """Check whether an order can currently be cancelled."""

        return order.status in cls.CANCELLABLE_STATUSES

    @classmethod
    def validate_cancellation_eligibility(
        cls,
        order: Order,
    ) -> None:
        """Raise an error if the order cannot be cancelled."""

        if order.status not in cls.CANCELLABLE_STATUSES:
            raise OrderCancellationError(
                "Order cannot be cancelled while its status "
                f"is '{order.status}'. "
                "Only pending and confirmed orders can be cancelled."
            )

    # =====================================================
    # CANCEL ORDER
    # =====================================================

    def cancel_order(
        self,
        order_id: int,
        reason: str,
        *,
        customer_id: int | None = None,
        cancelled_by: str | None = None,
    ) -> Order:
        """Cancel an eligible order.

        Args:
            order_id:
                ID of the order to cancel.

            reason:
                Mandatory cancellation reason.

            customer_id:
                Optional customer ID. When provided, ownership
                of the order is verified.

            cancelled_by:
                Identifier of the customer, administrator,
                or system initiating the cancellation.

        Returns:
            Updated Order instance.

        Note:
            This method uses flush(), not commit().
            The caller owns transaction management.
        """

        self._validate_id(order_id, "Order ID")

        normalized_reason = self._validate_reason(reason)

        actor = self._validate_actor(
            cancelled_by
            or (
                f"customer:{customer_id}"
                if customer_id is not None
                else "admin"
            )
        )

        # Retrieve order and check ownership.
        order = self.get_order(
            order_id=order_id,
            customer_id=customer_id,
        )

        # Enforce cancellation policy.
        self.validate_cancellation_eligibility(order)

        # Update order status through the existing repository.
        cancelled_order = self.repository.cancel_order(
            order_id=order_id,
            reason=normalized_reason,
            allowed_statuses=self.CANCELLABLE_STATUSES,
        )

        if cancelled_order is None:
            raise OrderCancellationError(
                "Order could not be cancelled."
            )

        # Record cancellation history.
        self.repository.add_tracking_event(
            order_id=order_id,
            status="cancelled",
            title="Order cancelled",
            description=normalized_reason,
            updated_by=actor,
        )

        # Retrieve updated order with its tracking events.
        result = self.repository.get_order_by_id(order_id)

        if result is None:
            raise OrderCancellationError(
                "Cancelled order could not be retrieved."
            )

        return result

    # =====================================================
    # CUSTOMER CANCELLATION
    # =====================================================

    def cancel_customer_order(
        self,
        order_id: int,
        customer_id: int,
        reason: str,
    ) -> Order:
        """Cancel an order belonging to a specific customer."""

        self._validate_id(customer_id, "Customer ID")

        return self.cancel_order(
            order_id=order_id,
            reason=reason,
            customer_id=customer_id,
            cancelled_by=f"customer:{customer_id}",
        )

    # =====================================================
    # ADMINISTRATIVE CANCELLATION
    # =====================================================

    def cancel_admin_order(
        self,
        order_id: int,
        reason: str,
        admin_identifier: str,
    ) -> Order:
        """Cancel an order through an authorized admin workflow.

        Admin authorization must be enforced by the API layer.
        """

        actor = self._validate_actor(admin_identifier)

        return self.cancel_order(
            order_id=order_id,
            reason=reason,
            cancelled_by=actor,
        )

    # =====================================================
    # CANCELLATION PREVIEW
    # =====================================================

    def get_cancellation_eligibility(
        self,
        order_id: int,
        customer_id: int | None = None,
    ) -> dict[str, Any]:
        """Return cancellation eligibility without changing the order."""

        order = self.get_order(
            order_id=order_id,
            customer_id=customer_id,
        )

        eligible = self.is_cancellable(order)

        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "current_status": order.status,
            "can_cancel": eligible,
            "allowed_statuses": sorted(
                self.CANCELLABLE_STATUSES
            ),
            "message": (
                "Order is eligible for cancellation."
                if eligible
                else (
                    "Order cannot be cancelled in its "
                    f"current status: {order.status}."
                )
            ),
        }


__all__ = [
    "OrderCancellation",
    "OrderCancellationError",
]
