
"""Money and currency calculation utilities."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


TWO_PLACES = Decimal("0.01")


def to_decimal(value: Decimal | int | float | str) -> Decimal:
    """Convert a numeric value to Decimal safely."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid monetary amount.") from exc

    if not amount.is_finite():
        raise ValueError("Amount must be a finite number.")

    return amount


def round_money(
    value: Decimal | int | float | str,
) -> Decimal:
    """Round a monetary amount to two decimal places."""
    return to_decimal(value).quantize(
        TWO_PLACES,
        rounding=ROUND_HALF_UP,
    )


def calculate_percentage(
    amount: Decimal | int | float | str,
    percentage: Decimal | int | float | str,
) -> Decimal:
    """Calculate a percentage of an amount."""
    base = to_decimal(amount)
    rate = to_decimal(percentage)

    if rate < 0:
        raise ValueError("Percentage cannot be negative.")

    return round_money(base * rate / Decimal("100"))


def calculate_total(
    subtotal: Decimal | int | float | str,
    tax: Decimal | int | float | str = 0,
    discount: Decimal | int | float | str = 0,
) -> Decimal:
    """Calculate final total after tax and discount."""
    subtotal_value = to_decimal(subtotal)
    tax_value = to_decimal(tax)
    discount_value = to_decimal(discount)

    if subtotal_value < 0 or tax_value < 0 or discount_value < 0:
        raise ValueError("Amounts cannot be negative.")

    if discount_value > subtotal_value + tax_value:
        raise ValueError("Discount cannot exceed subtotal plus tax.")

    return round_money(
        subtotal_value + tax_value - discount_value
    )
