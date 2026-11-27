
"""
Refund service for Finmarket Kart Essentials.

Responsibilities:
- Create full and partial payment refunds.
- Validate payment eligibility.
- Prevent refunds exceeding the captured payment amount.
- Integrate with the configured payment gateway.
- Store refund records in the database.
- Synchronize refund status.
- Update payment transaction status.

Supported provider:
- Razorpay

Important:
- This service does not commit or roll back database transactions.
- The calling service or API endpoint owns the transaction.
- A database rollback cannot undo an external Razorpay refund.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.payment import (
    PaymentRefund,
    PaymentTransaction,
)
from backend.payments.gateway import (
    PaymentGateway,
    PaymentGatewayError,
    get_payment_gateway,
)


class RefundServiceError(ValueError):
    """Raised when a refund operation is invalid."""


class RefundService:
    """Manage full and partial payment refunds."""

    REFUNDABLE_PAYMENT_STATUSES = {
        "captured",
        "partially_refunded",
    }

    REFUNDABLE_PAYMENT_METHODS = {
        "razorpay",
    }

    REFUND_STATUSES = {
        "pending",
        "processed",
        "failed",
    }

    def __init__(
        self,
        db: Session,
        gateway: PaymentGateway | None = None,
    ) -> None:
        self.db = db
        self.gateway = (
            gateway
            if gateway is not None
            else get_payment_gateway("razorpay")
        )

    # =====================================================
    # VALIDATION HELPERS
    # =====================================================

    @staticmethod
    def _validate_id(
        value: int,
        field_name: str,
    ) -> int:
        """Validate a positive integer ID."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise RefundServiceError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise RefundServiceError(
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
                raise RefundServiceError(
                    f"{field_name} is required."
                )
            return None

        if not isinstance(value, str):
            raise RefundServiceError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if required and not normalized:
            raise RefundServiceError(
                f"{field_name} cannot be empty."
            )

        if max_length is not None and len(normalized) > max_length:
            raise RefundServiceError(
                f"{field_name} cannot exceed "
                f"{max_length} characters."
            )

        return normalized or None

    @staticmethod
    def _to_decimal(
        value: Any,
        field_name: str,
    ) -> Decimal:
        """Convert a value into a valid two-decimal monetary amount."""

        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise RefundServiceError(
                f"Invalid monetary amount for {field_name}."
            ) from exc

        if not amount.is_finite():
            raise RefundServiceError(
                f"{field_name} must be a finite amount."
            )

        return amount.quantize(Decimal("0.01"))

    @staticmethod
    def _now() -> datetime:
        """Return the current UTC datetime."""

        return datetime.now(timezone.utc)

    # =====================================================
    # PAYMENT RETRIEVAL
    # =====================================================

    def get_payment(
        self,
        payment_transaction_id: int,
    ) -> PaymentTransaction:
        """Retrieve a payment transaction by database ID."""

        payment_transaction_id = self._validate_id(
            payment_transaction_id,
            "Payment transaction ID",
        )

        payment = self.db.get(
            PaymentTransaction,
            payment_transaction_id,
        )

        if payment is None:
            raise RefundServiceError(
                f"Payment transaction "
                f"{payment_transaction_id} was not found."
            )

        return payment

    def _get_payment_for_update(
        self,
        payment_transaction_id: int,
    ) -> PaymentTransaction:
        """
        Retrieve and lock a payment row during refund creation.

        This helps prevent concurrent refund requests from
        exceeding the remaining refundable balance.
        """

        payment_transaction_id = self._validate_id(
            payment_transaction_id,
            "Payment transaction ID",
        )

        statement = (
            select(PaymentTransaction)
            .where(
                PaymentTransaction.id == payment_transaction_id
            )
            .with_for_update()
        )

        payment = self.db.scalar(statement)

        if payment is None:
            raise RefundServiceError(
                f"Payment transaction "
                f"{payment_transaction_id} was not found."
            )

        return payment

    # =====================================================
    # REFUND RETRIEVAL
    # =====================================================

    def get_refund(
        self,
        refund_id: int,
    ) -> PaymentRefund:
        """Retrieve a refund by database ID."""

        refund_id = self._validate_id(
            refund_id,
            "Refund ID",
        )

        refund = self.db.get(
            PaymentRefund,
            refund_id,
        )

        if refund is None:
            raise RefundServiceError(
                f"Refund with ID {refund_id} was not found."
            )

        return refund

    def get_payment_refunds(
        self,
        payment_transaction_id: int,
    ) -> list[PaymentRefund]:
        """Retrieve all refund records for a payment."""

        payment_transaction_id = self._validate_id(
            payment_transaction_id,
            "Payment transaction ID",
        )

        self.get_payment(payment_transaction_id)

        statement = (
            select(PaymentRefund)
            .where(
                PaymentRefund.payment_id
                == payment_transaction_id
            )
            .order_by(PaymentRefund.created_at.desc())
        )

        return list(self.db.scalars(statement).all())

    # =====================================================
    # REFUND TOTAL CALCULATION
    # =====================================================

    def get_refunded_amount(
        self,
        payment_transaction_id: int,
    ) -> Decimal:
        """
        Calculate the amount reserved by pending and processed refunds.

        Failed refunds are excluded because they do not reserve
        refundable balance.
        """

        payment_transaction_id = self._validate_id(
            payment_transaction_id,
            "Payment transaction ID",
        )

        statement = (
            select(
                func.coalesce(
                    func.sum(PaymentRefund.amount),
                    0,
                )
            )
            .where(
                PaymentRefund.payment_id
                == payment_transaction_id,
                PaymentRefund.status.in_(
                    {"pending", "processed"}
                ),
            )
        )

        result = self.db.scalar(statement)

        return self._to_decimal(
            result or Decimal("0.00"),
            "Existing refunded amount",
        )

    def get_remaining_refundable_amount(
        self,
        payment_transaction_id: int,
    ) -> Decimal:
        """Calculate the remaining refundable payment balance."""

        payment = self.get_payment(payment_transaction_id)

        payment_amount = self._to_decimal(
            payment.amount,
            "Payment amount",
        )

        already_refunded = self.get_refunded_amount(
            payment_transaction_id
        )

        remaining = payment_amount - already_refunded

        return max(
            remaining,
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    # =====================================================
    # REFUND ELIGIBILITY
    # =====================================================

    def validate_refund_eligibility(
        self,
        payment: PaymentTransaction,
    ) -> None:
        """Validate whether a payment can be refunded."""

        payment_status = str(payment.status).lower()
        payment_method = str(payment.payment_method).lower()
        provider = str(payment.provider).lower()

        if payment_method not in self.REFUNDABLE_PAYMENT_METHODS:
            raise RefundServiceError(
                f"Refunds are not supported for payment method "
                f"'{payment_method}'."
            )

        if provider != "razorpay":
            raise RefundServiceError(
                f"Refunds are not supported for provider '{provider}'."
            )

        if payment_status not in self.REFUNDABLE_PAYMENT_STATUSES:
            raise RefundServiceError(
                f"Payment cannot be refunded while its status "
                f"is '{payment_status}'. "
                "The payment must be captured or partially refunded."
            )

        if not payment.provider_payment_id:
            raise RefundServiceError(
                "The payment does not have a provider payment ID."
            )

    # =====================================================
    # REFUND AMOUNT VALIDATION
    # =====================================================

    def _resolve_refund_amount(
        self,
        payment: PaymentTransaction,
        amount: Decimal | int | float | str | None,
    ) -> Decimal:
        """Validate and calculate the requested refund amount."""

        remaining = self.get_remaining_refundable_amount(
            payment.id
        )

        if remaining <= 0:
            raise RefundServiceError(
                "No refundable balance remains for this payment."
            )

        if amount is None:
            refund_amount = remaining
        else:
            refund_amount = self._to_decimal(
                amount,
                "Refund amount",
            )

        if refund_amount <= 0:
            raise RefundServiceError(
                "Refund amount must be greater than zero."
            )

        if refund_amount > remaining:
            raise RefundServiceError(
                f"Requested refund {refund_amount} exceeds "
                f"remaining refundable amount {remaining}."
            )

        return refund_amount

    # =====================================================
    # PAYMENT STATUS UPDATE
    # =====================================================

    def _update_payment_status(
        self,
        payment: PaymentTransaction,
    ) -> None:
        """Update payment status based on successfully processed refunds."""

        statement = (
            select(
                func.coalesce(
                    func.sum(PaymentRefund.amount),
                    0,
                )
            )
            .where(
                PaymentRefund.payment_id == payment.id,
                PaymentRefund.status == "processed",
            )
        )

        result = self.db.scalar(statement)

        processed_amount = self._to_decimal(
            result or Decimal("0.00"),
            "Processed refund amount",
        )

        payment_amount = self._to_decimal(
            payment.amount,
            "Payment amount",
        )

        if processed_amount >= payment_amount:
            payment.status = "refunded"
        elif processed_amount > 0:
            payment.status = "partially_refunded"
        else:
            return

        self.db.add(payment)
        self.db.flush()

    # =====================================================
    # CREATE REFUND
    # =====================================================

    def create_refund(
        self,
        payment_transaction_id: int,
        amount: Decimal | int | float | str | None = None,
        reason: str | None = None,
    ) -> PaymentRefund:
        """
        Create a full or partial Razorpay refund.

        If amount is omitted, the remaining refundable balance
        is used.

        A pending local refund record is created before the
        external provider request.
        """

        payment_transaction_id = self._validate_id(
            payment_transaction_id,
            "Payment transaction ID",
        )

        normalized_reason = self._validate_text(
            reason,
            "Refund reason",
            max_length=2000,
        )

        # Lock the payment row while checking and reserving balance.
        payment = self._get_payment_for_update(
            payment_transaction_id
        )

        self.validate_refund_eligibility(payment)

        refund_amount = self._resolve_refund_amount(
            payment,
            amount,
        )

        provider_payment_id = payment.provider_payment_id

        # Explicitly narrow the optional model field to str.
        if not provider_payment_id:
            raise RefundServiceError(
                "The payment does not have a provider payment ID."
            )

        # Create a pending refund record.
        refund = PaymentRefund(
            payment_id=payment.id,
            amount=refund_amount,
            currency=payment.currency,
            reason=normalized_reason,
            status="pending",
        )

        self.db.add(refund)
        self.db.flush()

        notes: dict[str, Any] = {
            "payment_transaction_id": str(payment.id),
            "order_id": str(payment.order_id),
            "refund_record_id": str(refund.id),
        }

        if normalized_reason is not None:
            notes["reason"] = normalized_reason

        try:
            provider_response = self.gateway.create_refund(
                payment_id=provider_payment_id,
                amount=refund_amount,
                notes=notes,
            )

        except PaymentGatewayError:
            # Preserve the refund record and its original reason.
            # The caller should reconcile this failed request
            # before attempting another refund.
            refund.status = "failed"

            self.db.add(refund)
            self.db.flush()
            self.db.refresh(refund)

            return refund

        provider_refund_id = provider_response.get("id")

        if provider_refund_id is not None:
            refund.provider_refund_id = str(
                provider_refund_id
            )

        provider_status = str(
            provider_response.get("status", "pending")
        ).lower()

        # Razorpay can return pending, processed, or failed.
        if provider_status == "processed":
            refund.status = "processed"
            refund.processed_at = self._now()

        elif provider_status == "failed":
            refund.status = "failed"

        else:
            refund.status = "pending"

        self.db.add(refund)
        self.db.flush()

        if refund.status == "processed":
            self._update_payment_status(payment)

        self.db.refresh(refund)

        return refund

    # =====================================================
    # REFUND STATUS SYNCHRONIZATION
    # =====================================================

    def synchronize_refund_status(
        self,
        refund_id: int,
        provider_status: str,
        provider_refund_id: str | None = None,
    ) -> PaymentRefund:
        """
        Synchronize a refund status from a trusted provider response
        or a verified webhook.

        This method does not independently verify webhook signatures.
        """

        refund_id = self._validate_id(
            refund_id,
            "Refund ID",
        )

        normalized_status = self._validate_text(
            provider_status,
            "Provider refund status",
            required=True,
            max_length=30,
        )

        if normalized_status is None:
            raise RefundServiceError(
                "Provider refund status is required."
            )

        normalized_status = normalized_status.lower()

        if normalized_status not in self.REFUND_STATUSES:
            raise RefundServiceError(
                f"Unsupported refund status: {normalized_status}."
            )

        normalized_provider_id = self._validate_text(
            provider_refund_id,
            "Provider refund ID",
            max_length=150,
        )

        refund = self.get_refund(refund_id)

        # Do not silently reverse terminal states.
        if refund.status == "processed":
            if normalized_status != "processed":
                raise RefundServiceError(
                    "A processed refund cannot be moved to another status."
                )

            return refund

        if refund.status == "failed":
            if normalized_status != "failed":
                raise RefundServiceError(
                    "A failed refund cannot be changed through "
                    "this synchronization method."
                )

            return refund

        refund.status = normalized_status

        if normalized_provider_id is not None:
            refund.provider_refund_id = normalized_provider_id

        if normalized_status == "processed":
            refund.processed_at = self._now()

        self.db.add(refund)
        self.db.flush()

        if normalized_status == "processed":
            payment = self.get_payment(refund.payment_id)
            self._update_payment_status(payment)

        self.db.refresh(refund)

        return refund

    # =====================================================
    # REFUND SUMMARY
    # =====================================================

    def get_refund_summary(
        self,
        payment_transaction_id: int,
    ) -> dict[str, Any]:
        """Return a summary of refunds for a payment."""

        payment_transaction_id = self._validate_id(
            payment_transaction_id,
            "Payment transaction ID",
        )

        payment = self.get_payment(
            payment_transaction_id
        )

        refunds = self.get_payment_refunds(
            payment_transaction_id
        )

        total_processed = sum(
            (
                self._to_decimal(
                    refund.amount,
                    "Refund amount",
                )
                for refund in refunds
                if refund.status == "processed"
            ),
            Decimal("0.00"),
        )

        total_pending = sum(
            (
                self._to_decimal(
                    refund.amount,
                    "Refund amount",
                )
                for refund in refunds
                if refund.status == "pending"
            ),
            Decimal("0.00"),
        )

        remaining = self.get_remaining_refundable_amount(
            payment_transaction_id
        )

        return {
            "payment_transaction_id": payment.id,
            "provider_payment_id": payment.provider_payment_id,
            "payment_amount": str(payment.amount),
            "currency": payment.currency,
            "payment_status": payment.status,
            "total_processed_refunds": str(
                total_processed.quantize(Decimal("0.01"))
            ),
            "total_pending_refunds": str(
                total_pending.quantize(Decimal("0.01"))
            ),
            "remaining_refundable_amount": str(remaining),
            "refund_count": len(refunds),
            "refunds": [
                {
                    "refund_id": refund.id,
                    "provider_refund_id": refund.provider_refund_id,
                    "amount": str(refund.amount),
                    "currency": refund.currency,
                    "status": refund.status,
                    "reason": refund.reason,
                    "processed_at": (
                        refund.processed_at.isoformat()
                        if refund.processed_at
                        else None
                    ),
                }
                for refund in refunds
            ],
        }


__all__ = [
    "RefundService",
    "RefundServiceError",
]
