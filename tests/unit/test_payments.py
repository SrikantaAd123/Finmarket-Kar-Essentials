
"""Unit tests for payment and refund validation."""

from decimal import Decimal

import pytest

from backend.utils.money import round_money, to_decimal


# ============================================================
# MONEY NORMALIZATION
# ============================================================

def test_round_money_rounds_correctly():
    assert round_money("100.456") == Decimal("100.46")


def test_round_money_accepts_integer():
    assert round_money(100) == Decimal("100.00")


def test_round_money_accepts_decimal():
    assert round_money(
        Decimal("250.75")
    ) == Decimal("250.75")


def test_round_money_accepts_string():
    assert round_money("125.50") == Decimal("125.50")


def test_round_money_rejects_nan():
    with pytest.raises(ValueError):
        round_money("NaN")


def test_round_money_rejects_infinity():
    with pytest.raises(ValueError):
        round_money("Infinity")


def test_round_money_rejects_invalid_text():
    with pytest.raises(ValueError):
        round_money("invalid")


def test_to_decimal_converts_string():
    assert to_decimal("500.25") == Decimal("500.25")


def test_to_decimal_rejects_invalid_value():
    with pytest.raises(ValueError):
        to_decimal("not-a-number")


def test_to_decimal_rejects_nan():
    with pytest.raises(ValueError):
        to_decimal("NaN")


def test_to_decimal_rejects_infinity():
    with pytest.raises(ValueError):
        to_decimal("Infinity")


def test_round_money_handles_negative_amount():
    assert round_money("-10.00") == Decimal("-10.00")
