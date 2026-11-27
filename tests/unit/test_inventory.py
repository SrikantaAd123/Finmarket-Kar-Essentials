
"""Unit tests for inventory repository validation."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.repositories.inventory_repository import InventoryRepository


@pytest.fixture
def repository():
    return InventoryRepository(MagicMock())


def test_valid_quantity(repository):
    result = repository._validate_quantity(
        Decimal("10.500")
    )

    assert result == Decimal("10.500")


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_invalid_quantity(repository, quantity):
    with pytest.raises(ValueError):
        repository._validate_quantity(quantity)


def test_quantity_with_too_many_decimal_places(repository):
    with pytest.raises(ValueError):
        repository._validate_quantity(
            Decimal("1.1234")
        )


def test_valid_nonnegative_quantity(repository):
    result = repository._validate_nonnegative_quantity(
        Decimal("0")
    )

    assert result == Decimal("0")


def test_negative_nonnegative_quantity_rejected(repository):
    with pytest.raises(ValueError):
        repository._validate_nonnegative_quantity(
            Decimal("-1")
        )


@pytest.mark.parametrize("direction", ["IN", "OUT"])
def test_valid_movement_direction(repository, direction):
    repository._validate_movement_direction(direction)


def test_invalid_movement_direction(repository):
    with pytest.raises(ValueError):
        repository._validate_movement_direction("SIDEWAYS")


@pytest.mark.parametrize(
    "movement_type",
    [
        "purchase",
        "sale",
        "return",
        "adjustment",
        "transfer_in",
        "transfer_out",
        "damage",
        "reservation",
        "release",
    ],
)
def test_valid_movement_type(repository, movement_type):
    repository._validate_movement_type(movement_type)


def test_invalid_movement_type(repository):
    with pytest.raises(ValueError):
        repository._validate_movement_type("unknown")


@pytest.mark.parametrize(
    "status",
    ["active", "confirmed", "released", "expired"],
)
def test_valid_reservation_status(repository, status):
    repository._validate_reservation_status(status)


def test_invalid_reservation_status(repository):
    with pytest.raises(ValueError):
        repository._validate_reservation_status("unknown")


def test_invalid_pagination(repository):
    with pytest.raises(ValueError):
        repository._validate_pagination(0, 20)


def test_page_size_above_limit(repository):
    with pytest.raises(ValueError):
        repository._validate_pagination(1, 101)
