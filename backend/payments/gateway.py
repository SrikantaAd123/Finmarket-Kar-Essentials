
"""
Payment gateway abstraction for Finmarket Kart Essentials.

Responsibilities:
- Define a common payment gateway interface.
- Provide a Razorpay implementation.
- Create and retrieve provider orders.
- Retrieve payment details.
- Verify payment signatures.
- Create full and partial refunds.
- Verify webhook signatures.

Database operations are handled separately by payment services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from backend.payments.razorpay_client import (
    RazorpayClient,
    RazorpayConfigurationError,
    RazorpayOperationError,
)


class PaymentGatewayError(RuntimeError):
    """Base exception for payment gateway operations."""


class PaymentGatewayConfigurationError(PaymentGatewayError):
    """Raised when payment gateway configuration is invalid."""


class PaymentGateway:
    """
    Common interface for payment gateway integrations.

    Application services should depend on this interface rather
    than directly depending on a payment provider SDK.
    """

    @abstractmethod
    def create_order(
        self,
        amount: Decimal | int | float | str,
        receipt: str,
        notes: dict[str, Any] | None = None,
        currency: str = "INR",
    ) -> dict[str, Any]:
        """Create a payment order."""

    @abstractmethod
    def fetch_order(
        self,
        provider_order_id: str,
    ) -> dict[str, Any]:
        """Fetch a payment order."""

    @abstractmethod
    def fetch_payment(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        """Fetch payment details."""

    @abstractmethod
    def verify_payment_signature(
        self,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str,
    ) -> bool:
        """Verify a payment signature."""

    @abstractmethod
    def create_refund(
        self,
        payment_id: str,
        amount: Decimal | int | float | str | None = None,
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a full or partial refund."""

    @abstractmethod
    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
    ) -> bool:
        """Verify a webhook signature."""


class RazorpayGateway(PaymentGateway):
    """Razorpay implementation of the payment gateway interface."""

    def __init__(
        self,
        client: RazorpayClient | None = None,
    ) -> None:
        """
        Initialize the Razorpay gateway.

        An existing RazorpayClient can be injected for testing
        or dependency management. Otherwise, a new client is created.
        """

        try:
            self.client = client or RazorpayClient()

        except RazorpayConfigurationError as exc:
            raise PaymentGatewayConfigurationError(
                "Unable to initialize Razorpay gateway. "
                "Check your Razorpay environment configuration."
            ) from exc

    # =====================================================
    # CREATE ORDER
    # =====================================================

    def create_order(
        self,
        amount: Decimal | int | float | str,
        receipt: str,
        notes: dict[str, Any] | None = None,
        currency: str = "INR",
    ) -> dict[str, Any]:
        """Create a Razorpay order."""

        try:
            response = self.client.create_order(
                amount=amount,
                receipt=receipt,
                notes=notes,
                currency=currency,
            )

            return dict(response)

        except (ValueError, RazorpayOperationError) as exc:
            raise PaymentGatewayError(
                f"Razorpay order creation failed: {exc}"
            ) from exc

    # =====================================================
    # FETCH ORDER
    # =====================================================

    def fetch_order(
        self,
        provider_order_id: str,
    ) -> dict[str, Any]:
        """Retrieve a Razorpay order."""

        if not isinstance(provider_order_id, str):
            raise PaymentGatewayError(
                "Provider order ID must be a string."
            )

        provider_order_id = provider_order_id.strip()

        if not provider_order_id:
            raise PaymentGatewayError(
                "Provider order ID is required."
            )

        try:
            return dict(
                self.client.fetch_order(provider_order_id)
            )

        except (ValueError, RazorpayOperationError) as exc:
            raise PaymentGatewayError(
                f"Razorpay order retrieval failed: {exc}"
            ) from exc

    # =====================================================
    # FETCH PAYMENT
    # =====================================================

    def fetch_payment(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        """Retrieve Razorpay payment details."""

        if not isinstance(payment_id, str):
            raise PaymentGatewayError(
                "Payment ID must be a string."
            )

        payment_id = payment_id.strip()

        if not payment_id:
            raise PaymentGatewayError(
                "Payment ID is required."
            )

        try:
            return dict(
                self.client.fetch_payment(payment_id)
            )

        except (ValueError, RazorpayOperationError) as exc:
            raise PaymentGatewayError(
                f"Razorpay payment retrieval failed: {exc}"
            ) from exc

    # =====================================================
    # VERIFY PAYMENT SIGNATURE
    # =====================================================

    def verify_payment_signature(
        self,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str,
    ) -> bool:
        """Verify Razorpay Checkout payment signature."""

        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                provider_order_id,
                provider_payment_id,
                signature,
            )
        ):
            return False

        try:
            return self.client.verify_payment_signature(
                provider_order_id=provider_order_id.strip(),
                provider_payment_id=provider_payment_id.strip(),
                signature=signature.strip(),
            )

        except Exception as exc:
            raise PaymentGatewayError(
                "Unable to verify Razorpay payment signature."
            ) from exc

    # =====================================================
    # CREATE REFUND
    # =====================================================

    def create_refund(
        self,
        payment_id: str,
        amount: Decimal | int | float | str | None = None,
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a full or partial Razorpay refund."""

        if not isinstance(payment_id, str):
            raise PaymentGatewayError(
                "Payment ID must be a string."
            )

        payment_id = payment_id.strip()

        if not payment_id:
            raise PaymentGatewayError(
                "Payment ID is required."
            )

        try:
            return dict(
                self.client.create_refund(
                    payment_id=payment_id,
                    amount=amount,
                    notes=notes,
                )
            )

        except (ValueError, RazorpayOperationError) as exc:
            raise PaymentGatewayError(
                f"Razorpay refund creation failed: {exc}"
            ) from exc

    # =====================================================
    # VERIFY WEBHOOK SIGNATURE
    # =====================================================

    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
    ) -> bool:
        """
        Verify a Razorpay webhook signature.

        Pass the original raw request body. Never parse and
        re-serialize the JSON before signature verification.
        """

        if not isinstance(body, bytes):
            raise PaymentGatewayError(
                "Webhook body must contain raw bytes."
            )

        if not isinstance(signature, str) or not signature.strip():
            return False

        try:
            return self.client.verify_webhook_signature(
                body=body,
                signature=signature.strip(),
            )

        except RazorpayConfigurationError as exc:
            raise PaymentGatewayConfigurationError(
                "Razorpay webhook secret is not configured."
            ) from exc


# =========================================================
# GATEWAY FACTORY
# =========================================================

def get_payment_gateway(
    provider: str = "razorpay",
    *,
    razorpay_client: RazorpayClient | None = None,
) -> PaymentGateway:
    """
    Return the configured payment gateway.

    Args:
        provider: Payment provider name.
        razorpay_client: Optional existing Razorpay client.

    Returns:
        A payment gateway implementation.

    Raises:
        PaymentGatewayConfigurationError:
            If the provider is unsupported or cannot be initialized.
    """

    normalized_provider = provider.strip().lower()

    if normalized_provider == "razorpay":
        return RazorpayGateway(client=razorpay_client)

    raise PaymentGatewayConfigurationError(
        f"Unsupported payment gateway: {provider}. "
        "Currently supported provider: razorpay."
    )


__all__ = [
    "PaymentGateway",
    "RazorpayGateway",
    "PaymentGatewayError",
    "PaymentGatewayConfigurationError",
    "get_payment_gateway",
]
