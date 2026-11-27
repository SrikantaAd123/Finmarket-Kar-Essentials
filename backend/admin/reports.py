
"""Admin reporting services for Finmarket Kart Essentials."""

from __future__ import annotations

import csv
from datetime import date, datetime, time, timedelta, timezone
from io import StringIO
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.order import Order
from backend.models.payment import PaymentTransaction


class AdminReportService:
    """Generate business reports for administrators."""

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
    def _format_value(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, datetime):
            return value.isoformat()

        return str(value)

    def generate_order_report(
        self,
        start_date: date,
        end_date: date,
    ) -> str:
        """Generate an order report in CSV format."""

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
            select(Order)
            .where(
                Order.created_at >= start_datetime,
                Order.created_at < end_datetime,
            )
            .order_by(Order.created_at, Order.id)
        )

        orders = self.db.scalars(statement).all()

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Order ID",
            "Order Number",
            "Customer ID",
            "Order Status",
            "Payment Status",
            "Payment Method",
            "Currency",
            "Subtotal",
            "Tax Amount",
            "Delivery Fee",
            "Discount Amount",
            "Total Amount",
            "Created At",
        ])

        for order in orders:
            writer.writerow([
                order.id,
                order.order_number,
                order.customer_id,
                order.status,
                order.payment_status,
                order.payment_method,
                order.currency,
                order.subtotal,
                order.tax_amount,
                order.delivery_fee,
                order.discount_amount,
                order.total_amount,
                self._format_value(order.created_at),
            ])

        return output.getvalue()

    def generate_payment_report(
        self,
        start_date: date,
        end_date: date,
    ) -> str:
        """Generate a payment transaction report in CSV format."""

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
            select(PaymentTransaction)
            .where(
                PaymentTransaction.created_at >= start_datetime,
                PaymentTransaction.created_at < end_datetime,
            )
            .order_by(
                PaymentTransaction.created_at,
                PaymentTransaction.id,
            )
        )

        payments = self.db.scalars(statement).all()

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Payment ID",
            "Order ID",
            "Payment Method",
            "Provider",
            "Provider Payment ID",
            "Amount",
            "Currency",
            "Status",
            "Created At",
            "Captured At",
        ])

        for payment in payments:
            writer.writerow([
                payment.id,
                payment.order_id,
                payment.payment_method,
                payment.provider,
                payment.provider_payment_id,
                payment.amount,
                payment.currency,
                payment.status,
                self._format_value(payment.created_at),
                self._format_value(payment.captured_at),
            ])

        return output.getvalue()
