
"""Unit tests for admin services."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.admin.dashboard import AdminDashboardService
from backend.admin.analytics import AdminAnalyticsService
from backend.admin.reports import AdminReportService


def test_dashboard_decimal_conversion():
    assert AdminDashboardService._decimal("125.50") == Decimal("125.50")


def test_dashboard_decimal_handles_none():
    assert AdminDashboardService._decimal(None) == Decimal("0")


def test_analytics_decimal_conversion():
    assert AdminAnalyticsService._decimal("500.00") == Decimal("500.00")


def test_analytics_rejects_reversed_date_range():
    with pytest.raises(ValueError):
        AdminAnalyticsService._validate_date_range(
            date(2026, 2, 1),
            date(2026, 1, 1),
        )


def test_analytics_accepts_valid_date_range():
    AdminAnalyticsService._validate_date_range(
        date(2026, 1, 1),
        date(2026, 1, 31),
    )


def test_analytics_rejects_range_over_ten_years():
    with pytest.raises(ValueError):
        AdminAnalyticsService._validate_date_range(
            date(2010, 1, 1),
            date(2026, 1, 1),
        )


def test_reports_reject_reversed_date_range():
    with pytest.raises(ValueError):
        AdminReportService._validate_date_range(
            date(2026, 3, 1),
            date(2026, 2, 1),
        )


def test_reports_accept_valid_date_range():
    AdminReportService._validate_date_range(
        date(2026, 1, 1),
        date(2026, 1, 31),
    )


def test_dashboard_overview():
    db = MagicMock()

    # Values must follow the exact order of db.scalar()
    # calls inside AdminDashboardService.get_overview().
    db.scalar.side_effect = [
        10,                    # total_orders
        20,                    # total_customers
        30,                    # total_products
        40,                    # total_payment_transactions
        Decimal("5000.00"),    # captured_revenue
        5,                     # pending_orders
    ]

    service = AdminDashboardService(db)
    result = service.get_overview()

    assert result["total_orders"] == 10
    assert result["total_customers"] == 20
    assert result["total_products"] == 30
    assert result["total_payment_transactions"] == 40
    assert result["captured_revenue"] == Decimal("5000.00")
    assert result["pending_orders"] == 5
    assert result["currency"] == "INR"

    assert db.scalar.call_count == 6



def test_dashboard_recent_orders_rejects_invalid_limit():
    service = AdminDashboardService(MagicMock())

    with pytest.raises(ValueError):
        service.get_recent_orders(limit=0)

    with pytest.raises(ValueError):
        service.get_recent_orders(limit=101)
