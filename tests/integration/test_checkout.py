
"""Integration tests for customer checkout API."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.api.v1.orders as orders_module

from backend.auth.dependencies import get_current_customer
from backend.database.connection import get_db


# ============================================================
# TEST DATA
# ============================================================

NOW = datetime.now(timezone.utc)


def make_order():
    """Create an order object matching the API response schema."""

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
        status="pending",
        title="Order placed",
        description="Your order has been successfully placed.",
        location=None,
        updated_by="system",
        created_at=NOW,
    )

    return SimpleNamespace(
        id=101,
        order_number="FMK-TEST-0001",
        customer_id=1,
        status="pending",
        payment_status="pending",
        payment_method="cod",
        currency="INR",
        subtotal=Decimal("200.00"),
        tax_amount=Decimal("0.00"),
        delivery_fee=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        total_amount=Decimal("200.00"),
        customer_notes="Please call before delivery.",
        cancellation_reason=None,

        # Shipping address snapshot
        shipping_name="Test Customer",
        shipping_phone="9876543210",
        shipping_address_line1="Test Street",
        shipping_address_line2=None,
        shipping_city="Hyderabad",
        shipping_state="Telangana",
        shipping_postal_code="500001",
        shipping_country="India",

        # Billing address snapshot
        billing_name="Test Customer",
        billing_phone="9876543210",
        billing_address_line1="Test Street",
        billing_address_line2=None,
        billing_city="Hyderabad",
        billing_state="Telangana",
        billing_postal_code="500001",
        billing_country="India",

        items=[item],
        tracking_events=[tracking_event],
        created_at=NOW,
        updated_at=NOW,
    )


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_db():
    """Provide a mocked SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def mock_customer():
    """Provide an authenticated customer."""
    return SimpleNamespace(
        id=1,
        email="customer@example.com",
        is_active=True,
    )


@pytest.fixture
def app(mock_db, mock_customer):
    """Create a FastAPI test application using the real orders router."""

    application = FastAPI()

    application.include_router(
        orders_module.router,
        prefix="/api/v1",
    )

    application.dependency_overrides[get_db] = (
        lambda: mock_db
    )

    application.dependency_overrides[get_current_customer] = (
        lambda: mock_customer
    )

    yield application

    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_order_service(monkeypatch):
    """Mock OrderService at the exact location used by the router."""

    service = MagicMock()

    monkeypatch.setattr(
        orders_module,
        "OrderService",
        lambda db: service,
    )

    return service


@pytest.fixture
def checkout_payload():
    """Valid COD checkout request."""

    return {
        "shipping_address_id": 1,
        "billing_address_id": None,
        "payment_method": "cod",
        "customer_notes": "Please call before delivery.",
    }


# ============================================================
# SUCCESSFUL CHECKOUT
# ============================================================

def test_checkout_success(
    client,
    mock_db,
    mock_order_service,
    checkout_payload,
):
    order = make_order()

    mock_order_service.checkout.return_value = order
    mock_order_service.get_order.return_value = order

    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == 101
    assert body["order_number"] == "FMK-TEST-0001"
    assert body["customer_id"] == 1
    assert body["status"] == "pending"
    assert body["payment_status"] == "pending"
    assert body["payment_method"] == "cod"
    assert body["currency"] == "INR"
    assert body["total_amount"] == "200.00"

    assert body["shipping_address"]["recipient_name"] == (
        "Test Customer"
    )

    assert len(body["items"]) == 1
    assert body["items"][0]["product_name"] == "Fresh Apples"

    assert len(body["tracking_events"]) == 1

    mock_order_service.checkout.assert_called_once()
    mock_order_service.get_order.assert_called_once_with(
        order_id=101,
        customer_id=1,
    )

    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()


def test_checkout_passes_authenticated_customer_id(
    client,
    mock_order_service,
    checkout_payload,
):
    order = make_order()

    mock_order_service.checkout.return_value = order
    mock_order_service.get_order.return_value = order

    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
    )

    assert response.status_code == 201

    kwargs = mock_order_service.checkout.call_args.kwargs

    assert kwargs["customer_id"] == 1
    assert kwargs["checkout_data"].payment_method == "cod"
    assert kwargs["checkout_data"].shipping_address_id == 1


