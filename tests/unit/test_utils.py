
"""Unit tests for shared utility functions."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.utils import (
    utc_now,
    ensure_utc,
    is_expired,
    normalize_pagination,
    build_pagination_metadata,
    to_decimal,
    round_money,
    calculate_percentage,
    calculate_total,
    normalize_text,
    generate_slug,
    truncate_text,
)


def test_utc_now_is_timezone_aware():
    result = utc_now()

    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)


def test_ensure_utc_converts_naive_datetime():
    value = datetime(2026, 1, 1, 12, 0)

    result = ensure_utc(value)

    assert result.tzinfo == timezone.utc


def test_ensure_utc_preserves_instant():
    value = datetime(
        2026, 1, 1, 12, 0,
        tzinfo=timezone.utc,
    )

    assert ensure_utc(value) == value


def test_is_expired_returns_true_for_past_datetime():
    past = utc_now() - timedelta(minutes=5)

    assert is_expired(past) is True


def test_is_expired_returns_false_for_future_datetime():
    future = utc_now() + timedelta(minutes=5)

    assert is_expired(future) is False


def test_normalize_pagination():
    result = normalize_pagination(page=2, page_size=20)

    assert result.page == 2
    assert result.page_size == 20
    assert result.offset == 20
    assert result.limit == 20


def test_normalize_pagination_limits_page_size():
    result = normalize_pagination(
        page=1,
        page_size=200,
        max_page_size=100,
    )

    assert result.page_size == 100


@pytest.mark.parametrize(
    "page,page_size",
    [(0, 20), (-1, 20), (1, 0), (1, -5)],
)
def test_normalize_pagination_rejects_invalid_values(
    page,
    page_size,
):
    with pytest.raises(ValueError):
        normalize_pagination(page, page_size)


def test_pagination_metadata():
    pagination = normalize_pagination(2, 20)

    result = build_pagination_metadata(95, pagination)

    assert result["total_items"] == 95
    assert result["total_pages"] == 5
    assert result["has_next"] is True
    assert result["has_previous"] is True


def test_to_decimal():
    assert to_decimal("125.50") == Decimal("125.50")


def test_round_money():
    assert round_money("12.345") == Decimal("12.35")


def test_calculate_percentage():
    assert calculate_percentage("1000", "18") == Decimal("180.00")


def test_calculate_total():
    result = calculate_total("1000", "180", "100")

    assert result == Decimal("1080.00")


def test_calculate_total_rejects_excessive_discount():
    with pytest.raises(ValueError):
        calculate_total("100", "10", "200")


def test_normalize_text():
    assert normalize_text("  Fresh    Apples  ") == "Fresh Apples"


def test_generate_slug():
    assert generate_slug("Fresh Apples") == "fresh-apples"


def test_generate_slug_rejects_empty_text():
    with pytest.raises(ValueError):
        generate_slug(" !!! ")


def test_truncate_text():
    assert truncate_text("Finmarket Kart", 9) == "Finmarket"


def test_truncate_text_rejects_negative_length():
    with pytest.raises(ValueError):
        truncate_text("Test", -1)
