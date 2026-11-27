
"""Razorpay webhook event processor for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from backend.models.payment_webhook import PaymentWebhookEvent
from backend.repositories.order_repository import OrderRepository
from backend.repositories.payment_repository import PaymentRepository
from backend.services.refund_service import RefundService


class WebhookHandler:
    """Process verified Razorpay webhook events.

    Signature verification and event storage happen before this handler.
    This class uses flush(), not commit().
    """

    SUPPORTED_EVENTS = {
        "payment.authorized",
        "payment.captured",
        "payment.failed",
        "refund.created",
        "refund.processed",
        "refund.failed",
        "refund.speed_changed",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.payment_repository = PaymentRepository(db)
        self.order_repository = OrderRepository(db)
        self.refund_service = RefundService(db)

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _amount_to_paise(amount: Decimal) -> int:
        value = Decimal(str(amount)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        return int(value * 100)

    @staticmethod
    def _extract_entity(
        payload: dict[str, Any],
        section_name: str,
    ) -> dict[str, Any]:
        """Extract an entity from a Razorpay webhook section."""

        payload_section = payload.get("payload")

        if not isinstance(payload_section, dict):
            raise ValueError("Webhook payload section is missing.")

        section = payload_section.get(section_name)

        if not isinstance(section, dict):
            raise ValueError(
                f"Webhook {section_name} section is missing."
            )

        entity = section.get("entity")

        if not isinstance(entity, dict):
            raise ValueError(
                f"Webhook {section_name} entity is missing."
            )

        return entity

    # =====================================================
    # PROCESS PAYMENT EVENTS
    # =====================================================

    def _process_payment_event(
        self,
        event: PaymentWebhookEvent,
    ) -> None:
        entity = self._extract_entity(
            event.payload,
            "payment",
        )

        provider_order_id = entity.get("order_id")
        provider_payment_id = entity.get("id")

        if not provider_order_id or not provider_payment_id:
            raise ValueError(
                "Webhook is missing the Razorpay order or payment ID."
            )

        payment = (
            self.payment_repository.get_payment_by_provider_order_id(
                str(provider_order_id)
            )
        )

        if payment is None:
            raise ValueError(
                "No local payment matches the Razorpay order ID."
            )

        if payment.payment_method != "razorpay":
            raise ValueError("Webhook does not match a Razorpay payment.")

        if payment.currency != entity.get("currency"):
            raise ValueError(
                "Webhook currency does not match the local payment."
            )

        webhook_amount = entity.get("amount")

        if webhook_amount is None:
            raise ValueError("Webhook payment amount is missing.")

        if int(webhook_amount) != self._amount_to_paise(payment.amount):
            raise ValueError(
                "Webhook amount does not match the local payment."
            )

        event_type = event.event_type

        if event_type == "payment.captured":
            if payment.status not in {
                "captured",
                "refunded",
                "partially_refunded",
            }:
                updated = self.payment_repository.update_payment_status(
                    payment.id,
                    "captured",
                    provider_payment_id=str(provider_payment_id),
                )

                if updated is None:
                    raise RuntimeError(
                        "Payment could not be marked as captured."
                    )

            order = self.order_repository.get_order_by_id(
                payment.order_id
            )

            if order is None:
                raise ValueError("Associated order was not found.")

            if order.payment_status not in {
                "refunded",
                "partially_refunded",
            }:
                updated_order = (
                    self.order_repository.update_payment_status(
                        payment.order_id,
                        "paid",
                    )
                )

                if updated_order is None:
                    raise RuntimeError(
                        "Order payment status could not be updated."
                    )

        elif event_type == "payment.authorized":
            if payment.status not in {
                "captured",
                "refunded",
                "partially_refunded",
                "failed",
                "cancelled",
            }:
                updated = self.payment_repository.update_payment_status(
                    payment.id,
                    "authorized",
                    provider_payment_id=str(provider_payment_id),
                )

                if updated is None:
                    raise RuntimeError(
                        "Payment authorization could not be recorded."
                    )

        elif event_type == "payment.failed":
            if payment.status not in {
                "captured",
                "refunded",
                "partially_refunded",
            }:
                updated = self.payment_repository.update_payment_status(
                    payment.id,
                    "failed",
                    failure_code=entity.get("error_code"),
                    failure_message=entity.get("error_description"),
                    provider_payment_id=str(provider_payment_id),
                )

                if updated is None:
                    raise RuntimeError(
                        "Payment failure could not be recorded."
                    )

                order = self.order_repository.get_order_by_id(
                    payment.order_id
                )

                if order is None:
                    raise ValueError("Associated order was not found.")

                if order.payment_status == "pending":
                    self.order_repository.update_payment_status(
                        payment.order_id,
                        "failed",
                    )

    # =====================================================
    # PROCESS REFUND EVENTS
    # =====================================================

    def _process_refund_event(
        self,
        event: PaymentWebhookEvent,
    ) -> None:
        refund_entity = self._extract_entity(
            event.payload,
            "refund",
        )

        provider_refund_id = refund_entity.get("id")
        provider_payment_id = refund_entity.get("payment_id")

        if not provider_refund_id or not provider_payment_id:
            raise ValueError(
                "Refund webhook is missing its refund or payment ID."
            )

        refund = (
            self.payment_repository.get_refund_by_provider_id(
                str(provider_refund_id)
            )
        )

        # Fallback: our refund request stores its local ID in Razorpay notes.
        if refund is None:
            notes = refund_entity.get("notes")

            if isinstance(notes, dict):
                local_refund_id = notes.get("local_refund_id")

                if local_refund_id is not None:
                    try:
                        refund = (
                            self.payment_repository.get_refund_by_id(
                                int(local_refund_id)
                            )
                        )
                    except (TypeError, ValueError):
                        refund = None

        if refund is None:
            raise ValueError(
                "No local refund matches the Razorpay refund ID."
            )

        payment = self.payment_repository.get_payment_by_id(
            refund.payment_id
        )

        if payment is None:
            raise ValueError("Associated payment was not found.")

        if payment.provider_payment_id != str(provider_payment_id):
            raise ValueError(
                "Refund webhook payment ID does not match the local payment."
            )

        if refund.currency != refund_entity.get("currency"):
            raise ValueError(
                "Refund currency does not match the local refund."
            )

        webhook_amount = refund_entity.get("amount")

        if webhook_amount is None:
            raise ValueError("Refund amount is missing.")

        if int(webhook_amount) != self._amount_to_paise(refund.amount):
            raise ValueError(
                "Refund amount does not match the local refund."
            )

        event_type = event.event_type

        if event_type == "refund.created":
            new_status = "pending"

        elif event_type == "refund.processed":
            new_status = "processed"

        elif event_type == "refund.failed":
            new_status = "failed"

        elif event_type == "refund.speed_changed":
            # A speed change is not itself a completed refund.
            # Preserve the current local status.
            new_status = refund.status

        else:
            raise ValueError("Unsupported refund event.")

        self.refund_service.update_refund_status(
            refund_id=refund.id,
            status=new_status,
            provider_refund_id=str(provider_refund_id),
        )

    # =====================================================
    # PROCESS ONE EVENT
    # =====================================================

    def process_event(
        self,
        event_id: int,
    ) -> dict[str, Any]:
        """Process one previously verified webhook event."""

        if (
            isinstance(event_id, bool)
            or not isinstance(event_id, int)
            or event_id <= 0
        ):
            raise ValueError(
                "Webhook event ID must be a positive integer."
            )

        event = self.db.get(PaymentWebhookEvent, event_id)

        if event is None:
            raise ValueError("Webhook event was not found.")

        if event.is_processed:
            return {
                "event_id": event.id,
                "processed": True,
                "duplicate": True,
                "message": "Webhook event was already processed.",
            }

        
        event_type = event.event_type

        try:
            if event.provider != "razorpay":
                raise ValueError(
                    f"Unsupported webhook provider: {event.provider}"
                )

            if event.event_type in {
                "payment.authorized",
                "payment.captured",
                "payment.failed",
            }:
                self._process_payment_event(event)

            elif event.event_type in {
                "refund.created",
                "refund.processed",
                "refund.failed",
                "refund.speed_changed",
            }:
                self._process_refund_event(event)

            else:
                # Unknown events are safely acknowledged and recorded.
                self.payment_repository.mark_webhook_processed(
                    event.id
                )

                return {
                    "event_id": event.id,
                    "processed": True,
                    "ignored": True,
                    "message": (
                        f"Unsupported event ignored: {event.event_type}"
                    ),
                }

            processed_event = (
                self.payment_repository.mark_webhook_processed(
                    event.id
                )
            )

            if processed_event is None:
                raise RuntimeError(
                    "Webhook event could not be marked as processed."
                )

            return {
                "event_id": event.id,
                "event_type": event.event_type,
                "processed": True,
                "duplicate": False,
                "message": "Webhook event processed successfully.",
            }

       
        except Exception as exc:
            # Roll back all partial business updates first.
            self.db.rollback()

            # Reload the previously committed webhook event.
            self.payment_repository.mark_webhook_failed(
                event_id,
                str(exc),
            )

            return {
                "event_id": event_id,
                "event_type": event.event_type,
                "processed": False,
                "error": str(exc),
            }

    # =====================================================
    # PROCESS PENDING EVENTS
    # =====================================================

    def process_pending_events(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Process a page of unprocessed webhook events."""

        events = (
            self.payment_repository.get_unprocessed_webhook_events(
                page=page,
                page_size=page_size,
            )
        )

        results = [
            self.process_event(event.id)
            for event in events
        ]

        successful = sum(
            1
            for result in results
            if result.get("processed") is True
        )

        return {
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results,
        }
