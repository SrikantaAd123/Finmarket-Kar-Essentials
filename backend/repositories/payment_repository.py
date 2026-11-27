
"""Payment repository for Finmarket Kart Essentials.

Manages payment transactions, refunds and webhook events.

This repository uses flush(), not commit().
Transaction management belongs to the service layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.payment import (
    PaymentTransaction,
    PaymentRefund,
)
from backend.models.payment_webhook import PaymentWebhookEvent


class PaymentRepository:
    """Database operations for payments, refunds and webhooks."""

    PAYMENT_STATUSES = {
        "created",
        "pending",
        "authorized",
        "captured",
        "failed",
        "cancelled",
        "refunded",
        "partially_refunded",
    }

    PAYMENT_METHODS = {
        "razorpay",
        "cod",
    }

    REFUND_STATUSES = {
        "pending",
        "processed",
        "failed",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    # =====================================================
    # VALIDATION HELPERS
    # =====================================================

    def _validate_payment_status(self, status: str) -> None:
        if status not in self.PAYMENT_STATUSES:
            raise ValueError(
                f"Invalid payment status: {status}"
            )

    def _validate_payment_method(self, method: str) -> None:
        if method not in self.PAYMENT_METHODS:
            raise ValueError(
                f"Invalid payment method: {method}"
            )

    def _validate_refund_status(self, status: str) -> None:
        if status not in self.REFUND_STATUSES:
            raise ValueError(
                f"Invalid refund status: {status}"
            )

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

    # =====================================================
    # CREATE PAYMENT
    # =====================================================

    def create_payment(
        self,
        data: dict[str, Any],
    ) -> PaymentTransaction:
        """Create a payment transaction."""

        payment_data = data.copy()

        method = payment_data.get("payment_method")

        if method is None:
            raise ValueError("Payment method is required.")

        self._validate_payment_method(method)

        status = payment_data.get("status", "created")
        self._validate_payment_status(status)

        amount = Decimal(str(payment_data["amount"]))

        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        payment_data["amount"] = amount

        payment = PaymentTransaction(**payment_data)

        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)

        return payment

    # =====================================================
    # PAYMENT RETRIEVAL
    # =====================================================

    def get_payment_by_id(
        self,
        payment_id: int,
    ) -> PaymentTransaction | None:
        """Retrieve a payment by its primary key."""

        return self.db.get(
            PaymentTransaction,
            payment_id,
        )

    def get_payment_by_provider_order_id(
        self,
        provider_order_id: str,
    ) -> PaymentTransaction | None:
        """Retrieve a payment using the provider order ID."""

        statement = select(PaymentTransaction).where(
            PaymentTransaction.provider_order_id
            == provider_order_id
        )

        return self.db.scalars(statement).first()

    def get_payment_by_provider_payment_id(
        self,
        provider_payment_id: str,
    ) -> PaymentTransaction | None:
        """Retrieve a payment using the provider payment ID."""

        statement = select(PaymentTransaction).where(
            PaymentTransaction.provider_payment_id
            == provider_payment_id
        )

        return self.db.scalars(statement).first()

    def get_payment_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> PaymentTransaction | None:
        """Retrieve a payment using its idempotency key."""

        statement = select(PaymentTransaction).where(
            PaymentTransaction.idempotency_key
            == idempotency_key
        )

        return self.db.scalars(statement).first()

    def get_order_payments(
        self,
        order_id: int,
    ) -> list[PaymentTransaction]:
        """Retrieve all payment attempts for an order."""

        statement = (
            select(PaymentTransaction)
            .where(
                PaymentTransaction.order_id == order_id
            )
            .order_by(
                PaymentTransaction.created_at.desc(),
                PaymentTransaction.id.desc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def get_latest_order_payment(
        self,
        order_id: int,
    ) -> PaymentTransaction | None:
        """Retrieve the latest payment attempt for an order."""

        statement = (
            select(PaymentTransaction)
            .where(
                PaymentTransaction.order_id == order_id
            )
            .order_by(
                PaymentTransaction.created_at.desc(),
                PaymentTransaction.id.desc(),
            )
            .limit(1)
        )

        return self.db.scalars(statement).first()

    # =====================================================
    # PAYMENT UPDATES
    # =====================================================

    def update_payment_status(
        self,
        payment_id: int,
        status: str,
        failure_code: str | None = None,
        failure_message: str | None = None,
        provider_payment_id: str | None = None,
    ) -> PaymentTransaction | None:
        """Update payment status and provider information."""

        self._validate_payment_status(status)

        payment = self.get_payment_by_id(payment_id)

        if payment is None:
            return None

        payment.status = status

        if failure_code is not None:
            payment.failure_code = failure_code

        if failure_message is not None:
            payment.failure_message = failure_message

        if provider_payment_id is not None:
            payment.provider_payment_id = provider_payment_id

        now = datetime.now(timezone.utc)

        if status == "authorized" and payment.authorized_at is None:
            payment.authorized_at = now

        if status == "captured" and payment.captured_at is None:
            payment.captured_at = now

        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)

        return payment

    def update_provider_order_id(
        self,
        payment_id: int,
        provider_order_id: str,
    ) -> PaymentTransaction | None:
        """Save the payment provider's order reference."""

        payment = self.get_payment_by_id(payment_id)

        if payment is None:
            return None

        payment.provider_order_id = provider_order_id

        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)

        return payment

    # =====================================================
    # PAYMENT LISTING
    # =====================================================

    def get_all_payments(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        payment_method: str | None = None,
        order_id: int | None = None,
    ) -> tuple[list[PaymentTransaction], int]:
        """Retrieve filtered and paginated payment transactions."""

        self._validate_pagination(page, page_size)

        filters = []

        if status is not None:
            self._validate_payment_status(status)
            filters.append(
                PaymentTransaction.status == status
            )

        if payment_method is not None:
            self._validate_payment_method(payment_method)
            filters.append(
                PaymentTransaction.payment_method
                == payment_method
            )

        if order_id is not None:
            filters.append(
                PaymentTransaction.order_id == order_id
            )

        count_statement = (
            select(func.count(PaymentTransaction.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            select(PaymentTransaction)
            .where(*filters)
            .order_by(
                PaymentTransaction.created_at.desc(),
                PaymentTransaction.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        payments = list(self.db.scalars(statement).all())

        return payments, int(total)

    # =====================================================
    # REFUND CREATION
    # =====================================================

    def create_refund(
        self,
        payment_id: int,
        amount: Decimal,
        reason: str | None = None,
        status: str = "pending",
        provider_refund_id: str | None = None,
    ) -> PaymentRefund:
        """Create a full or partial refund record.

        Pending and processed refunds both count against the
        remaining refundable amount.
        """

        amount = Decimal(str(amount))

        if amount <= 0:
            raise ValueError(
                "Refund amount must be positive."
            )

        self._validate_refund_status(status)

        payment = self.get_payment_by_id(payment_id)

        if payment is None:
            raise ValueError("Payment does not exist.")

        if payment.status not in {
            "captured",
            "partially_refunded",
        }:
            raise ValueError(
                "Only captured or partially refunded "
                "payments can be refunded."
            )

        already_refunded = self.get_refund_total(
            payment_id,
            include_pending=True,
        )

        remaining_amount = payment.amount - already_refunded

        if amount > remaining_amount:
            raise ValueError(
                f"Refund amount exceeds the remaining "
                f"refundable amount: {remaining_amount}."
            )

        refund = PaymentRefund(
            payment_id=payment_id,
            amount=amount,
            currency=payment.currency,
            reason=reason,
            status=status,
            provider_refund_id=provider_refund_id,
            processed_at=(
                datetime.now(timezone.utc)
                if status == "processed"
                else None
            ),
        )

        self.db.add(refund)
        self.db.flush()
        self.db.refresh(refund)

        return refund

    # =====================================================
    # REFUND RETRIEVAL
    # =====================================================

    def get_refund_by_id(
        self,
        refund_id: int,
    ) -> PaymentRefund | None:
        """Retrieve a refund by its primary key."""

        return self.db.get(PaymentRefund, refund_id)

    def get_refund_by_provider_id(
        self,
        provider_refund_id: str,
    ) -> PaymentRefund | None:
        """Retrieve a refund using its provider reference."""

        statement = select(PaymentRefund).where(
            PaymentRefund.provider_refund_id
            == provider_refund_id
        )

        return self.db.scalars(statement).first()

    def get_payment_refunds(
        self,
        payment_id: int,
    ) -> list[PaymentRefund]:
        """Retrieve all refunds associated with a payment."""

        statement = (
            select(PaymentRefund)
            .where(
                PaymentRefund.payment_id == payment_id
            )
            .order_by(
                PaymentRefund.created_at.desc(),
                PaymentRefund.id.desc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def get_refund_total(
        self,
        payment_id: int,
        include_pending: bool = False,
    ) -> Decimal:
        """Calculate the amount already refunded or reserved for refund."""

        statuses = (
            ("processed", "pending")
            if include_pending
            else ("processed",)
        )

        statement = select(
            func.coalesce(
                func.sum(PaymentRefund.amount),
                0,
            )
        ).where(
            PaymentRefund.payment_id == payment_id,
            PaymentRefund.status.in_(statuses),
        )

        result = self.db.scalar(statement)

        return Decimal(str(result or 0))

    # =====================================================
    # REFUND UPDATES
    # =====================================================

    def update_refund_status(
        self,
        refund_id: int,
        status: str,
        provider_refund_id: str | None = None,
    ) -> PaymentRefund | None:
        """Update a refund's processing status."""

        self._validate_refund_status(status)

        refund = self.get_refund_by_id(refund_id)

        if refund is None:
            return None

        refund.status = status

        if provider_refund_id is not None:
            refund.provider_refund_id = provider_refund_id

        if status == "processed":
            refund.processed_at = datetime.now(timezone.utc)

        self.db.add(refund)
        self.db.flush()
        self.db.refresh(refund)

        return refund

    # =====================================================
    # WEBHOOK EVENT STORAGE
    # =====================================================

    def get_webhook_event(
        self,
        provider: str,
        provider_event_id: str,
    ) -> PaymentWebhookEvent | None:
        """Find an event using provider and event ID."""

        statement = select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider == provider,
            PaymentWebhookEvent.provider_event_id
            == provider_event_id,
        )

        return self.db.scalars(statement).first()

    def create_webhook_event(
        self,
        provider: str,
        provider_event_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> tuple[PaymentWebhookEvent, bool]:
        """Store a webhook event only if it does not already exist.

        Returns:
            (event, created)

        The database unique constraint remains the final
        protection against concurrent duplicate insertions.
        """

        existing = self.get_webhook_event(
            provider,
            provider_event_id,
        )

        if existing is not None:
            return existing, False

        event = PaymentWebhookEvent(
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=payload,
            is_processed=False,
        )

        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)

        return event, True

    def get_unprocessed_webhook_events(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> list[PaymentWebhookEvent]:
        """Retrieve webhook events awaiting processing."""

        self._validate_pagination(page, page_size)

        statement = (
            select(PaymentWebhookEvent)
            .where(
                PaymentWebhookEvent.is_processed.is_(False)
            )
            .order_by(
                PaymentWebhookEvent.created_at.asc(),
                PaymentWebhookEvent.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        return list(self.db.scalars(statement).all())

    # =====================================================
    # WEBHOOK PROCESSING
    # =====================================================

    def mark_webhook_processed(
        self,
        event_id: int,
    ) -> PaymentWebhookEvent | None:
        """Mark a webhook event as successfully processed."""

        event = self.db.get(
            PaymentWebhookEvent,
            event_id,
        )

        if event is None:
            return None

        event.is_processed = True
        event.processing_error = None
        event.processed_at = datetime.now(timezone.utc)

        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)

        return event

    def mark_webhook_failed(
        self,
        event_id: int,
        error_message: str,
    ) -> PaymentWebhookEvent | None:
        """Record an error while processing a webhook event."""

        event = self.db.get(
            PaymentWebhookEvent,
            event_id,
        )

        if event is None:
            return None

        event.is_processed = False
        event.processing_error = error_message
        event.processed_at = None

        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)

        return event

    # =====================================================
    # STATISTICS
    # =====================================================

    def count_payments_by_status(
        self,
        status: str,
    ) -> int:
        """Count payment transactions by status."""

        self._validate_payment_status(status)

        statement = select(
            func.count(PaymentTransaction.id)
        ).where(
            PaymentTransaction.status == status
        )

        return int(self.db.scalar(statement) or 0)

    def get_captured_payment_total(self) -> Decimal:
        """Calculate the total amount of captured payments."""

        statement = select(
            func.coalesce(
                func.sum(PaymentTransaction.amount),
                0,
            )
        ).where(
            PaymentTransaction.status == "captured"
        )

        result = self.db.scalar(statement)

        return Decimal(str(result or 0))
