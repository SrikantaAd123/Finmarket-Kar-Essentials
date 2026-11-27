
"""Razorpay gateway client for Finmarket Kart Essentials."""

from __future__ import annotations

import hashlib
import hmac
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class RazorpayConfigurationError(RuntimeError):
    """Raised when Razorpay configuration is missing."""


class RazorpayOperationError(RuntimeError):
    """Raised when a Razorpay operation fails."""


class RazorpayClient:
    """Wrapper around the official Razorpay Python SDK."""

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:

        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = key_secret or os.getenv(
            "RAZORPAY_KEY_SECRET"
        )
        self.webhook_secret = webhook_secret or os.getenv(
            "RAZORPAY_WEBHOOK_SECRET"
        )

        if not self.key_id or not self.key_secret:
            raise RazorpayConfigurationError(
                "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET "
                "must be configured in the .env file."
            )

        try:
            import razorpay
        except ImportError as exc:
            raise RazorpayConfigurationError(
                "Razorpay SDK is missing. Install it using: uv add razorpay"
            ) from exc

        # Razorpay SDK exposes resources dynamically.
        # Any is used because its Client type does not declare
        # the order, payment and utility resource attributes.
        self.client: Any = razorpay.Client(
            auth=(self.key_id, self.key_secret)
        )

    # =====================================================
    # AMOUNT CONVERSION
    # =====================================================

    @staticmethod
    def amount_to_paise(
        amount: Decimal | int | float | str,
    ) -> int:
        """Convert Indian Rupees into integer paise."""

        value = Decimal(str(amount))

        if not value.is_finite() or value <= 0:
            raise ValueError(
                "Payment amount must be a positive finite value."
            )

        rounded = value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        return int(rounded * 100)

    # =====================================================
    # CREATE RAZORPAY ORDER
    # =====================================================

    def create_order(
        self,
        amount: Decimal | int | float | str,
        receipt: str,
        notes: dict[str, Any] | None = None,
        currency: str = "INR",
    ) -> dict[str, Any]:
        """Create an order in Razorpay."""

        if not receipt or not receipt.strip():
            raise ValueError(
                "A receipt reference is required."
            )

        if currency != "INR":
            raise ValueError(
                "This store currently supports INR only."
            )

        payload = {
            "amount": self.amount_to_paise(amount),
            "currency": currency,
            "receipt": receipt.strip(),
            "notes": notes or {},
        }

        try:
            response = self.client.order.create(
                data=payload
            )

            return dict(response)

        except Exception as exc:
            raise RazorpayOperationError(
                "Unable to create the Razorpay order."
            ) from exc

    # =====================================================
    # FETCH RAZORPAY ORDER
    # =====================================================

    def fetch_order(
        self,
        provider_order_id: str,
    ) -> dict[str, Any]:
        """Fetch an existing Razorpay order."""

        if not provider_order_id:
            raise ValueError(
                "Razorpay order ID is required."
            )

        try:
            response = self.client.order.fetch(
                provider_order_id
            )

            return dict(response)

        except Exception as exc:
            raise RazorpayOperationError(
                "Unable to retrieve the Razorpay order."
            ) from exc

    # =====================================================
    # FETCH PAYMENT
    # =====================================================

    def fetch_payment(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        """Fetch payment details from Razorpay."""

        if not payment_id:
            raise ValueError(
                "Razorpay payment ID is required."
            )

        try:
            response = self.client.payment.fetch(
                payment_id
            )

            return dict(response)

        except Exception as exc:
            raise RazorpayOperationError(
                "Unable to retrieve Razorpay payment details."
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
            (
                provider_order_id,
                provider_payment_id,
                signature,
            )
        ):
            return False

        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": provider_order_id,
                    "razorpay_payment_id": provider_payment_id,
                    "razorpay_signature": signature,
                }
            )

            return True

        except Exception:
            return False

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

        if not payment_id:
            raise ValueError(
                "Razorpay payment ID is required."
            )

        payload: dict[str, Any] = {}

        if amount is not None:
            payload["amount"] = self.amount_to_paise(
                amount
            )

        if notes:
            payload["notes"] = notes

        try:
            response = self.client.payment.refund(
                payment_id,
                payload,
            )

            return dict(response)

        except Exception as exc:
            raise RazorpayOperationError(
                "Unable to create the Razorpay refund."
            ) from exc

    # =====================================================
    # VERIFY WEBHOOK SIGNATURE
    # =====================================================

    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
    ) -> bool:
        """Verify a Razorpay webhook using its webhook secret.

        Always supply the original raw HTTP request body.
        Do not parse and re-serialize JSON before verification.
        """

        if not self.webhook_secret:
            raise RazorpayConfigurationError(
                "RAZORPAY_WEBHOOK_SECRET is not configured."
            )

        if not body or not signature:
            return False

        expected_signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            expected_signature,
            signature,
        )
