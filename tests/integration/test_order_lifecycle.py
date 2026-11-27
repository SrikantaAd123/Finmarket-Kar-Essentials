
"""Integration tests for administrator order lifecycle API."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.api.v1.admin as admin_module

from backend.auth.dependencies import get_current_admin
from backend.database.connection import get_db


# ============================================================
# TEST DATA
# ============================================================

NOW = datetime.now(timezone.utc)


def make_order(status: str = "pending"):
    """Create an order matching the admin order serializer."""

    customer = SimpleNamespace(
        id=1,
        full_name="Test Customer",
        email="customer@example.com",
        phone_number="9876543210",
    )

    item = SimpleNamespace(
        id=1,
        product_id=10,
        product_name="Fresh Apples",
        product_sku="FV-001",
        quantity=2,
        unit_price=Decimal("100.00"),
        line_total=Decimal("200.00"),
    )

    tracking_event = SimpleNamespace(
        id=1,
        status=status,
        title="Order status updated",
        description="Order lifecycle test",
        location="Hyderabad",
        updated_by="admin@example.com",
        created_at=NOW,
    )

    return SimpleNamespace(
        id=101,
        order_number="FMK-TEST-0001",
        customer_id=1,
        customer=customer,

        status=status,
        payment_status="pending",
        payment_method="cod",
        currency="INR",

        subtotal=Decimal("200.00"),
        tax_amount=Decimal("0.00"),
        delivery_fee=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("200.00"),

        customer_notes=None,
        cancellation_reason=None,

        # Shipping address
        shipping_name="Test Customer",
        shipping_phone="9876543210",
        shipping_address_line1="Test Street",
        shipping_address_line2=None,
        shipping_city="Hyderabad",
        shipping_state="Telangana",
        shipping_postal_code="500001",
        shipping_country="India",

        # Billing address
        billing_name="Test Customer",
        billing_phone="9876543210",
        billing_address_line1="Test Street",
        billing_address_line2=None,
        billing_city="Hyderabad",
        billing_state="Telangana",
        billing_postal_code="500001",
        billing_country="India",

        # Related records required by serializer
        items=[item],
        payments=[],
        tracking_events=[tracking_event],

        created_at=NOW,
        updated_at=NOW,
    )


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_admin():
    return {
        "sub": "admin-user-001",
        "email": "admin@example.com",
        "roles": ["admin"],
    }


@pytest.fixture
def app(mock_db, mock_admin):
    """Create FastAPI app with the actual admin router."""

    application = FastAPI()

    application.include_router(
        admin_module.router,
        prefix="/api/v1",
    )

    application.dependency_overrides[get_db] = (
        lambda: mock_db
    )

    application.dependency_overrides[get_current_admin] = (
        lambda: mock_admin
    )

    yield application

    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_order_service(monkeypatch):
    """Patch OrderService in the admin router module."""

    service = MagicMock()

    monkeypatch.setattr(
        admin_module,
        "OrderService",
        lambda db: service,
    )

    return service


# ============================================================
# SUCCESSFUL STATUS UPDATES
# ============================================================

@pytest.mark.parametrize(
    "new_status",
    [
        "confirmed",
        "processing",
        "packed",
        "shipped",
        "out_for_delivery",
        "delivered",
    ],
)
def test_admin_can_update_order_status(
    client,
    mock_db,
    mock_order_service,
    new_status,
):
    order = make_order(new_status)

    mock_order_service.update_order_status.return_value = order

    mock_db.refresh.side_effect = lambda obj: None

    response = client.patch(
        "/api/v1/admin/orders/101/status",
        json={
            "status": new_status,
            "description": "Order status updated during testing.",
            "location": "Hyderabad",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == (
        "Order status updated successfully."
    )

    assert body["order"]["id"] == 101
    assert body["order"]["status"] == new_status
    assert body["order"]["order_number"] == "FMK-TEST-0001"

    assert body["order"]["payments"] == []
    assert len(body["order"]["items"]) == 1
    assert len(body["order"]["tracking_events"]) == 1

    mock_order_service.update_order_status.assert_called_once_with(
        order_id=101,
        new_status=new_status,
        updated_by="admin@example.com",
        description="Order status updated during testing.",
        location="Hyderabad",
    )

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(order)
    mock_db.rollback.assert_not_called()


# ============================================================
# ADMIN IDENTITY FALLBACK
# ============================================================

def test_status_update_uses_subject_when_email_missing(
    app,
    client,
    mock_db,
    mock_order_service,
):
    """Use the admin subject when email is unavailable."""

    app.dependency_overrides[get_current_admin] = (
        lambda: {
            "sub": "admin-user-002",
        }
    )

    order = make_order("confirmed")

    mock_order_service.update_order_status.return_value = order
    mock_db.refresh.side_effect = lambda obj: None

    response = client.patch(
        "/api/v1/admin/orders/101/status",
        json={
            "status": "confirmed",
        },
    )

    assert response.status_code == 200

    kwargs = (
        mock_order_service.update_order_status.call_args.kwargs
    )

    assert kwargs["updated_by"] == "admin-user-002"

    mock_db.commit.assert_called_once()


def test_status_update_uses_default_admin_identifier(
    app,
    client,
    mock_db,
    mock_order_service,
):
    """Use 'admin' when neither email nor subject is supplied."""

    app.dependency_overrides[get_current_admin] = (
        lambda: {}
    )

    order = make_order("confirmed")

    mock_order_service.update_order_status.return_value = order
    mock_db.refresh.side_effect = lambda obj: None

    response = client.patch(
        "/api/v1/admin/orders/101/status",
        json={
            "status": "confirmed",
        },
    )

    assert response.status_code == 200

    kwargs = (
        mock_order_service.update_order_status.call_args.kwargs
    )

    assert kwargs["updated_by"] == "admin"


# ============================================================
# REQUEST VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": ""},
        {"status": "x" * 41},
        {
            "status": "confirmed",
            "description": "x" * 2001,
        },
        {
            "status": "confirmed",
            "location": "x" * 256,
        },
    ],
)
def test_status_update_rejects_invalid_payload(
    client,
    mock_order_service,
    payload,
):
    response = client.patch(
        "/api/v1/admin/orders/101/status",
        json=payload,
    )

    assert response.status_code == 422

    mock_order_service.update_order_status.assert_not_called()


# ============================================================
# SERVICE VALIDATION ERRORS
# ============================================================

def test_status_update_handles_invalid_status(
    client,
    mock_db,
    mock_order_service,
):
    mock_order_service.update_order_status.side_effect = (
        ValueError("Invalid order status: unknown")
    )

    response = client.patch(
        "/api/v1/admin/orders/101/status",
        json={
            "status": "unknown",
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Invalid order status: unknown"
    )

    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()


def test_status_update_handles_missing_order(
    client,
    mock_db,
    mock_order_service,
):
    mock_order_service.update_order_status.side_effect = (
        ValueError("Order not found.")
    )

    response = client.patch(
        "/api/v1/admin/orders/999/status",
        json={
            "status": "confirmed",
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == "Order not found."

    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()


# ============================================================
# DATABASE FAILURE
# ============================================================

def test_status_update_rolls_back_on_commit_failure(
    client,
    mock_db,
    mock_order_service,
):
    order = make_order("confirmed")

    mock_order_service.update_order_status.return_value = order

    mock_db.commit.side_effect = RuntimeError(
        "Database commit failed."
    )

    response = client.patch(
        "/api/v1/admin/orders/101/status",
        json={
            "status": "confirmed",
        },
    )

    assert response.status_code == 500

    assert response.json()["detail"] == (
        "Unable to update order status."
    )

    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_called_once()


def test_status_update_rolls_back_when_refresh_fails(
    client,
    mock_db,
    mock_order_service,
):
    order = make_order("confirmed")

    mock_order_service.update_order_status.return_value = order

    mock_db.refresh.side_effect = RuntimeError(
        "Refresh failed."
    )

    response = client.patch(
        "/api/v1/admin/orders/101/status",
        json={
            "status": "confirmed",
        },
    )

    assert response.status_code == 500

    assert response.json()["detail"] == (
        "Unable to update order status."
    )

    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_called_once()
