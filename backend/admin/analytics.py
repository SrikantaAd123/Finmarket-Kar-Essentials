
"""Admin analytics services for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.order import Order
from backend.models.payment import PaymentTransaction


class AdminAnalyticsService:
    """Provides business analytics for administrators."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _validate_date_range(
        start_date: date,
        end_date: date,
    ) -> None:
        if start_date > end_date:
            raise ValueError(
                "Start date cannot be after end date."
            )

        if (end_date - start_date).days > 3660:
            raise ValueError(
                "Date range cannot exceed ten years."
            )

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        return Decimal(str(value or 0))

    def get_sales_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Summarize captured payment revenue within a date range."""

        self._validate_date_range(start_date, end_date)

        start_datetime = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )

        end_datetime = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

        statement = (
            select(
                func.count(PaymentTransaction.id),
                func.coalesce(
                    func.sum(PaymentTransaction.amount),
                    0,
                ),
            )
            .where(
                PaymentTransaction.status == "captured",
                PaymentTransaction.captured_at >= start_datetime,
                PaymentTransaction.captured_at < end_datetime,
            )
        )

        total_payments, total_revenue = self.db.execute(
            statement
        ).one()

        return {
            "start_date": start_date,
            "end_date": end_date,
            "captured_payment_count": int(total_payments or 0),
            "total_revenue": self._decimal(total_revenue),
            "currency": "INR",
        }

    def get_daily_sales(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Return captured payment revenue grouped by day."""

        self._validate_date_range(start_date, end_date)

        start_datetime = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )

        end_datetime = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

        sales_date = func.date(
            PaymentTransaction.captured_at
        )

        statement = (
            select(
                sales_date.label("sales_date"),
                func.count(PaymentTransaction.id).label(
                    "payment_count"
                ),
                func.sum(PaymentTransaction.amount).label(
                    "revenue"
                ),
            )
            .where(
                PaymentTransaction.status == "captured",
                PaymentTransaction.captured_at >= start_datetime,
                PaymentTransaction.captured_at < end_datetime,
            )
            .group_by(sales_date)
            .order_by(sales_date)
        )

        rows = self.db.execute(statement).all()

        return [
            {
                "date": sales_date,
                "payment_count": int(payment_count),
                "revenue": self._decimal(revenue),
            }
            for sales_date, payment_count, revenue in rows
        ]

    def get_payment_status_summary(self) -> list[dict[str, Any]]:
        """Return payment transaction counts grouped by status."""

        statement = (
            select(
                PaymentTransaction.status,
                func.count(PaymentTransaction.id).label("total"),
                func.coalesce(
                    func.sum(PaymentTransaction.amount),
                    0,
                ).label("amount"),
            )
            .group_by(PaymentTransaction.status)
            .order_by(PaymentTransaction.status)
        )

        rows = self.db.execute(statement).all()

        return [
            {
                "status": status,
                "total": int(total),
                "amount": self._decimal(amount),
            }
            for status, total, amount in rows
        ]

    def get_order_status_summary(self) -> list[dict[str, Any]]:
        """Return order counts grouped by order status."""

        statement = (
            select(
                Order.status,
                func.count(Order.id).label("total"),
            )
            .group_by(Order.status)
            .order_by(Order.status)
        )

        rows = self.db.execute(statement).all()

        return [
            {
                "status": status,
                "total": int(total),
            }
            for status, total in rows
        ]
