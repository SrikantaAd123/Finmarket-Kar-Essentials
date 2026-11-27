
"""Refund service for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from backend.payments.razorpay_client import (
    RazorpayClient,
    RazorpayOperationError,
)
from backend.repositories.order_repository import OrderRepository
from backend.repositories.payment_repository import PaymentRepository


class RefundService:
    """Business logic for full and partial Razorpay refunds."""

    def __init__(
        self,
        db: Session,
        razorpay_client: RazorpayClient | None = None,
    ) -> None:
        self.db = db
        self.payment_repository = PaymentRepository(db)
        self.order_repository = OrderRepository(db)
        self.razorpay = razorpay_client

    # =====================================================
    # COMMON HELPERS
    # =====================================================

    @staticmethod
    def _validate_id(value: int, name: str) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a positive integer."
            )

    @staticmethod
    def _money(
        value: Decimal | int | float | str,
    ) -> Decimal:
        amount = Decimal(str(value))

        if not amount.is_finite():
            raise ValueError(
                "Amount must be a finite number."
            )

        return amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    def _get_razorpay(self) -> RazorpayClient:
        """Return the configured Razorpay client."""

        if self.razorpay is None:
            self.razorpay = RazorpayClient()

        return self.razorpay

    # =====================================================
    # REFUND REQUEST
    # =====================================================

    def request_refund(
        self,
        payment_id: int,
        amount: Decimal | int | float | str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Request a full or partial Razorpay refund.

        Only captured Razorpay payments can be refunded.

        The refund is first recorded as pending in the database.
        Razorpay is then asked to process the refund.
        """

        self._validate_id(payment_id, "Payment ID")

        refund_amount = self._money(amount)

        if refund_amount <= Decimal("0.00"):
            raise ValueError(
                "Refund amount must be greater than zero."
            )

        if reason is not None:
            if not isinstance(reason, str):
                raise ValueError(
                    "Refund reason must be text."
                )

            reason = reason.strip() or None

        payment = self.payment_repository.get_payment_by_id(
            payment_id
        )

        if payment is None:
            raise ValueError("Payment not found.")

        if payment.payment_method != "razorpay":
            raise ValueError(
                "This refund service currently supports Razorpay payments only."
            )

        if payment.status not in {
            "captured",
            "partially_refunded",
        }:
            raise ValueError(
                "Only captured or partially refunded payments can be refunded."
            )

        if not payment.provider_payment_id:
            raise ValueError(
                "Razorpay payment reference is missing."
            )

        if payment.currency != "INR":
            raise ValueError(
                "Only INR refunds are currently supported."
            )

        # Create a pending refund record.
        # The repository checks the remaining refundable amount.
        refund = self.payment_repository.create_refund(
            payment_id=payment.id,
            amount=refund_amount,
            reason=reason,
            status="pending",
        )

        if refund is None:
            raise RuntimeError(
                "Refund record could not be created."
            )

        refund_id = refund.id

        try:
            gateway = self._get_razorpay()

            gateway_response = gateway.create_refund(
                payment_id=payment.provider_payment_id,
                amount=refund_amount,
                notes={
                    "local_payment_id": str(payment.id),
                    "local_refund_id": str(refund_id),
                    "reason": reason or "Customer refund request",
                },
            )

            provider_refund_id = gateway_response.get("id")

            if not provider_refund_id:
                raise RazorpayOperationError(
                    "Razorpay did not return a refund ID."
                )

            gateway_status = gateway_response.get("status")

            if gateway_status == "processed":
                refund_status = "processed"

            elif gateway_status in {"pending", "created"}:
                refund_status = "pending"

            else:
                raise RazorpayOperationError(
                    f"Unexpected Razorpay refund status: {gateway_status}"
                )

            updated_refund = (
                self.payment_repository.update_refund_status(
                    refund_id=refund_id,
                    status=refund_status,
                    provider_refund_id=str(provider_refund_id),
                )
            )

            if updated_refund is None:
                raise RuntimeError(
                    "Refund record could not be updated."
                )

            if refund_status == "processed":
                self._synchronize_payment_status(payment.id)

            return {
                "success": True,
                "refund": self._refund_response(updated_refund),
                "provider_status": gateway_status,
                "message": (
                    "Refund processed successfully."
                    if refund_status == "processed"
                    else "Refund request submitted and is awaiting processing."
                ),
            }

        except Exception as exc:
            # A failed request must release the pending refund amount.
            self.payment_repository.update_refund_status(
                refund_id=refund_id,
                status="failed",
            )

            raise RuntimeError(
                "Unable to complete the refund request."
            ) from exc

    # =====================================================
    # PAYMENT STATUS SYNCHRONIZATION
    # =====================================================

    def _synchronize_payment_status(
        self,
        payment_id: int,
    ) -> None:
        """Update payment and order status after a processed refund."""

        payment = self.payment_repository.get_payment_by_id(
            payment_id
        )

        if payment is None:
            raise ValueError("Payment not found.")

        processed_refunds = (
            self.payment_repository.get_refund_total(
                payment_id,
                include_pending=False,
            )
        )

        processed_refunds = self._money(processed_refunds)
        payment_amount = self._money(payment.amount)

        if processed_refunds <= Decimal("0.00"):
            return

        if processed_refunds >= payment_amount:
            new_payment_status = "refunded"
            new_order_payment_status = "refunded"

        else:
            new_payment_status = "partially_refunded"
            new_order_payment_status = "partially_refunded"

        updated_payment = (
            self.payment_repository.update_payment_status(
                payment_id,
                new_payment_status,
            )
        )

        if updated_payment is None:
            raise RuntimeError(
                "Payment status could not be synchronized."
            )

        updated_order = self.order_repository.update_payment_status(
            payment.order_id,
            new_order_payment_status,
        )

        if updated_order is None:
            raise RuntimeError(
                "Order payment status could not be synchronized."
            )

    # =====================================================
    # REFUND STATUS UPDATE
    # =====================================================

    def update_refund_status(
        self,
        refund_id: int,
        status: str,
        provider_refund_id: str | None = None,
    ) -> dict[str, Any]:
        """Update a refund after receiving a provider confirmation.

        This method is intended for trusted webhook or
        reconciliation workflows, not unrestricted customer access.
        """

        self._validate_id(refund_id, "Refund ID")

        if status not in {"pending", "processed", "failed"}:
            raise ValueError(
                "Refund status must be pending, processed or failed."
            )

        refund = self.payment_repository.get_refund_by_id(
            refund_id
        )

        if refund is None:
            raise ValueError("Refund not found.")

        # Do not allow a failed refund to become processed through
        # an ordinary status update without reconciliation.
        if refund.status == "failed" and status == "processed":
            raise ValueError(
                "A failed refund requires provider reconciliation."
            )

        updated_refund = (
            self.payment_repository.update_refund_status(
                refund_id=refund_id,
                status=status,
                provider_refund_id=provider_refund_id,
            )
        )

        if updated_refund is None:
            raise RuntimeError(
                "Refund status could not be updated."
            )

        if status == "processed":
            self._synchronize_payment_status(
                updated_refund.payment_id
            )

        return self._refund_response(updated_refund)

    # =====================================================
    # REFUND RETRIEVAL
    # =====================================================

    def get_refund(self, refund_id: int):
        """Retrieve one refund."""

        self._validate_id(refund_id, "Refund ID")

        refund = self.payment_repository.get_refund_by_id(
            refund_id
        )

        if refund is None:
            raise ValueError("Refund not found.")

        return refund

    def get_payment_refunds(
        self,
        payment_id: int,
    ) -> list[Any]:
        """Retrieve all refunds for a payment."""

        self._validate_id(payment_id, "Payment ID")

        payment = self.payment_repository.get_payment_by_id(
            payment_id
        )

        if payment is None:
            raise ValueError("Payment not found.")

        return self.payment_repository.get_payment_refunds(
            payment_id
        )

    def get_refund_total(
        self,
        payment_id: int,
        include_pending: bool = False,
    ) -> Decimal:
        """Get the total processed or reserved refund amount."""

        self._validate_id(payment_id, "Payment ID")

        payment = self.payment_repository.get_payment_by_id(
            payment_id
        )

        if payment is None:
            raise ValueError("Payment not found.")

        total = self.payment_repository.get_refund_total(
            payment_id,
            include_pending=include_pending,
        )

        return self._money(total)

    # =====================================================
    # RESPONSE SERIALIZATION
    # =====================================================

    @staticmethod
    def _refund_response(refund: Any) -> dict[str, Any]:
        """Convert a refund model into a safe response dictionary."""

        return {
            "id": refund.id,
            "payment_id": refund.payment_id,
            "provider_refund_id": refund.provider_refund_id,
            "amount": str(refund.amount),
            "currency": refund.currency,
            "reason": refund.reason,
            "status": refund.status,
            "processed_at": refund.processed_at,
            "created_at": refund.created_at,
        }
