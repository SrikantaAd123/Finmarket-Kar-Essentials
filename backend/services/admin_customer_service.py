
"""Admin customer management service for Finmarket Kart Essentials."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.models.customer import Customer
from backend.models.order import Order


class AdminCustomerService:
    """Business operations for administrator customer management."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_customers(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Customer], int]:
        """Return filtered and paginated customers."""

        if page < 1:
            raise ValueError("Page must be at least 1.")

        if not 1 <= page_size <= 100:
            raise ValueError("Page size must be between 1 and 100.")

        filters = []

        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Customer.full_name.ilike(term),
                    Customer.email.ilike(term),
                    Customer.phone_number.ilike(term),
                )
            )

        if is_active is not None:
            filters.append(Customer.is_active.is_(is_active))

        total = self.db.scalar(
            select(func.count(Customer.id)).where(*filters)
        ) or 0

        statement = (
            select(Customer)
            .where(*filters)
            .order_by(Customer.created_at.desc(), Customer.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        customers = list(self.db.scalars(statement).all())

        return customers, int(total)

    def get_customer_details(self, customer_id: int) -> Customer:
        """Return one customer with addresses and orders."""

        if isinstance(customer_id, bool) or customer_id < 1:
            raise ValueError("Customer ID must be positive.")

        statement = (
            select(Customer)
            .options(
                selectinload(Customer.addresses),
                selectinload(Customer.orders),
            )
            .where(Customer.id == customer_id)
        )

        customer = self.db.scalars(statement).first()

        if customer is None:
            raise ValueError("Customer not found.")

        return customer

    def get_customer_orders(
        self,
        customer_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Order], int]:
        """Return paginated order history for a customer."""

        if isinstance(customer_id, bool) or customer_id < 1:
            raise ValueError("Customer ID must be positive.")

        if page < 1:
            raise ValueError("Page must be at least 1.")

        if not 1 <= page_size <= 100:
            raise ValueError("Page size must be between 1 and 100.")

        customer_exists = self.db.scalar(
            select(Customer.id).where(Customer.id == customer_id)
        )

        if customer_exists is None:
            raise ValueError("Customer not found.")

        filters = [Order.customer_id == customer_id]

        total = self.db.scalar(
            select(func.count(Order.id)).where(*filters)
        ) or 0

        statement = (
            select(Order)
            .where(*filters)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        orders = list(self.db.scalars(statement).all())

        return orders, int(total)

    def update_customer_status(
        self,
        customer_id: int,
        is_active: bool,
    ) -> Customer:
        """Activate or deactivate a customer account."""

        if isinstance(customer_id, bool) or customer_id < 1:
            raise ValueError("Customer ID must be positive.")

        if not isinstance(is_active, bool):
            raise ValueError("is_active must be a boolean.")

        customer = self.db.get(Customer, customer_id)

        if customer is None:
            raise ValueError("Customer not found.")

        customer.is_active = is_active

        self.db.add(customer)
        self.db.flush()
        self.db.refresh(customer)

        return customer
