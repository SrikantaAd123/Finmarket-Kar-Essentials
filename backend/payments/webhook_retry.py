
"""Retry service for failed Razorpay webhook events."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.payments.webhook_handler import WebhookHandler
from backend.repositories.payment_repository import PaymentRepository


class WebhookRetryService:
    """Retry unprocessed webhook events with per-event transactions."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.payment_repository = PaymentRepository(db)
        self.webhook_handler = WebhookHandler(db)

    def retry_pending_events(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Retry a page of unprocessed webhook events."""

        events = self.payment_repository.get_unprocessed_webhook_events(
            page=page,
            page_size=page_size,
        )

        # Keep IDs rather than ORM objects across commits.
        event_ids = [event.id for event in events]

        results: list[dict[str, Any]] = []

        for event_id in event_ids:
            try:
                result = self.webhook_handler.process_event(event_id)

                # Commit each event independently.
                self.db.commit()

                results.append(result)

            except Exception as exc:
                self.db.rollback()

                results.append(
                    {
                        "event_id": event_id,
                        "processed": False,
                        "error": str(exc),
                    }
                )

        successful = sum(
            1 for result in results
            if result.get("processed") is True
        )

        failed = len(results) - successful

        return {
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "results": results,
        }
