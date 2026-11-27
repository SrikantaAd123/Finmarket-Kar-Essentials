
"""
Order invoice generation.

Responsibilities:
- Retrieve an order and its stored order items.
- Build a structured invoice representation.
- Include customer, billing, and shipping information.
- Preserve stored order prices and monetary totals.
- Return JSON-friendly invoice data.

This module does not:
- Generate PDF files.
- Create or persist a separate invoice database record.
- Recalculate product prices or taxes.
- Commit or roll back database transactions.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.order_repository import OrderRepository


class InvoiceError(ValueError):
    """Raised when invoice generation fails."""


class OrderInvoice:
    """Build invoice data for an existing order."""

    MONEY_FIELDS = (
        "subtotal",
        "tax_amount",
        "delivery_fee",
        "discount_amount",
        "total_amount",
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OrderRepository(db)

    # ---------------------------------------------------------
    # VALIDATION AND FORMATTING HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _validate_order_id(order_id: int) -> int:
        """Validate a positive order ID."""

        if isinstance(order_id, bool) or not isinstance(order_id, int):
            raise InvoiceError("Order ID must be an integer.")

        if order_id <= 0:
            raise InvoiceError("Order ID must be greater than zero.")

        return order_id

    @staticmethod
    def _to_decimal(value: Any, field_name: str) -> Decimal:
        """Convert a monetary value to Decimal safely."""

        if value is None:
            return Decimal("0.00")

        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise InvoiceError(
                f"Invalid monetary value for '{field_name}'."
            ) from exc

        if not amount.is_finite():
            raise InvoiceError(
                f"'{field_name}' must be a finite monetary value."
            )

        return amount.quantize(Decimal("0.01"))

    @classmethod
    def _format_money(cls, value: Any, field_name: str) -> str:
        """Return a monetary amount as a two-decimal string."""

        return format(
            cls._to_decimal(value, field_name),
            ".2f",
        )

    @staticmethod
    def _format_datetime(value: Any) -> str | None:
        """Convert a date or datetime into an ISO formatted string."""

        if value is None:
            return None

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        return str(value)

    @staticmethod
    def _get_value(obj: Any, field_name: str, default: Any = None) -> Any:
        """Safely retrieve an attribute from an ORM object."""

        return getattr(obj, field_name, default)

    @classmethod
    def _get_address(
        cls,
        obj: Any,
        prefix: str,
        *,
        fallback_prefix: str | None = None,
    ) -> dict[str, str | None]:
        """
        Build an address from order snapshot fields.

        If a billing field is missing, the corresponding shipping
        field can be used as a fallback.
        """

        fields = {
            "name": "name",
            "phone": "phone",
            "address_line1": "address_line1",
            "address_line2": "address_line2",
            "city": "city",
            "state": "state",
            "postal_code": "postal_code",
            "country": "country",
        }

        result: dict[str, str | None] = {}

        for output_name, field_suffix in fields.items():
            attribute = f"{prefix}_{field_suffix}"
            value = cls._get_value(obj, attribute)

            if value is None and fallback_prefix is not None:
                fallback_attribute = (
                    f"{fallback_prefix}_{field_suffix}"
                )
                value = cls._get_value(obj, fallback_attribute)

            result[output_name] = (
                str(value).strip() if value is not None else None
            )

        return result

    # ---------------------------------------------------------
    # ORDER RETRIEVAL
    # ---------------------------------------------------------

    def get_order(self, order_id: int) -> Any:
        """Retrieve an order or raise an error."""

        order_id = self._validate_order_id(order_id)

        order = self.repository.get_order_by_id(order_id)

        if order is None:
            raise InvoiceError(
                f"Order with ID {order_id} was not found."
            )

        return order

    # ---------------------------------------------------------
    # INVOICE ITEM BUILDER
    # ---------------------------------------------------------

    @classmethod
    def _build_invoice_item(cls, item: Any) -> dict[str, Any]:
        """Convert one OrderItem ORM object into invoice item data."""

        quantity = cls._get_value(item, "quantity", 0)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError) as exc:
            raise InvoiceError(
                "An order item has an invalid quantity."
            ) from exc

        if quantity <= 0:
            raise InvoiceError(
                "Order item quantity must be greater than zero."
            )

        unit_price = cls._to_decimal(
            cls._get_value(item, "unit_price"),
            "unit_price",
        )

        line_total_value = cls._get_value(item, "line_total")

        if line_total_value is None:
            line_total = unit_price * quantity
        else:
            line_total = cls._to_decimal(
                line_total_value,
                "line_total",
            )

        return {
            "order_item_id": cls._get_value(item, "id"),
            "product_id": cls._get_value(item, "product_id"),
            "product_name": cls._get_value(
                item,
                "product_name",
                "",
            ),
            "product_sku": cls._get_value(
                item,
                "product_sku",
            ),
            "quantity": quantity,
            "unit_price": cls._format_money(
                unit_price,
                "unit_price",
            ),
            "line_total": cls._format_money(
                line_total,
                "line_total",
            ),
        }

    # ---------------------------------------------------------
    # INVOICE BUILDER
    # ---------------------------------------------------------

    def build_invoice(self, order_id: int) -> dict[str, Any]:
        """
        Build an invoice dictionary for an existing order.

        The invoice number is derived from the existing order number.
        It is a display identifier, not a separately persisted invoice.
        """

        order = self.get_order(order_id)

        order_number = self._get_value(order, "order_number")

        if not order_number:
            raise InvoiceError(
                "The order does not have a valid order number."
            )

        order_items = self._get_value(order, "items", None)

        if order_items is None:
            order_items = self.repository.get_order_items(order_id)

        if order_items is None:
            order_items = []

        items = [
            self._build_invoice_item(item)
            for item in order_items
        ]

        if not items:
            raise InvoiceError(
                f"Order '{order_number}' does not contain any items."
            )

        currency = self._get_value(order, "currency", "INR")

        if not currency:
            currency = "INR"

        currency = str(currency).upper()

        monetary_totals = {
            field: self._format_money(
                self._get_value(order, field),
                field,
            )
            for field in self.MONEY_FIELDS
        }

        shipping_address = self._get_address(
            order,
            "shipping",
        )

        billing_address = self._get_address(
            order,
            "billing",
            fallback_prefix="shipping",
        )

        return {
            "invoice_number": f"INV-{order_number}",
            "order_id": self._get_value(order, "id"),
            "order_number": order_number,
            "invoice_date": self._format_datetime(
                self._get_value(order, "created_at")
            ),
            "last_updated": self._format_datetime(
                self._get_value(order, "updated_at")
            ),
            "currency": currency,
            "order_status": self._get_value(order, "status"),
            "payment_status": self._get_value(
                order,
                "payment_status",
            ),
            "payment_method": self._get_value(
                order,
                "payment_method",
            ),
            "customer": {
                "customer_id": self._get_value(
                    order,
                    "customer_id",
                ),
                "name": shipping_address["name"],
                "phone": shipping_address["phone"],
            },
            "billing_address": billing_address,
            "shipping_address": shipping_address,
            "items": items,
            "totals": monetary_totals,
            "customer_notes": self._get_value(
                order,
                "customer_notes",
            ),
        }

    # ---------------------------------------------------------
    # CONVENIENCE METHODS
    # ---------------------------------------------------------

    def get_invoice(self, order_id: int) -> dict[str, Any]:
        """Alias for build_invoice()."""

        return self.build_invoice(order_id)

    def get_invoice_number(self, order_id: int) -> str:
        """Return the display invoice number for an order."""

        order = self.get_order(order_id)
        order_number = self._get_value(order, "order_number")

        if not order_number:
            raise InvoiceError(
                "The order does not have a valid order number."
            )

        return f"INV-{order_number}"