# ============================================================
# REQUEST VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "shipping_address_id": 1,
            "payment_method": "invalid_method",
        },
        {
            "shipping_address_id": 0,
            "payment_method": "cod",
        },
        {
            "shipping_address_id": 1,
            "payment_method": "cod",
            "customer_notes": "x" * 2001,
        },
        {
            "shipping_address_id": 1,
            "billing_address_id": 0,
            "payment_method": "cod",
        },
    ],
)
def test_checkout_rejects_invalid_request(
    client,
    mock_order_service,
    payload,
):
    response = client.post(
        "/api/v1/orders/checkout",
        json=payload,
    )

    assert response.status_code == 422
    mock_order_service.checkout.assert_not_called()


# ============================================================
# CHECKOUT BUSINESS VALIDATION
# ============================================================

def test_checkout_rejects_empty_cart(
    client,
    mock_db,
    mock_order_service,
    checkout_payload,
):
    mock_order_service.checkout.side_effect = ValueError(
        "Your shopping cart is empty."
    )

    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Your shopping cart is empty."
    )

    mock_db.rollback.assert_called_once()


def test_checkout_rejects_unavailable_product(
    client,
    mock_db,
    mock_order_service,
    checkout_payload,
):
    mock_order_service.checkout.side_effect = ValueError(
        "A product in your cart is no longer available."
    )

    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
    )

    assert response.status_code == 400
    assert "no longer available" in response.json()["detail"]

    mock_db.rollback.assert_called_once()


def test_checkout_handles_missing_customer(
    client,
    mock_db,
    mock_order_service,
    checkout_payload,
):
    mock_order_service.checkout.side_effect = ValueError(
        "Customer not found."
    )

    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found."

    mock_db.rollback.assert_called_once()


# ============================================================
# ORDER CREATION FAILURE
# ============================================================

def test_checkout_handles_order_creation_failure(
    client,
    mock_db,
    mock_order_service,
    checkout_payload,
):
    mock_order_service.checkout.return_value = None

    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Order creation failed."

    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called_once()


# ============================================================
# DATABASE TRANSACTION FAILURE
# ============================================================

def test_checkout_rolls_back_when_commit_fails(
    client,
    mock_db,
    mock_order_service,
    checkout_payload,
):
    mock_order_service.checkout.return_value = make_order()

    mock_db.commit.side_effect = RuntimeError(
        "Database commit failed."
    )

    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
    )

    assert response.status_code == 500

    assert response.json()["detail"] == (
        "An unexpected error occurred while processing the order."
    )

    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_called_once()

    mock_order_service.get_order.assert_not_called()


# ============================================================
# ORDER RETRIEVAL FAILURE
# ============================================================

def test_checkout_handles_order_retrieval_failure(
    client,
    mock_db,
    mock_order_service,
    checkout_payload,
):
    mock_order_service.checkout.return_value = make_order()
    mock_order_service.get_order.return_value = None

    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload,
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Created order could not be retrieved."
    )

    # The route commits before retrieving the saved order.
    mock_db.commit.assert_called_once()

    # The error handler still calls rollback.
    mock_db.rollback.assert_called_once()


# ============================================================
# CUSTOMER ORDER HISTORY
# ============================================================

def test_customer_order_history(
    client,
    mock_order_service,
):
    order = make_order()

    mock_order_service.get_customer_orders.return_value = (
        [order],
        1,
    )

    response = client.get("/api/v1/orders")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert len(body["items"]) == 1

    assert body["items"][0]["order_number"] == (
        "FMK-TEST-0001"
    )


def test_customer_order_history_supports_pagination(
    client,
    mock_order_service,
):
    mock_order_service.get_customer_orders.return_value = (
        [],
        0,
    )

    response = client.get(
        "/api/v1/orders?page=2&page_size=20&status=pending"
    )

    assert response.status_code == 200

    kwargs = (
        mock_order_service.get_customer_orders.call_args.kwargs
    )

    assert kwargs["customer_id"] == 1
    assert kwargs["page"] == 2
    assert kwargs["page_size"] == 20
    assert kwargs["status"] == "pending"


def test_customer_order_history_rejects_invalid_pagination(
    client,
    mock_order_service,
):
    response = client.get(
        "/api/v1/orders?page=0&page_size=20"
    )

    assert response.status_code == 422

    mock_order_service.get_customer_orders.assert_not_called()


# ============================================================
# ORDER HISTORY ERROR HANDLING
# ============================================================

def test_customer_order_history_handles_service_error(
    client,
    mock_db,
    mock_order_service,
):
    mock_order_service.get_customer_orders.side_effect = (
        ValueError("Customer not found.")
    )

    response = client.get("/api/v1/orders")

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found."

    mock_db.rollback.assert_called_once()
