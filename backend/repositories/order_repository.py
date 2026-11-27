
"""Order repository for Finmarket Kart Essentials.

Handles order creation, retrieval, status updates,
cancellation and order tracking.

This repository uses flush(), not commit().
Transaction management belongs to the service layer.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.order import Order, OrderItem
from backend.models.order_tracking import OrderTracking


class OrderRepository:
    """Database operations for customer and admin orders."""

    ORDER_STATUSES = {
        "pending",
        "confirmed",
        "processing",
        "packed",
        "shipped",
        "out_for_delivery",
        "delivered",
        "cancelled",
        "returned",
    }

    PAYMENT_STATUSES = {
        "pending",
        "paid",
        "failed",
        "refunded",
        "partially_refunded",
    }

    # Conservative default. The order service should enforce
    # the actual cancellation policy for your business.
    DEFAULT_CANCELLABLE_STATUSES = {
        "pending",
        "confirmed",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    # =====================================================
    # INTERNAL QUERY
    # =====================================================

    def _order_query(self):
        """Load order items and tracking events with the order."""

        return select(Order).options(
            selectinload(Order.items),
            selectinload(Order.tracking_events),
        )

    # =====================================================
    # CREATE ORDER
    # =====================================================

    def create_order(
        self,
        order_data: dict[str, Any],
        items_data: list[dict[str, Any]],
    ) -> Order:
        """Create an order and its historical item snapshots.

        order_data contains Order model fields.
        items_data contains OrderItem model fields except order_id.
        """

        if not items_data:
            raise ValueError(
                "An order must contain at least one item."
            )

        order_values = order_data.copy()

        order = Order(**order_values)

        self.db.add(order)
        self.db.flush()

        for item_data in items_data:
            item_values = item_data.copy()

            item_values.pop("id", None)
            item_values.pop("order_id", None)

            item = OrderItem(
                order_id=order.id,
                **item_values,
            )

            self.db.add(item)

        self.db.flush()

        # Reload with related records.
        created_order = self.get_order_by_id(order.id)

        if created_order is None:
            raise RuntimeError(
                "Order was created but could not be retrieved."
            )

        return created_order

    # =====================================================
    # ORDER RETRIEVAL
    # =====================================================

    def get_order_by_id(
        self,
        order_id: int,
    ) -> Order | None:
        """Retrieve an order by its primary key."""

        statement = (
            self._order_query()
            .where(Order.id == order_id)
        )

        return self.db.scalars(statement).first()

    def get_order_by_number(
        self,
        order_number: str,
    ) -> Order | None:
        """Retrieve an order using its unique order number."""

        statement = (
            self._order_query()
            .where(Order.order_number == order_number)
        )

        return self.db.scalars(statement).first()

    def get_customer_order(
        self,
        order_id: int,
        customer_id: int,
    ) -> Order | None:
        """Retrieve an order only if it belongs to the customer."""

        statement = (
            self._order_query()
            .where(
                Order.id == order_id,
                Order.customer_id == customer_id,
            )
        )

        return self.db.scalars(statement).first()

    def get_customer_order_by_number(
        self,
        order_number: str,
        customer_id: int,
    ) -> Order | None:
        """Retrieve a customer's order using its order number."""

        statement = (
            self._order_query()
            .where(
                Order.order_number == order_number,
                Order.customer_id == customer_id,
            )
        )

        return self.db.scalars(statement).first()

    # =====================================================
    # CUSTOMER ORDER HISTORY
    # =====================================================

    def get_customer_orders(
        self,
        customer_id: int,
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
    ) -> tuple[list[Order], int]:
        """Retrieve paginated order history for one customer.

        Returns:
            (orders, total_count)
        """

        self._validate_pagination(page, page_size)

        filters = [
            Order.customer_id == customer_id,
        ]

        if status is not None:
            self._validate_order_status(status)
            filters.append(Order.status == status)

        count_statement = (
            select(func.count(Order.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            self._order_query()
            .where(*filters)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        orders = list(self.db.scalars(statement).all())

        return orders, int(total)

    # =====================================================
    # ADMIN ORDER LISTING
    # =====================================================

    def get_all_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        payment_status: str | None = None,
        customer_id: int | None = None,
    ) -> tuple[list[Order], int]:
        """Retrieve filtered and paginated orders for administrators."""

        self._validate_pagination(page, page_size)

        filters = []

        if status is not None:
            self._validate_order_status(status)
            filters.append(Order.status == status)

        if payment_status is not None:
            self._validate_payment_status(payment_status)
            filters.append(
                Order.payment_status == payment_status
            )

        if customer_id is not None:
            filters.append(Order.customer_id == customer_id)

        count_statement = (
            select(func.count(Order.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            self._order_query()
            .where(*filters)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        orders = list(self.db.scalars(statement).all())

        return orders, int(total)

    # =====================================================
    # ORDER ITEM RETRIEVAL
    # =====================================================

    def get_order_items(
        self,
        order_id: int,
    ) -> list[OrderItem]:
        """Retrieve all items belonging to an order."""

        statement = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.id)
        )

        return list(self.db.scalars(statement).all())

    def get_order_item(
        self,
        order_id: int,
        item_id: int,
    ) -> OrderItem | None:
        """Retrieve an individual item belonging to an order."""

        statement = select(OrderItem).where(
            OrderItem.id == item_id,
            OrderItem.order_id == order_id,
        )

        return self.db.scalars(statement).first()

    # =====================================================
    # ORDER STATUS MANAGEMENT
    # =====================================================

    def update_order_status(
        self,
        order_id: int,
        new_status: str,
    ) -> Order | None:
        """Update the order status."""

        self._validate_order_status(new_status)

        order = self.db.get(Order, order_id)

        if order is None:
            return None

        order.status = new_status

        self.db.add(order)
        self.db.flush()
        self.db.refresh(order)

        return order

    def update_payment_status(
        self,
        order_id: int,
        new_payment_status: str,
    ) -> Order | None:
        """Update the payment status of an order."""

        self._validate_payment_status(new_payment_status)

        order = self.db.get(Order, order_id)

        if order is None:
            return None

        order.payment_status = new_payment_status

        self.db.add(order)
        self.db.flush()
        self.db.refresh(order)

        return order

    # =====================================================
    # CANCELLATION
    # =====================================================

    def cancel_order(
        self,
        order_id: int,
        reason: str,
        allowed_statuses: set[str] | None = None,
    ) -> Order | None:
        """Cancel an order if its current status permits cancellation.

        The service layer must separately handle payment refunds,
        inventory release and notifications.
        """

        order = self.db.get(Order, order_id)

        if order is None:
            return None

        cancellable = (
            allowed_statuses
            if allowed_statuses is not None
            else self.DEFAULT_CANCELLABLE_STATUSES
        )

        if order.status not in cancellable:
            raise ValueError(
                f"Order cannot be cancelled while its status "
                f"is '{order.status}'."
            )

        if not reason or not reason.strip():
            raise ValueError(
                "A cancellation reason is required."
            )

        order.status = "cancelled"
        order.cancellation_reason = reason.strip()

        self.db.add(order)
        self.db.flush()
        self.db.refresh(order)

        return order

    # =====================================================
    # TRACKING EVENTS
    # =====================================================

    def add_tracking_event(
        self,
        order_id: int,
        status: str,
        title: str,
        description: str | None = None,
        location: str | None = None,
        updated_by: str | None = None,
    ) -> OrderTracking:
        """Add a tracking event to an existing order."""

        self._validate_order_status(status)

        order = self.db.get(Order, order_id)

        if order is None:
            raise ValueError("Order does not exist.")

        event = OrderTracking(
            order_id=order_id,
            status=status,
            title=title,
            description=description,
            location=location,
            updated_by=updated_by,
        )

        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)

        return event

    def get_order_tracking(
        self,
        order_id: int,
    ) -> list[OrderTracking]:
        """Retrieve tracking events for an order."""

        statement = (
            select(OrderTracking)
            .where(OrderTracking.order_id == order_id)
            .order_by(
                OrderTracking.created_at.asc(),
                OrderTracking.id.asc(),
            )
        )

        return list(self.db.scalars(statement).all())

    # =====================================================
    # ORDER TOTALS
    # =====================================================

    def get_order_total(
        self,
        order_id: int,
    ) -> Decimal | None:
        """Retrieve the stored total amount of an order."""

        statement = select(Order.total_amount).where(
            Order.id == order_id
        )

        result = self.db.scalar(statement)

        if result is None:
            return None

        return Decimal(str(result))

    def count_customer_orders(
        self,
        customer_id: int,
    ) -> int:
        """Count all orders belonging to a customer."""

        statement = select(
            func.count(Order.id)
        ).where(
            Order.customer_id == customer_id
        )

        return int(self.db.scalar(statement) or 0)

    def count_orders_by_status(
        self,
        status: str,
    ) -> int:
        """Count orders having a particular status."""

        self._validate_order_status(status)

        statement = select(
            func.count(Order.id)
        ).where(
            Order.status == status
        )

        return int(self.db.scalar(statement) or 0)

    # =====================================================
    # INTERNAL VALIDATION
    # =====================================================

    def _validate_order_status(
        self,
        status: str,
    ) -> None:
        """Validate order status against the model constraint."""

        if status not in self.ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {status}"
            )

    def _validate_payment_status(
        self,
        status: str,
    ) -> None:
        """Validate payment status against the model constraint."""

        if status not in self.PAYMENT_STATUSES:
            raise ValueError(
                f"Invalid payment status: {status}"
            )

    @staticmethod
    def _validate_pagination(
        page: int,
        page_size: int,
    ) -> None:
        """Validate pagination values."""

        if isinstance(page, bool) or page < 1:
            raise ValueError("Page must be at least 1.")

        if isinstance(page_size, bool) or page_size < 1:
            raise ValueError("Page size must be at least 1.")

        if page_size > 100:
            raise ValueError(
                "Page size cannot exceed 100."
            )
