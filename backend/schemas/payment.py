
"""Payment management schemas for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from backend.schemas.common import (
    BaseSchema,
    TimestampSchema,
)


# =========================================================
# PAYMENT TYPES
# =========================================================

PaymentMethod = Literal[
    "razorpay",
    "cod",
]

PaymentStatus = Literal[
    "created",
    "pending",
    "authorized",
    "captured",
    "failed",
    "cancelled",
    "refunded",
    "partially_refunded",
]

RefundStatus = Literal[
    "pending",
    "processed",
    "failed",
]


# =========================================================
# PAYMENT INITIATION
# =========================================================

class PaymentInitiateRequest(BaseSchema):
    """Request to initiate payment for an existing order."""

    order_id: int = Field(gt=0)

    payment_method: PaymentMethod


class PaymentInitiateResponse(BaseSchema):
    """Payment initiation response."""

    success: bool = True

    message: str

    payment_id: int = Field(gt=0)

    order_id: int = Field(gt=0)

    provider: str

    provider_order_id: str | None = None

    amount: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    currency: str = "INR"

    status: PaymentStatus


# =========================================================
# RAZORPAY VERIFICATION
# =========================================================

class RazorpayVerificationRequest(BaseSchema):
    """Razorpay payment verification request.

    The backend must verify the signature using the secret
    stored securely on the server.
    """

    razorpay_order_id: str = Field(
        min_length=1,
        max_length=150,
    )

    razorpay_payment_id: str = Field(
        min_length=1,
        max_length=150,
    )

    razorpay_signature: str = Field(
        min_length=1,
        max_length=500,
    )


class PaymentVerificationResponse(BaseSchema):
    """Result of server-side payment verification."""

    success: bool

    message: str

    payment_id: int = Field(gt=0)

    order_id: int = Field(gt=0)

    status: PaymentStatus

    verified_at: datetime | None = None


# =========================================================
# PAYMENT TRANSACTION RESPONSE
# =========================================================

class PaymentTransactionResponse(TimestampSchema):
    """Payment transaction details returned by the API."""

    id: int = Field(gt=0)

    order_id: int = Field(gt=0)

    payment_method: PaymentMethod

    provider: str

    provider_order_id: str | None = None

    provider_payment_id: str | None = None

    amount: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    currency: str = "INR"

    status: PaymentStatus

    failure_code: str | None = None

    failure_message: str | None = None

    authorized_at: datetime | None = None

    captured_at: datetime | None = None


# =========================================================
# REFUND REQUEST
# =========================================================

class PaymentRefundRequest(BaseSchema):
    """Request to initiate a full or partial refund."""

    payment_id: int = Field(gt=0)

    amount: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    reason: str = Field(
        min_length=5,
        max_length=1000,
    )


# =========================================================
# REFUND RESPONSE
# =========================================================

class PaymentRefundResponse(TimestampSchema):
    """Refund transaction details."""

    id: int = Field(gt=0)

    payment_id: int = Field(gt=0)

    provider_refund_id: str | None = None

    amount: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    currency: str = "INR"

    reason: str | None = None

    status: RefundStatus

    processed_at: datetime | None = None


# =========================================================
# PAYMENT HISTORY
# =========================================================

class PaymentHistoryResponse(BaseSchema):
    """List of payment transactions for an order."""

    order_id: int = Field(gt=0)

    payments: list[PaymentTransactionResponse] = Field(
        default_factory=list,
    )

    total: int = Field(
        default=0,
        ge=0,
    )


# =========================================================
# PAYMENT STATUS
# =========================================================

class PaymentStatusResponse(BaseSchema):
    """Compact payment status response."""

    order_id: int = Field(gt=0)

    payment_id: int = Field(gt=0)

    status: PaymentStatus

    amount: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )

    currency: str = "INR"

    message: str


__all__ = [
    "PaymentMethod",
    "PaymentStatus",
    "RefundStatus",
    "PaymentInitiateRequest",
    "PaymentInitiateResponse",
    "RazorpayVerificationRequest",
    "PaymentVerificationResponse",
    "PaymentTransactionResponse",
    "PaymentRefundRequest",
    "PaymentRefundResponse",
    "PaymentHistoryResponse",
    "PaymentStatusResponse",
]
