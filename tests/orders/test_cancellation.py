
"""Unit tests for customer order cancellation."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.services.order_service import OrderService


# ============================================================
# TEST HELPERS
# ============================================================

def make_customer(
    customer_id: int = 1,
    is_active: bool = True,
):
    return SimpleNamespace(
        id=customer_id,
        is_active=is_active,
    )


def make_order(
    order_id: int = 101,
    customer_id: int = 1,
    status: str = "pending",
):
    return SimpleNamespace(
        id=order_id,
        customer_id=customer_id,
        status=status,
        cancellation_reason=None,
    )


@pytest.fixture
def service():
    """Create OrderService with mocked repositories."""

    instance = OrderService.__new__(OrderService)

    instance.db = MagicMock()
    instance.repository = MagicMock()
    instance.cart_repository = MagicMock()
    instance.customer_repository = MagicMock()

    instance.customer_repository.get_customer_by_id.return_value = (
        make_customer()
    )

    instance.repository.get_customer_order.return_value = (
        make_order()
    )

    cancelled_order = make_order(status="cancelled")

    instance.repository.cancel_order.return_value = cancelled_order
    instance.repository.get_order_by_id.return_value = cancelled_order

    return instance


# ============================================================
# SUCCESSFUL CANCELLATION
# ============================================================

def test_cancel_pending_order_successfully(service):
    """A pending order can be cancelled."""

    result = service.cancel_order(
        order_id=101,
        customer_id=1,
        reason="Customer changed their mind",
    )

    assert result is not None
    assert result.status == "cancelled"

    service.repository.cancel_order.assert_called_once_with(
        order_id=101,
        reason="Customer changed their mind",
        allowed_statuses=service.CANCELLABLE_STATUSES,
    )

    service.repository.add_tracking_event.assert_called_once_with(
        order_id=101,
        status="cancelled",
        title="Order cancelled",
        description="Customer changed their mind",
        updated_by="customer:1",
    )

    service.repository.get_order_by_id.assert_called_once_with(101)


def test_cancel_confirmed_order_successfully(service):
    """A confirmed order can also be cancelled."""

    service.repository.get_customer_order.return_value = (
        make_order(status="confirmed")
    )

    service.cancel_order(
        order_id=101,
        customer_id=1,
        reason="Incorrect delivery address",
    )

    service.repository.cancel_order.assert_called_once()


def test_cancellation_reason_is_trimmed(service):
    """Whitespace around a valid reason is removed."""

    service.cancel_order(
        order_id=101,
        customer_id=1,
        reason="  Changed my mind  ",
    )

    kwargs = service.repository.cancel_order.call_args.kwargs

    assert kwargs["reason"] == "Changed my mind"

    tracking_kwargs = (
        service.repository.add_tracking_event.call_args.kwargs
    )

    assert tracking_kwargs["description"] == "Changed my mind"


# ============================================================
# INVALID ORDER IDS
# ============================================================

@pytest.mark.parametrize(
    "order_id",
    [
        0,
        -1,
        None,
        "101",
        True,
    ],
)
def test_cancel_rejects_invalid_order_id(service, order_id):
    with pytest.raises(ValueError):
        service.cancel_order(
            order_id=order_id,
            customer_id=1,
            reason="Cancellation requested",
        )

    service.repository.get_customer_order.assert_not_called()
    service.repository.cancel_order.assert_not_called()


# ============================================================
# INVALID CUSTOMER IDS
# ============================================================

@pytest.mark.parametrize(
    "customer_id",
    [
        0,
        -1,
        None,
        "1",
        True,
    ],
)
def test_cancel_rejects_invalid_customer_id(
    service,
    customer_id,
):
    with pytest.raises(ValueError):
        service.cancel_order(
            order_id=101,
            customer_id=customer_id,
            reason="Cancellation requested",
        )

    service.repository.cancel_order.assert_not_called()


# ============================================================
# CUSTOMER VALIDATION
# ============================================================

def test_cancel_rejects_missing_customer(service):
    service.customer_repository.get_customer_by_id.return_value = None

    with pytest.raises(
        ValueError,
        match="Customer not found",
    ):
        service.cancel_order(
            order_id=101,
            customer_id=1,
            reason="Cancellation requested",
        )

    service.repository.cancel_order.assert_not_called()


def test_cancel_rejects_inactive_customer(service):
    service.customer_repository.get_customer_by_id.return_value = (
        make_customer(is_active=False)
    )

    with pytest.raises(
        ValueError,
        match="Customer account is inactive",
    ):
        service.cancel_order(
            order_id=101,
            customer_id=1,
            reason="Cancellation requested",
        )

    service.repository.cancel_order.assert_not_called()


# ============================================================
# ORDER OWNERSHIP AND EXISTENCE
# ============================================================

def test_cancel_rejects_order_not_owned_by_customer(service):
    """The repository returns no customer-owned order."""

    service.repository.get_customer_order.return_value = None

    with pytest.raises(
        ValueError,
        match="Order not found",
    ):
        service.cancel_order(
            order_id=101,
            customer_id=1,
            reason="Cancellation requested",
        )

    service.repository.cancel_order.assert_not_called()


def test_cancel_uses_authenticated_customer_id(service):
    service.cancel_order(
        order_id=101,
        customer_id=25,
        reason="Cancellation requested",
    )

    service.repository.get_customer_order.assert_called_once_with(
        101,
        25,
    )

    kwargs = service.repository.add_tracking_event.call_args.kwargs

    assert kwargs["updated_by"] == "customer:25"


# ============================================================
# CANCELLATION REASON VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "reason",
    [
        "",
        " ",
        "     ",
        None,
        123,
    ],
)
def test_cancel_rejects_empty_or_invalid_reason(
    service,
    reason,
):
    with pytest.raises(
        ValueError,
        match="A cancellation reason is required",
    ):
        service.cancel_order(
            order_id=101,
            customer_id=1,
            reason=reason,
        )

    service.repository.cancel_order.assert_not_called()
    service.repository.add_tracking_event.assert_not_called()


# ============================================================
# ORDER STATUS VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "status",
    [
        "processing",
        "packed",
        "shipped",
        "out_for_delivery",
        "delivered",
        "cancelled",
        "returned",
    ],
)
def test_cancel_rejects_non_cancellable_order_status(
    service,
    status,
):
    service.repository.get_customer_order.return_value = (
        make_order(status=status)
    )

    with pytest.raises(
        ValueError,
        match="Order cannot be cancelled",
    ):
        service.cancel_order(
            order_id=101,
            customer_id=1,
            reason="Cancellation requested",
        )

    service.repository.cancel_order.assert_not_called()
    service.repository.add_tracking_event.assert_not_called()


# ============================================================
# REPOSITORY FAILURE HANDLING
# ============================================================

def test_cancel_rejects_when_repository_returns_none(service):
    service.repository.cancel_order.return_value = None

    with pytest.raises(
        ValueError,
        match="Order could not be cancelled",
    ):
        service.cancel_order(
            order_id=101,
            customer_id=1,
            reason="Cancellation requested",
        )

    service.repository.add_tracking_event.assert_not_called()
    service.repository.get_order_by_id.assert_not_called()


def test_cancel_does_not_create_tracking_if_repository_fails(
    service,
):
    service.repository.cancel_order.side_effect = RuntimeError(
        "Database operation failed"
    )

    with pytest.raises(
        RuntimeError,
        match="Database operation failed",
    ):
        service.cancel_order(
            order_id=101,
            customer_id=1,
            reason="Cancellation requested",
        )

    service.repository.add_tracking_event.assert_not_called()


def test_cancel_returns_repository_order(service):
    expected_order = make_order(status="cancelled")

    service.repository.get_order_by_id.return_value = expected_order

    result = service.cancel_order(
        order_id=101,
        customer_id=1,
        reason="Changed my mind",
    )

    assert result is expected_order
