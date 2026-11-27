
"""Admin dashboard services for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.customer import Customer
from backend.models.catalog import Product
from backend.models.order import Order
from backend.models.payment import PaymentTransaction


class AdminDashboardService:
    """Provides summary statistics for the admin dashboard."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        """Convert database numeric values into Decimal."""
        return Decimal(str(value or 0))

    def get_overview(self) -> dict[str, Any]:
        """Return the main dashboard statistics."""

        total_orders = self.db.scalar(
            select(func.count(Order.id))
        ) or 0

        total_customers = self.db.scalar(
            select(func.count(Customer.id))
        ) or 0

        total_products = self.db.scalar(
            select(func.count(Product.id))
        ) or 0

        total_payments = self.db.scalar(
            select(func.count(PaymentTransaction.id))
        ) or 0

        captured_revenue = self.db.scalar(
            select(func.coalesce(func.sum(PaymentTransaction.amount), 0))
            .where(PaymentTransaction.status == "captured")
        )

        pending_orders = self.db.scalar(
            select(func.count(Order.id)).where(
                Order.status == "pending"
            )
        ) or 0

        return {
            "total_orders": int(total_orders),
            "total_customers": int(total_customers),
            "total_products": int(total_products),
            "total_payment_transactions": int(total_payments),
            "pending_orders": int(pending_orders),
            "captured_revenue": self._decimal(captured_revenue),
            "currency": "INR",
        }

    def get_order_status_summary(self) -> list[dict[str, Any]]:
        """Return the number of orders grouped by status."""

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

    def get_recent_orders(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return the most recently created orders."""

        if isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100.")

        statement = (
            select(Order)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(limit)
        )

        orders = self.db.scalars(statement).all()

        return [
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer_id": order.customer_id,
                "status": order.status,
                "payment_status": order.payment_status,
                "total_amount": self._decimal(order.total_amount),
                "created_at": order.created_at,
            }
            for order in orders
        ]
