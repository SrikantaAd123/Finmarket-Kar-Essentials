
"""Order service for Finmarket Kart Essentials.

Handles:
- Customer checkout
- Order creation
- Shipping and billing address validation
- Order item snapshots
- Order total calculations
- Customer order history
- Order cancellation
- Order status management
- Order tracking

Database operations are delegated to repositories.
Transaction commits are managed by the caller.
"""

from __future__ import annotations

import secrets
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.cart_repository import CartRepository
from backend.repositories.customer_repository import CustomerRepository
from backend.repositories.order_repository import OrderRepository


class OrderService:
    """Business logic layer for customer orders."""

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

    PAYMENT_METHODS = {
        "razorpay",
        "cod",
    }

    CANCELLABLE_STATUSES = {
        "pending",
        "confirmed",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OrderRepository(db)
        self.cart_repository = CartRepository(db)
        self.customer_repository = CustomerRepository(db)

    # =====================================================
    # COMMON HELPERS
    # =====================================================

    @staticmethod
    def _validate_id(
        value: int,
        field_name: str = "ID",
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

    @staticmethod
    def _model_data(data: Any) -> dict[str, Any]:
        """Convert a dictionary or Pydantic model to a dictionary."""

        if isinstance(data, dict):
            return data.copy()

        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)

        raise TypeError(
            "Input must be a dictionary or Pydantic model."
        )

    @staticmethod
    def _money(value: Decimal | int | float | str) -> Decimal:
        """Normalize a monetary amount to two decimal places."""

        return Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def _validate_nonnegative_amount(
        cls,
        value: Decimal | int | float | str,
        field_name: str,
    ) -> Decimal:
        amount = cls._money(value)

        if amount < Decimal("0.00"):
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return amount

    @staticmethod
    def _generate_order_number() -> str:
        """Generate a unique-looking order reference.

        The database unique constraint remains the final
        protection against duplicate order numbers.
        """

        return f"FMK-{secrets.token_hex(8).upper()}"

    # =====================================================
    # CUSTOMER VALIDATION
    # =====================================================

    def _get_active_customer(self, customer_id: int):
        """Retrieve and validate a customer."""

        self._validate_id(customer_id, "Customer ID")

        customer = self.customer_repository.get_customer_by_id(
            customer_id
        )

        if customer is None:
            raise ValueError("Customer not found.")

        if not customer.is_active:
            raise ValueError("Customer account is inactive.")

        return customer

    def _get_customer_address(
        self,
        address_id: int,
        customer_id: int,
    ):
        """Retrieve an active address owned by the customer."""

        self._validate_id(address_id, "Address ID")

        address = self.customer_repository.get_address_by_id(
            address_id,
            customer_id,
        )

        if address is None:
            raise ValueError(
                "Address not found or does not belong to this customer."
            )

        if not address.is_active:
            raise ValueError(
                "The selected address is inactive."
            )

        return address

    @staticmethod
    def _address_snapshot(address: Any) -> dict[str, Any]:
        """Convert a saved address into an order address snapshot."""

        return {
            "name": address.recipient_name,
            "phone": address.phone_number,
            "address_line1": address.address_line_1,
            "address_line2": address.address_line_2,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
        }

    # =====================================================
    # CHECKOUT
    # =====================================================

    def checkout(
        self,
        customer_id: int,
        checkout_data: Any,
        *,
        tax_amount: Decimal | int | float | str = Decimal("0.00"),
        delivery_fee: Decimal | int | float | str = Decimal("0.00"),
        discount_amount: Decimal | int | float | str = Decimal("0.00"),
    ):
        """Create an order from the customer's active cart.

        checkout_data must contain:
            shipping_address_id
            billing_address_id (optional)
            payment_method
            customer_notes (optional)

        Tax, delivery fee and discount default to zero because
        the business pricing policy must be supplied separately.
        """

        customer = self._get_active_customer(customer_id)
        data = self._model_data(checkout_data)

        shipping_address_id = data.get("shipping_address_id")
        billing_address_id = data.get("billing_address_id")
        payment_method = data.get("payment_method")

        if shipping_address_id is None:
            raise ValueError(
                "A shipping address is required."
            )

        if payment_method not in self.PAYMENT_METHODS:
            raise ValueError(
                "Payment method must be razorpay or cod."
            )

        shipping_address = self._get_customer_address(
            int(shipping_address_id),
            customer.id,
        )

        if billing_address_id is not None:
            billing_address = self._get_customer_address(
                int(billing_address_id),
                customer.id,
            )
        else:
            billing_address = shipping_address

        # Retrieve the customer's active cart.
        cart = self.cart_repository.get_customer_cart(
            customer.id
        )

        if cart is None:
            raise ValueError(
                "Your shopping cart is empty."
            )

        cart_items = self.cart_repository.get_cart_items(
            cart.id
        )

        if not cart_items:
            raise ValueError(
                "Cannot checkout with an empty cart."
            )

        # Validate amounts supplied by the pricing layer.
        tax = self._validate_nonnegative_amount(
            tax_amount,
            "Tax amount",
        )

        delivery = self._validate_nonnegative_amount(
            delivery_fee,
            "Delivery fee",
        )

        discount = self._validate_nonnegative_amount(
            discount_amount,
            "Discount amount",
        )

        # Build immutable historical item snapshots.
        items_data: list[dict[str, Any]] = []
        subtotal = Decimal("0.00")

        for cart_item in cart_items:
            product = cart_item.product

            if product is None:
                raise ValueError(
                    "A product in your cart is no longer available."
                )

            if not product.is_active or not product.is_published:
                raise ValueError(
                    f"Product '{product.name}' is no longer available."
                )

            quantity = cart_item.quantity

            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, int)
                or quantity < 1
                or quantity > 100
            ):
                raise ValueError(
                    f"Invalid quantity for product '{product.name}'."
                )

            # Use the current database catalogue price.
            unit_price = self._money(product.price)

            if unit_price < Decimal("0.00"):
                raise ValueError(
                    f"Invalid price for product '{product.name}'."
                )

            line_total = self._money(
                unit_price * quantity
            )

            subtotal += line_total

            items_data.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "product_sku": product.sku,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                }
            )

        subtotal = self._money(subtotal)

        if discount > subtotal + tax + delivery:
            raise ValueError(
                "Discount cannot exceed the order amount."
            )

        total_amount = self._money(
            subtotal + tax + delivery - discount
        )

        shipping = self._address_snapshot(shipping_address)
        billing = self._address_snapshot(billing_address)

        customer_notes = data.get("customer_notes")

        if customer_notes is not None:
            if not isinstance(customer_notes, str):
                raise ValueError(
                    "Customer notes must be text."
                )

            customer_notes = customer_notes.strip() or None

        order_data = {
            "order_number": self._generate_order_number(),
            "customer_id": customer.id,
            "status": "pending",
            "payment_status": "pending",
            "payment_method": payment_method,
            "currency": cart.currency,
            "subtotal": subtotal,
            "tax_amount": tax,
            "delivery_fee": delivery,
            "discount_amount": discount,
            "total_amount": total_amount,
            "customer_notes": customer_notes,

            # Shipping address snapshot.
            "shipping_name": shipping["name"],
            "shipping_phone": shipping["phone"],
            "shipping_address_line1": shipping["address_line1"],
            "shipping_address_line2": shipping["address_line2"],
            "shipping_city": shipping["city"],
            "shipping_state": shipping["state"],
            "shipping_postal_code": shipping["postal_code"],
            "shipping_country": shipping["country"],

            # Billing address snapshot.
            "billing_name": billing["name"],
            "billing_phone": billing["phone"],
            "billing_address_line1": billing["address_line1"],
            "billing_address_line2": billing["address_line2"],
            "billing_city": billing["city"],
            "billing_state": billing["state"],
            "billing_postal_code": billing["postal_code"],
            "billing_country": billing["country"],
        }

        # Create order and order items.
        order = self.repository.create_order(
            order_data=order_data,
            items_data=items_data,
        )

        # Record the initial order event.
        self.repository.add_tracking_event(
            order_id=order.id,
            status="pending",
            title="Order placed",
            description="Your order has been successfully placed.",
            updated_by="system",
        )

        # Convert the cart only after the order has been created.
        self.cart_repository.convert_cart(cart.id)

        return self.repository.get_order_by_id(order.id)

    # =====================================================
    # ORDER RETRIEVAL
    # =====================================================

    def get_order(
        self,
        order_id: int,
        customer_id: int,
    ):
        """Retrieve an order belonging to a customer."""

        self._validate_id(order_id, "Order ID")
        self._get_active_customer(customer_id)

        order = self.repository.get_customer_order(
            order_id,
            customer_id,
        )

        if order is None:
            raise ValueError(
                "Order not found."
            )

        return order

    def get_order_by_number(
        self,
        order_number: str,
        customer_id: int,
    ):
        """Retrieve a customer's order by its order number."""

        if not order_number or not order_number.strip():
            raise ValueError(
                "Order number is required."
            )

        self._get_active_customer(customer_id)

        order = self.repository.get_customer_order_by_number(
            order_number.strip(),
            customer_id,
        )

        if order is None:
            raise ValueError(
                "Order not found."
            )

        return order

    def get_customer_orders(
        self,
        customer_id: int,
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
    ):
        """Retrieve paginated customer order history."""

        self._get_active_customer(customer_id)

        if page < 1:
            raise ValueError(
                "Page must be at least 1."
            )

        if not 1 <= page_size <= 100:
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        if status is not None and status not in self.ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {status}"
            )

        return self.repository.get_customer_orders(
            customer_id=customer_id,
            page=page,
            page_size=page_size,
            status=status,
        )

    def get_order_items(
        self,
        order_id: int,
        customer_id: int,
    ):
        """Retrieve the items of a customer's order."""

        self.get_order(order_id, customer_id)

        return self.repository.get_order_items(order_id)

    # =====================================================
    # ORDER CANCELLATION
    # =====================================================

    def cancel_order(
        self,
        order_id: int,
        customer_id: int,
        reason: str,
    ):
        """Cancel an eligible customer order.

        Refund processing, inventory release and notifications
        must be handled by their respective services.
        """

        self._validate_id(order_id, "Order ID")

        order = self.get_order(
            order_id,
            customer_id,
        )

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "A cancellation reason is required."
            )

        if order.status not in self.CANCELLABLE_STATUSES:
            raise ValueError(
                f"Order cannot be cancelled while its status "
                f"is '{order.status}'."
            )

        cancelled_order = self.repository.cancel_order(
            order_id=order_id,
            reason=reason.strip(),
            allowed_statuses=self.CANCELLABLE_STATUSES,
        )

        if cancelled_order is None:
            raise ValueError(
                "Order could not be cancelled."
            )

        self.repository.add_tracking_event(
            order_id=order_id,
            status="cancelled",
            title="Order cancelled",
            description=reason.strip(),
            updated_by=f"customer:{customer_id}",
        )

        return self.repository.get_order_by_id(order_id)

    # =====================================================
    # ORDER TRACKING
    # =====================================================

    def get_order_tracking(
        self,
        order_id: int,
        customer_id: int,
    ):
        """Retrieve tracking history for a customer's order."""

        self.get_order(order_id, customer_id)

        return self.repository.get_order_tracking(order_id)

    # =====================================================
    # ORDER TOTAL
    # =====================================================

    def get_order_total(
        self,
        order_id: int,
        customer_id: int,
    ) -> Decimal:
        """Retrieve the stored total of a customer's order."""

        self.get_order(order_id, customer_id)

        total = self.repository.get_order_total(order_id)

        if total is None:
            raise ValueError(
                "Order total could not be retrieved."
            )

        return total

    # =====================================================
    # ADMIN OPERATIONS
    # =====================================================

    def update_order_status(
        self,
        order_id: int,
        new_status: str,
        *,
        updated_by: str = "admin",
        description: str | None = None,
        location: str | None = None,
    ):
        """Update order status and create a tracking event.

        This method is intended for an authorized admin workflow.
        Authorization must be enforced by the API dependency.
        """

        self._validate_id(order_id, "Order ID")

        if new_status not in self.ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {new_status}"
            )

        order = self.repository.get_order_by_id(order_id)

        if order is None:
            raise ValueError("Order not found.")

        if order.status in {"cancelled", "returned", "delivered"}:
            raise ValueError(
                f"Cannot change an order from '{order.status}'."
            )

        updated_order = self.repository.update_order_status(
            order_id,
            new_status,
        )

        if updated_order is None:
            raise ValueError(
                "Order status could not be updated."
            )

        self.repository.add_tracking_event(
            order_id=order_id,
            status=new_status,
            title=f"Order {new_status.replace('_', ' ')}",
            description=description,
            location=location,
            updated_by=updated_by,
        )

        return self.repository.get_order_by_id(order_id)

    def update_payment_status(
        self,
        order_id: int,
        new_payment_status: str,
    ):
        """Update payment status through an authorized payment workflow."""

        self._validate_id(order_id, "Order ID")

        if new_payment_status not in self.PAYMENT_STATUSES:
            raise ValueError(
                f"Invalid payment status: {new_payment_status}"
            )

        order = self.repository.update_payment_status(
            order_id,
            new_payment_status,
        )

        if order is None:
            raise ValueError("Order not found.")

        return order

    def get_all_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        payment_status: str | None = None,
        customer_id: int | None = None,
    ):
        """Retrieve filtered orders for an authorized admin."""

        if page < 1:
            raise ValueError(
                "Page must be at least 1."
            )

        if not 1 <= page_size <= 100:
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        if status is not None and status not in self.ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {status}"
            )

        if (
            payment_status is not None
            and payment_status not in self.PAYMENT_STATUSES
        ):
            raise ValueError(
                f"Invalid payment status: {payment_status}"
            )

        if customer_id is not None:
            self._validate_id(customer_id, "Customer ID")

        return self.repository.get_all_orders(
            page=page,
            page_size=page_size,
            status=status,
            payment_status=payment_status,
            customer_id=customer_id,
        )

    # =====================================================
    # ORDER STATISTICS
    # =====================================================

    def count_customer_orders(self, customer_id: int) -> int:
        """Count orders belonging to a customer."""

        self._get_active_customer(customer_id)

        return self.repository.count_customer_orders(
            customer_id
        )

    def count_orders_by_status(self, status: str) -> int:
        """Count orders having a particular status."""

        if status not in self.ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {status}"
            )

        return self.repository.count_orders_by_status(status)

    # =====================================================
    # ADMIN ORDER RETRIEVAL
    # =====================================================

    def get_admin_order(self, order_id: int):
        """Retrieve any order for an authorized administrator."""

        self._validate_id(order_id, "Order ID")

        order = self.repository.get_order_by_id(order_id)

        if order is None:
            raise ValueError("Order not found.")

        return order

    def get_admin_order_by_number(self, order_number: str):
        """Retrieve an order by its unique number for an admin."""

        if not isinstance(order_number, str) or not order_number.strip():
            raise ValueError("Order number is required.")

        order = self.repository.get_order_by_number(
            order_number.strip()
        )

        if order is None:
            raise ValueError("Order not found.")

        return order
