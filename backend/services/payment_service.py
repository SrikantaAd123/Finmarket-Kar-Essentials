
"""Payment service for Finmarket Kart Essentials."""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from backend.payments.razorpay_client import (
    RazorpayClient,
    RazorpayOperationError,
)
from backend.repositories.order_repository import OrderRepository
from backend.repositories.payment_repository import PaymentRepository


class PaymentService:
    """Business logic for Razorpay and COD payments."""

    def __init__(
        self,
        db: Session,
        razorpay_client: RazorpayClient | None = None,
    ) -> None:
        self.db = db
        self.repository = PaymentRepository(db)
        self.order_repository = OrderRepository(db)
        self.razorpay = razorpay_client

    # =====================================================
    # COMMON HELPERS
    # =====================================================

    @staticmethod
    def _validate_id(
        value: int,
        name: str,
    ) -> None:
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

    def _get_customer_order(
        self,
        order_id: int,
        customer_id: int,
    ):
        """Retrieve an order belonging to the customer."""

        self._validate_id(order_id, "Order ID")
        self._validate_id(customer_id, "Customer ID")

        order = self.order_repository.get_customer_order(
            order_id,
            customer_id,
        )

        if order is None:
            raise ValueError(
                "Order not found or does not belong to this customer."
            )

        return order

    # =====================================================
    # INITIATE PAYMENT
    # =====================================================

    def initiate_payment(
        self,
        order_id: int,
        customer_id: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Initiate Razorpay or COD payment for an order.

        The amount always comes from the database order.
        The browser must never provide the payment amount.
        """

        order = self._get_customer_order(
            order_id,
            customer_id,
        )

        if order.status in {"cancelled", "returned"}:
            raise ValueError(
                "Payment cannot be initiated for this order."
            )

        if order.payment_status in {"paid", "refunded"}:
            raise ValueError(
                "This order has already been paid or refunded."
            )

        if (
            not isinstance(idempotency_key, str)
            or not idempotency_key.strip()
        ):
            raise ValueError(
                "An idempotency key is required."
            )

        idempotency_key = idempotency_key.strip()

        # Check whether this request was already processed.
        existing = (
            self.repository.get_payment_by_idempotency_key(
                idempotency_key
            )
        )

        if existing is not None:
            if existing.order_id != order.id:
                raise ValueError(
                    "This idempotency key belongs to another order."
                )

            response = self._payment_response(existing)

            if existing.provider_order_id:
                response["razorpay_order_id"] = (
                    existing.provider_order_id
                )

            return response

        amount = self._money(order.total_amount)

        if amount <= 0:
            raise ValueError(
                "Order amount must be greater than zero."
            )

        # -------------------------------------------------
        # CASH ON DELIVERY
        # -------------------------------------------------

        if order.payment_method == "cod":
            payment = self.repository.create_payment(
                {
                    "order_id": order.id,
                    "payment_method": "cod",
                    "provider": "cod",
                    "amount": amount,
                    "currency": order.currency,
                    "status": "pending",
                    "idempotency_key": idempotency_key,
                }
            )

            if payment is None:
                raise RuntimeError(
                    "COD payment transaction could not be created."
                )

            return self._payment_response(payment)

        # -------------------------------------------------
        # RAZORPAY
        # -------------------------------------------------

        if order.payment_method != "razorpay":
            raise ValueError(
                "Unsupported payment method."
            )

        payment = self.repository.create_payment(
            {
                "order_id": order.id,
                "payment_method": "razorpay",
                "provider": "razorpay",
                "amount": amount,
                "currency": order.currency,
                "status": "created",
                "idempotency_key": idempotency_key,
            }
        )

        if payment is None:
            raise RuntimeError(
                "Payment transaction could not be created."
            )

        # Keep the ID separately for safe access in try/except.
        payment_id = payment.id

        try:
            gateway = self._get_razorpay()

            gateway_order = gateway.create_order(
                amount=amount,
                receipt=order.order_number,
                notes={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "customer_id": str(customer_id),
                },
                currency=order.currency,
            )

            provider_order_id = gateway_order.get("id")

            if not provider_order_id:
                raise RazorpayOperationError(
                    "Razorpay did not return an order ID."
                )

            updated = self.repository.update_provider_order_id(
                payment_id,
                str(provider_order_id),
            )

            if updated is None:
                raise RuntimeError(
                    "Payment record could not be updated."
                )

            payment = self.repository.update_payment_status(
                payment_id,
                "pending",
            )

            if payment is None:
                raise RuntimeError(
                    "Payment status could not be updated."
                )

            return {
                **self._payment_response(payment),
                "razorpay_order_id": str(provider_order_id),
                "razorpay_key_id": gateway.key_id,
                "amount_paise": gateway_order.get("amount"),
                "currency": gateway_order.get(
                    "currency",
                    order.currency,
                ),
            }

        except Exception as exc:
            self.repository.update_payment_status(
                payment_id,
                "failed",
                failure_message=(
                    "Payment gateway order creation failed."
                ),
            )

            raise RuntimeError(
                "Unable to initiate payment. Please try again."
            ) from exc

    # =====================================================
    # VERIFY RAZORPAY PAYMENT
    # =====================================================

    def verify_payment(
        self,
        order_id: int,
        customer_id: int,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str,
    ) -> dict[str, Any]:
        """Verify Razorpay payment and update database status."""

        order = self._get_customer_order(
            order_id,
            customer_id,
        )

        if order.payment_method != "razorpay":
            raise ValueError(
                "Razorpay verification is not valid for this order."
            )

        if not all(
            (provider_order_id, provider_payment_id, signature)
        ):
            raise ValueError(
                "Razorpay payment verification details are required."
            )

        payment = (
            self.repository.get_payment_by_provider_order_id(
                provider_order_id
            )
        )

        if payment is None or payment.order_id != order.id:
            raise ValueError(
                "Payment transaction not found for this order."
            )

        if payment.status == "captured":
            return self._payment_response(payment)

        gateway = self._get_razorpay()

        signature_valid = gateway.verify_payment_signature(
            provider_order_id,
            provider_payment_id,
            signature,
        )

        if not signature_valid:
            raise ValueError(
                "Razorpay payment signature verification failed."
            )

        # Fetch the actual payment details from Razorpay.
        gateway_payment = gateway.fetch_payment(
            provider_payment_id
        )

        if gateway_payment.get("order_id") != provider_order_id:
            raise ValueError(
                "Gateway payment does not match the Razorpay order."
            )

        expected_paise = gateway.amount_to_paise(
            payment.amount
        )

        if int(gateway_payment.get("amount", -1)) != expected_paise:
            raise ValueError(
                "Gateway payment amount does not match the order."
            )

        if gateway_payment.get("currency") != payment.currency:
            raise ValueError(
                "Gateway payment currency does not match the order."
            )

        gateway_status = gateway_payment.get("status")

        if gateway_status == "captured":
            new_status = "captured"
            order_payment_status = "paid"

        elif gateway_status == "authorized":
            new_status = "authorized"
            order_payment_status = "pending"

        elif gateway_status == "failed":
            new_status = "failed"
            order_payment_status = "failed"

        else:
            raise ValueError(
                "Payment is not completed. "
                f"Gateway status: {gateway_status}"
            )

        updated_payment = self.repository.update_payment_status(
            payment.id,
            new_status,
            failure_code=gateway_payment.get("error_code"),
            failure_message=gateway_payment.get(
                "error_description"
            ),
            provider_payment_id=provider_payment_id,
        )

        if updated_payment is None:
            raise RuntimeError(
                "Payment record could not be updated."
            )

        updated_order = self.order_repository.update_payment_status(
            order.id,
            order_payment_status,
        )

        if updated_order is None:
            raise RuntimeError(
                "Order payment status could not be updated."
            )

        return self._payment_response(updated_payment)

    # =====================================================
    # GET PAYMENT
    # =====================================================

    def get_payment(
        self,
        payment_id: int,
        customer_id: int,
    ):
        """Retrieve a payment belonging to the customer."""

        self._validate_id(payment_id, "Payment ID")
        self._validate_id(customer_id, "Customer ID")

        payment = self.repository.get_payment_by_id(
            payment_id
        )

        if payment is None:
            raise ValueError(
                "Payment not found."
            )

        self._get_customer_order(
            payment.order_id,
            customer_id,
        )

        return payment

    # =====================================================
    # GET ORDER PAYMENTS
    # =====================================================

    def get_order_payments(
        self,
        order_id: int,
        customer_id: int,
    ):
        """Retrieve all payment attempts for a customer's order."""

        self._get_customer_order(
            order_id,
            customer_id,
        )

        return self.repository.get_order_payments(
            order_id
        )

    # =====================================================
    # WEBHOOK EVENT STORAGE
    # =====================================================

    def record_webhook_event(
        self,
        raw_body: bytes,
        signature: str,
        provider_event_id: str,
    ) -> dict[str, Any]:
        """Verify and store a Razorpay webhook event.

        This method stores the event for later processing.
        It does not yet execute payment or refund business logic.
        """

        if (
            not isinstance(provider_event_id, str)
            or not provider_event_id.strip()
        ):
            raise ValueError(
                "Webhook event ID is required."
            )

        gateway = self._get_razorpay()

        if not gateway.verify_webhook_signature(
            raw_body,
            signature,
        ):
            raise ValueError(
                "Invalid Razorpay webhook signature."
            )

        try:
            payload = json.loads(
                raw_body.decode("utf-8")
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError(
                "Invalid webhook JSON payload."
            ) from exc

        if not isinstance(payload, dict):
            raise ValueError(
                "Webhook payload must be a JSON object."
            )

        event_type = payload.get("event")

        if not isinstance(event_type, str) or not event_type:
            raise ValueError(
                "Webhook event type is missing."
            )

        event, created = self.repository.create_webhook_event(
            provider="razorpay",
            provider_event_id=provider_event_id.strip(),
            event_type=event_type,
            payload=payload,
        )

        if event is None:
            raise RuntimeError(
                "Webhook event could not be stored."
            )

        return {
            "event_id": event.id,
            "event_type": event.event_type,
            "created": created,
            "is_processed": event.is_processed,
        }

    # =====================================================
    # RESPONSE SERIALIZATION
    # =====================================================

    @staticmethod
    def _payment_response(
        payment: Any,
    ) -> dict[str, Any]:
        """Return payment information without secret credentials."""

        return {
            "id": payment.id,
            "order_id": payment.order_id,
            "payment_method": payment.payment_method,
            "provider": payment.provider,
            "provider_order_id": payment.provider_order_id,
            "provider_payment_id": payment.provider_payment_id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "failure_code": payment.failure_code,
            "failure_message": payment.failure_message,
            "created_at": payment.created_at,
        }
