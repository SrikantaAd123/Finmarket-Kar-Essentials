
"""
Order return management.

Responsibilities:
- Create customer return requests.
- Validate order ownership and returnable quantities.
- Prevent duplicate returns of the same order-item quantities.
- Approve or reject return requests.
- Record pickup, receipt, and refund completion.
- Retrieve return requests and summaries.

Important:
- This module does not initiate payment-provider refunds.
- Refund amounts are calculated from original order-item prices.
- This module does not commit or roll back transactions.
  The calling service or API endpoint owns the transaction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.order import Order, OrderItem
from backend.models.order_return import OrderReturn, OrderReturnItem


class OrderReturnError(ValueError):
    """Raised when an order return operation is invalid."""


class OrderReturns:
    """Manage customer order returns and refund records."""

    RETURN_STATUSES = {
        "requested",
        "approved",
        "rejected",
        "picked_up",
        "received",
        "refunded",
        "cancelled",
    }

    REFUND_STATUSES = {
        "not_required",
        "pending",
        "processing",
        "completed",
        "failed",
    }

    ACTIVE_RETURN_STATUSES = {
        "requested",
        "approved",
        "picked_up",
        "received",
        "refunded",
    }

    ALLOWED_TRANSITIONS = {
        "requested": {"approved", "rejected", "cancelled"},
        "approved": {"picked_up", "received"},
        "picked_up": {"received"},
        "received": {"refunded"},
        "rejected": set(),
        "refunded": set(),
        "cancelled": set(),
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    # =========================================================
    # VALIDATION HELPERS
    # =========================================================

    @staticmethod
    def _validate_id(value: int, field_name: str) -> int:
        """Validate a positive integer ID."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise OrderReturnError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise OrderReturnError(
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
        """Validate and normalize text."""

        if value is None:
            if required:
                raise OrderReturnError(
                    f"{field_name} is required."
                )
            return None

        if not isinstance(value, str):
            raise OrderReturnError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if required and not normalized:
            raise OrderReturnError(
                f"{field_name} cannot be empty."
            )

        if max_length is not None and len(normalized) > max_length:
            raise OrderReturnError(
                f"{field_name} cannot exceed "
                f"{max_length} characters."
            )

        return normalized or None

    @staticmethod
    def _to_decimal(value: Any, field_name: str) -> Decimal:
        """Convert a value to Decimal safely."""

        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise OrderReturnError(
                f"Invalid monetary value for {field_name}."
            ) from exc

        if not amount.is_finite():
            raise OrderReturnError(
                f"{field_name} must be a finite amount."
            )

        if amount < 0:
            raise OrderReturnError(
                f"{field_name} cannot be negative."
            )

        return amount.quantize(Decimal("0.01"))

    @staticmethod
    def _now() -> datetime:
        """Return the current UTC time."""

        return datetime.now(timezone.utc)

    @classmethod
    def _validate_reviewer(
        cls,
        reviewed_by: str,
    ) -> str:
        """
        Validate reviewer ID.

        The OrderReturn model stores reviewed_by as a string.
        """

        normalized_reviewer = cls._validate_text(
            reviewed_by,
            "Reviewer ID",
            required=True,
            max_length=255,
        )

        if normalized_reviewer is None:
            raise OrderReturnError(
                "Reviewer ID is required."
            )

        return normalized_reviewer

    # =========================================================
    # ORDER AND RETURN RETRIEVAL
    # =========================================================

    def get_order(self, order_id: int) -> Order:
        """Retrieve an order by ID."""

        order_id = self._validate_id(
            order_id,
            "Order ID",
        )

        order = self.db.get(Order, order_id)

        if order is None:
            raise OrderReturnError(
                f"Order with ID {order_id} was not found."
            )

        return order

    def get_return(
        self,
        return_id: int,
        *,
        customer_id: int | None = None,
    ) -> OrderReturn:
        """Retrieve a return request, optionally checking ownership."""

        return_id = self._validate_id(
            return_id,
            "Return ID",
        )

        return_request = self.db.get(
            OrderReturn,
            return_id,
        )

        if return_request is None:
            raise OrderReturnError(
                f"Return request with ID {return_id} was not found."
            )

        if customer_id is not None:
            customer_id = self._validate_id(
                customer_id,
                "Customer ID",
            )

            if return_request.customer_id != customer_id:
                raise OrderReturnError(
                    "You are not authorized to access this return request."
                )

        return return_request

    def list_returns(
        self,
        *,
        customer_id: int | None = None,
        order_id: int | None = None,
        status: str | None = None,
    ) -> list[OrderReturn]:
        """List return requests with optional filters."""

        statement = select(OrderReturn)

        if customer_id is not None:
            customer_id = self._validate_id(
                customer_id,
                "Customer ID",
            )

            statement = statement.where(
                OrderReturn.customer_id == customer_id
            )

        if order_id is not None:
            order_id = self._validate_id(
                order_id,
                "Order ID",
            )

            statement = statement.where(
                OrderReturn.order_id == order_id
            )

        if status is not None:
            normalized_status = self._validate_text(
                status,
                "Return status",
                required=True,
                max_length=50,
            )

            if normalized_status is None:
                raise OrderReturnError(
                    "Return status is required."
                )

            normalized_status = normalized_status.lower()

            if normalized_status not in self.RETURN_STATUSES:
                raise OrderReturnError(
                    f"Invalid return status: {normalized_status}."
                )

            statement = statement.where(
                OrderReturn.status == normalized_status
            )

        statement = statement.order_by(
            OrderReturn.created_at.desc()
        )

        return list(self.db.scalars(statement).all())

    # =========================================================
    # RETURN QUANTITY VALIDATION
    # =========================================================

    def _get_previously_returned_quantity(
        self,
        order_item_id: int,
    ) -> int:
        """Calculate quantities reserved by existing active returns."""

        statement = (
            select(
                func.coalesce(
                    func.sum(OrderReturnItem.quantity),
                    0,
                )
            )
            .join(
                OrderReturn,
                OrderReturn.id == OrderReturnItem.return_id,
            )
            .where(
                OrderReturnItem.order_item_id == order_item_id,
                OrderReturn.status.in_(
                    self.ACTIVE_RETURN_STATUSES
                ),
            )
        )

        result = self.db.scalar(statement)

        return int(result or 0)

    def _validate_return_items(
        self,
        order_id: int,
        requested_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Validate requested items and calculate refund amounts."""

        if not requested_items:
            raise OrderReturnError(
                "At least one item is required for a return."
            )

        order_items = self.db.scalars(
            select(OrderItem).where(
                OrderItem.order_id == order_id
            )
        ).all()

        order_items_by_id = {
            item.id: item for item in order_items
        }

        validated_items: list[dict[str, Any]] = []
        seen_item_ids: set[int] = set()

        for requested_item in requested_items:
            if not isinstance(requested_item, dict):
                raise OrderReturnError(
                    "Each return item must be a dictionary."
                )

            raw_item_id = requested_item.get("order_item_id")
            raw_quantity = requested_item.get("quantity")

            # Validate the dictionary value before passing it
            # to the method that requires an integer.
            if (
                isinstance(raw_item_id, bool)
                or not isinstance(raw_item_id, int)
            ):
                raise OrderReturnError(
                    "Order item ID must be a valid integer."
                )

            item_id = self._validate_id(
                raw_item_id,
                "Order item ID",
            )

            if item_id in seen_item_ids:
                raise OrderReturnError(
                    f"Order item {item_id} appears more than once."
                )

            seen_item_ids.add(item_id)

            if (
                isinstance(raw_quantity, bool)
                or not isinstance(raw_quantity, int)
                or raw_quantity <= 0
            ):
                raise OrderReturnError(
                    "Return quantity must be a positive integer."
                )

            order_item = order_items_by_id.get(item_id)

            if order_item is None:
                raise OrderReturnError(
                    f"Order item {item_id} does not belong "
                    f"to order {order_id}."
                )

            ordered_quantity = int(order_item.quantity)

            already_returned = (
                self._get_previously_returned_quantity(item_id)
            )

            available_quantity = (
                ordered_quantity - already_returned
            )

            if raw_quantity > available_quantity:
                raise OrderReturnError(
                    f"Cannot return {raw_quantity} units of "
                    f"order item {item_id}. "
                    f"Available return quantity: {available_quantity}."
                )

            unit_price = self._to_decimal(
                order_item.unit_price,
                "Unit price",
            )

            refund_amount = (
                unit_price * raw_quantity
            ).quantize(Decimal("0.01"))

            validated_items.append(
                {
                    "order_item_id": item_id,
                    "product_name": order_item.product_name,
                    "product_sku": order_item.product_sku,
                    "quantity": raw_quantity,
                    "unit_price": unit_price,
                    "refund_amount": refund_amount,
                }
            )

        return validated_items

    # =========================================================
    # CREATE RETURN REQUEST
    # =========================================================

    def request_return(
        self,
        *,
        order_id: int,
        customer_id: int,
        reason: str,
        items: list[dict[str, Any]],
        description: str | None = None,
    ) -> OrderReturn:
        """Create a return request for a customer's delivered order."""

        order_id = self._validate_id(
            order_id,
            "Order ID",
        )

        customer_id = self._validate_id(
            customer_id,
            "Customer ID",
        )

        normalized_reason = self._validate_text(
            reason,
            "Return reason",
            required=True,
            max_length=255,
        )

        if normalized_reason is None:
            raise OrderReturnError(
                "Return reason is required."
            )

        normalized_description = self._validate_text(
            description,
            "Return description",
            max_length=2000,
        )

        order = self.get_order(order_id)

        if order.customer_id != customer_id:
            raise OrderReturnError(
                "This order does not belong to the specified customer."
            )

        if str(order.status).lower() != "delivered":
            raise OrderReturnError(
                "Only delivered orders can be returned."
            )

        validated_items = self._validate_return_items(
            order_id,
            items,
        )

        total_refund = sum(
            (
                item["refund_amount"]
                for item in validated_items
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

        return_request = OrderReturn(
            order_id=order_id,
            customer_id=customer_id,
            return_number=f"RET-{uuid4().hex[:12].upper()}",
            reason=normalized_reason,
            description=normalized_description,
            status="requested",
            requested_refund_amount=total_refund,
            refund_status="pending",
        )

        self.db.add(return_request)
        self.db.flush()

        for item in validated_items:
            return_item = OrderReturnItem(
                return_id=return_request.id,
                order_item_id=item["order_item_id"],
                product_name=item["product_name"],
                product_sku=item["product_sku"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                refund_amount=item["refund_amount"],
            )

            self.db.add(return_item)

        self.db.flush()
        self.db.refresh(return_request)

        return return_request

    # =========================================================
    # RETURN STATUS TRANSITIONS
    # =========================================================

    def _validate_transition(
        self,
        return_request: OrderReturn,
        new_status: str,
    ) -> None:
        """Validate a return status transition."""

        current_status = str(
            return_request.status
        ).lower()

        if new_status not in self.RETURN_STATUSES:
            raise OrderReturnError(
                f"Invalid return status: {new_status}."
            )

        allowed = self.ALLOWED_TRANSITIONS.get(
            current_status,
            set(),
        )

        if new_status not in allowed:
            raise OrderReturnError(
                f"Cannot change return status from "
                f"'{current_status}' to '{new_status}'. "
                f"Allowed transitions: {sorted(allowed)}"
            )

    # =========================================================
    # APPROVE RETURN
    # =========================================================

    def approve_return(
        self,
        return_id: int,
        *,
        reviewed_by: str,
        admin_notes: str | None = None,
    ) -> OrderReturn:
        """Approve a requested return."""

        return_id = self._validate_id(
            return_id,
            "Return ID",
        )

        normalized_reviewer = self._validate_reviewer(
            reviewed_by
        )

        normalized_notes = self._validate_text(
            admin_notes,
            "Admin notes",
            max_length=2000,
        )

        return_request = self.get_return(return_id)

        self._validate_transition(
            return_request,
            "approved",
        )

        return_request.status = "approved"
        return_request.reviewed_by = normalized_reviewer
        return_request.reviewed_at = self._now()
        return_request.admin_notes = normalized_notes
        return_request.refund_status = "pending"

        self.db.add(return_request)
        self.db.flush()
        self.db.refresh(return_request)

        return return_request

    # =========================================================
    # REJECT RETURN
    # =========================================================

    def reject_return(
        self,
        return_id: int,
        *,
        reviewed_by: str,
        rejection_reason: str,
        admin_notes: str | None = None,
    ) -> OrderReturn:
        """Reject a requested return."""

        return_id = self._validate_id(
            return_id,
            "Return ID",
        )

        normalized_reviewer = self._validate_reviewer(
            reviewed_by
        )

        normalized_reason = self._validate_text(
            rejection_reason,
            "Rejection reason",
            required=True,
            max_length=1000,
        )

        if normalized_reason is None:
            raise OrderReturnError(
                "Rejection reason is required."
            )

        normalized_notes = self._validate_text(
            admin_notes,
            "Admin notes",
            max_length=2000,
        )

        return_request = self.get_return(return_id)

        self._validate_transition(
            return_request,
            "rejected",
        )

        return_request.status = "rejected"
        return_request.reviewed_by = normalized_reviewer
        return_request.reviewed_at = self._now()
        return_request.rejection_reason = normalized_reason
        return_request.admin_notes = normalized_notes
        return_request.refund_status = "not_required"

        self.db.add(return_request)
        self.db.flush()
        self.db.refresh(return_request)

        return return_request

    # =========================================================
    # PICKUP AND RECEIPT
    # =========================================================

    def mark_picked_up(
        self,
        return_id: int,
    ) -> OrderReturn:
        """Mark an approved return as picked up."""

        return_request = self.get_return(return_id)

        self._validate_transition(
            return_request,
            "picked_up",
        )

        return_request.status = "picked_up"

        self.db.add(return_request)
        self.db.flush()
        self.db.refresh(return_request)

        return return_request

    def mark_received(
        self,
        return_id: int,
        *,
        admin_notes: str | None = None,
    ) -> OrderReturn:
        """Mark returned items as received by the business."""

        return_id = self._validate_id(
            return_id,
            "Return ID",
        )

        normalized_notes = self._validate_text(
            admin_notes,
            "Admin notes",
            max_length=2000,
        )

        return_request = self.get_return(return_id)

        self._validate_transition(
            return_request,
            "received",
        )

        return_request.status = "received"
        return_request.received_at = self._now()
        return_request.refund_status = "processing"

        if normalized_notes is not None:
            return_request.admin_notes = normalized_notes

        self.db.add(return_request)
        self.db.flush()
        self.db.refresh(return_request)

        return return_request

    # =========================================================
    # REFUND RECORDING
    # =========================================================

    def update_refund_status(
        self,
        return_id: int,
        refund_status: str,
        *,
        refund_reference: str | None = None,
    ) -> OrderReturn:
        """
        Update the recorded refund status.

        This method does not call a payment gateway.
        """

        return_id = self._validate_id(
            return_id,
            "Return ID",
        )

        normalized_refund_status = self._validate_text(
            refund_status,
            "Refund status",
            required=True,
            max_length=50,
        )

        if normalized_refund_status is None:
            raise OrderReturnError(
                "Refund status is required."
            )

        normalized_refund_status = (
            normalized_refund_status.lower()
        )

        if normalized_refund_status not in self.REFUND_STATUSES:
            raise OrderReturnError(
                f"Invalid refund status: {normalized_refund_status}."
            )

        normalized_reference = self._validate_text(
            refund_reference,
            "Refund reference",
            max_length=255,
        )

        return_request = self.get_return(return_id)

        if return_request.status != "received":
            raise OrderReturnError(
                "Refund status can only be updated after "
                "the returned items have been received."
            )

        if normalized_refund_status == "completed":
            self._validate_transition(
                return_request,
                "refunded",
            )

            return_request.status = "refunded"
            return_request.refunded_at = self._now()

        elif normalized_refund_status in {
            "pending",
            "processing",
            "failed",
        }:
            pass

        else:
            raise OrderReturnError(
                "A received return can only have pending, "
                "processing, failed, or completed refund status."
            )

        return_request.refund_status = normalized_refund_status

        if normalized_reference is not None:
            return_request.refund_reference = normalized_reference

        self.db.add(return_request)
        self.db.flush()
        self.db.refresh(return_request)

        return return_request

    # =========================================================
    # CANCEL RETURN
    # =========================================================

    def cancel_return(
        self,
        return_id: int,
        *,
        customer_id: int | None = None,
        admin_notes: str | None = None,
    ) -> OrderReturn:
        """Cancel a return request that has not been approved."""

        return_id = self._validate_id(
            return_id,
            "Return ID",
        )

        normalized_notes = self._validate_text(
            admin_notes,
            "Admin notes",
            max_length=2000,
        )

        return_request = self.get_return(
            return_id,
            customer_id=customer_id,
        )

        self._validate_transition(
            return_request,
            "cancelled",
        )

        return_request.status = "cancelled"
        return_request.refund_status = "not_required"

        if normalized_notes is not None:
            return_request.admin_notes = normalized_notes

        self.db.add(return_request)
        self.db.flush()
        self.db.refresh(return_request)

        return return_request

    # =========================================================
    # RETURN SUMMARY
    # =========================================================

    def get_return_summary(
        self,
        return_id: int,
        *,
        customer_id: int | None = None,
    ) -> dict[str, Any]:
        """Return a structured summary of a return request."""

        return_request = self.get_return(
            return_id,
            customer_id=customer_id,
        )

        return_items = list(return_request.items or [])

        return {
            "return_id": return_request.id,
            "return_number": return_request.return_number,
            "order_id": return_request.order_id,
            "customer_id": return_request.customer_id,
            "reason": return_request.reason,
            "description": return_request.description,
            "status": return_request.status,
            "refund_status": return_request.refund_status,
            "requested_refund_amount": str(
                return_request.requested_refund_amount
            ),
            "refund_reference": return_request.refund_reference,
            "rejection_reason": return_request.rejection_reason,
            "admin_notes": return_request.admin_notes,
            "reviewed_by": return_request.reviewed_by,
            "reviewed_at": (
                return_request.reviewed_at.isoformat()
                if return_request.reviewed_at
                else None
            ),
            "received_at": (
                return_request.received_at.isoformat()
                if return_request.received_at
                else None
            ),
            "refunded_at": (
                return_request.refunded_at.isoformat()
                if return_request.refunded_at
                else None
            ),
            "created_at": (
                return_request.created_at.isoformat()
                if return_request.created_at
                else None
            ),
            "items": [
                {
                    "id": item.id,
                    "order_item_id": item.order_item_id,
                    "product_name": item.product_name,
                    "product_sku": item.product_sku,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                    "refund_amount": str(item.refund_amount),
                }
                for item in return_items
            ],
        }
