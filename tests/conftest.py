
"""Shared pytest fixtures for Finmarket Kart Essentials."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_db():
    """Provide a mocked SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def sample_product_data():
    """Sample product data for tests."""
    return {
        "id": 1,
        "name": "Fresh Apples",
        "sku": "FV-001",
        "price": "180.00",
        "currency": "INR",
    }


@pytest.fixture
def sample_warehouse_data():
    """Sample warehouse data for tests."""
    return {
        "warehouse_code": "HYD-001",
        "name": "Hyderabad Main Warehouse",
        "address_line1": "Industrial Area",
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode": "500001",
        "country": "India",
    }
