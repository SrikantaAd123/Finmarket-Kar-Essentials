
"""Tests for Razorpay webhook event processing."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.payments.webhook_handler import WebhookHandler


# ============================================================
# TEST HELPERS
# ============================================================

def make_event(
    event_id=1,
    event_type="payment.captured",
    provider="razorpay",
    is_processed=False,
):
    return SimpleNamespace(
        id=event_id,
        event_type=event_type,
        provider=provider,
        is_processed=is_processed,
        payload={},
    )


@pytest.fixture
def handler():
    """Create WebhookHandler without opening a database session."""

    instance = WebhookHandler.__new__(WebhookHandler)

    instance.db = MagicMock()
    instance.payment_repository = MagicMock()
    instance.order_repository = MagicMock()
    instance.refund_service = MagicMock()

    return instance


# ============================================================
# EVENT ID VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "event_id",
    [
        0,
        -1,
        None,
        "1",
        True,
        1.5,
    ],
)
def test_process_event_rejects_invalid_event_id(
    handler,
    event_id,
):
    with pytest.raises(ValueError):
        handler.process_event(event_id)

    handler.db.get.assert_not_called()


# ============================================================
# EVENT RETRIEVAL
# ============================================================

def test_process_event_rejects_missing_event(handler):
    handler.db.get.return_value = None

    with pytest.raises(
        ValueError,
        match="Webhook event was not found",
    ):
        handler.process_event(1)


def test_process_event_uses_event_id_to_retrieve_event(handler):
    event = make_event(is_processed=True)

    handler.db.get.return_value = event

    handler.process_event(1)

    handler.db.get.assert_called_once()


# ============================================================
# DUPLICATE EVENT HANDLING
# ============================================================

def test_process_event_ignores_already_processed_event(handler):
    event = make_event(
        event_id=10,
        is_processed=True,
    )

    handler.db.get.return_value = event

    result = handler.process_event(10)

    assert result == {
        "event_id": 10,
        "processed": True,
        "duplicate": True,
        "message": "Webhook event was already processed.",
    }

    handler.payment_repository.mark_webhook_processed.assert_not_called()
    handler.db.rollback.assert_not_called()


# ============================================================
# PAYMENT EVENT PROCESSING
# ============================================================

@pytest.mark.parametrize(
    "event_type",
    [
        "payment.authorized",
        "payment.captured",
        "payment.failed",
    ],
)
def test_processes_supported_payment_event(
    handler,
    monkeypatch,
    event_type,
):
    event = make_event(event_type=event_type)

    handler.db.get.return_value = event

    process_payment = MagicMock()

    monkeypatch.setattr(
        handler,
        "_process_payment_event",
        process_payment,
    )

    handler.payment_repository.mark_webhook_processed.return_value = (
        event
    )

    result = handler.process_event(1)

    process_payment.assert_called_once_with(event)

    handler.payment_repository.mark_webhook_processed.assert_called_once_with(
        event.id
    )

    assert result["event_id"] == 1
    assert result["event_type"] == event_type
    assert result["processed"] is True
    assert result["duplicate"] is False


# ============================================================
# REFUND EVENT PROCESSING
# ============================================================

@pytest.mark.parametrize(
    "event_type",
    [
        "refund.created",
        "refund.processed",
        "refund.failed",
        "refund.speed_changed",
    ],
)
def test_processes_supported_refund_event(
    handler,
    monkeypatch,
    event_type,
):
    event = make_event(event_type=event_type)

    handler.db.get.return_value = event

    process_refund = MagicMock()

    monkeypatch.setattr(
        handler,
        "_process_refund_event",
        process_refund,
    )

    handler.payment_repository.mark_webhook_processed.return_value = (
        event
    )

    result = handler.process_event(1)

    process_refund.assert_called_once_with(event)

    handler.payment_repository.mark_webhook_processed.assert_called_once_with(
        event.id
    )

    assert result["processed"] is True
    assert result["event_type"] == event_type


# ============================================================
# UNKNOWN EVENT HANDLING
# ============================================================

def test_ignores_unsupported_event(handler):
    event = make_event(
        event_id=20,
        event_type="customer.created",
    )

    handler.db.get.return_value = event

    handler.payment_repository.mark_webhook_processed.return_value = (
        event
    )

    result = handler.process_event(20)

    assert result["event_id"] == 20
    assert result["processed"] is True
    assert result["ignored"] is True

    assert "customer.created" in result["message"]

    handler.payment_repository.mark_webhook_processed.assert_called_once_with(
        20
    )


# ============================================================
# PROVIDER VALIDATION
# ============================================================

def test_rejects_unsupported_provider(handler):
    event = make_event(provider="unknown_provider")

    handler.db.get.return_value = event

    handler.payment_repository.mark_webhook_failed.return_value = (
        event
    )

    result = handler.process_event(1)

    assert result["processed"] is False
    assert "Unsupported webhook provider" in result["error"]

    handler.db.rollback.assert_called_once()

    handler.payment_repository.mark_webhook_failed.assert_called_once()


# ============================================================
# PROCESSING FAILURE
# ============================================================

def test_rolls_back_when_payment_processing_fails(
    handler,
    monkeypatch,
):
    event = make_event(event_type="payment.captured")

    handler.db.get.return_value = event

    monkeypatch.setattr(
        handler,
        "_process_payment_event",
        MagicMock(
            side_effect=ValueError(
                "Payment amount does not match."
            )
        ),
    )

    handler.payment_repository.mark_webhook_failed.return_value = (
        event
    )

    result = handler.process_event(1)

    assert result["processed"] is False

    assert result["error"] == (
        "Payment amount does not match."
    )

    handler.db.rollback.assert_called_once()

    handler.payment_repository.mark_webhook_failed.assert_called_once_with(
        1,
        "Payment amount does not match.",
    )


def test_marks_event_failed_when_processing_raises_runtime_error(
    handler,
    monkeypatch,
):
    event = make_event(event_type="payment.captured")

    handler.db.get.return_value = event

    monkeypatch.setattr(
        handler,
        "_process_payment_event",
        MagicMock(
            side_effect=RuntimeError("Unexpected failure")
        ),
    )

    handler.payment_repository.mark_webhook_failed.return_value = (
        event
    )

    result = handler.process_event(1)

    assert result["processed"] is False
    assert result["error"] == "Unexpected failure"

    handler.db.rollback.assert_called_once()


# ============================================================
# MARKING EVENT AS PROCESSED
# ============================================================

def test_fails_when_event_cannot_be_marked_processed(
    handler,
    monkeypatch,
):
    event = make_event(event_type="payment.captured")

    handler.db.get.return_value = event

    monkeypatch.setattr(
        handler,
        "_process_payment_event",
        MagicMock(),
    )

    handler.payment_repository.mark_webhook_processed.return_value = (
        None
    )

    handler.payment_repository.mark_webhook_failed.return_value = (
        event
    )

    result = handler.process_event(1)

    assert result["processed"] is False

    assert (
        "Webhook event could not be marked as processed."
        in result["error"]
    )

    handler.db.rollback.assert_called_once()


# ============================================================
# PROCESS PENDING EVENTS
# ============================================================

def test_process_pending_events_with_no_events(
    handler,
    monkeypatch,
):
    handler.payment_repository.get_unprocessed_webhook_events.return_value = (
        []
    )

    result = handler.process_pending_events()

    assert result == {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "results": [],
    }


def test_process_pending_events_processes_each_event(
    handler,
    monkeypatch,
):
    events = [
        make_event(event_id=1),
        make_event(event_id=2),
        make_event(event_id=3),
    ]

    handler.payment_repository.get_unprocessed_webhook_events.return_value = (
        events
    )

    process_event = MagicMock(
        side_effect=[
            {"event_id": 1, "processed": True},
            {"event_id": 2, "processed": False},
            {"event_id": 3, "processed": True},
        ]
    )

    monkeypatch.setattr(
        handler,
        "process_event",
        process_event,
    )

    result = handler.process_pending_events(
        page=1,
        page_size=50,
    )

    assert result["total"] == 3
    assert result["successful"] == 2
    assert result["failed"] == 1

    assert len(result["results"]) == 3

    assert process_event.call_count == 3


def test_process_pending_events_passes_pagination(
    handler,
    monkeypatch,
):
    handler.payment_repository.get_unprocessed_webhook_events.return_value = (
        []
    )

    handler.process_pending_events(
        page=2,
        page_size=25,
    )

    handler.payment_repository.get_unprocessed_webhook_events.assert_called_once_with(
        page=2,
        page_size=25,
    )
