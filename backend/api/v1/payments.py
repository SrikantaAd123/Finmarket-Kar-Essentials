
"""Customer payment APIs for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_customer
from backend.database.connection import get_db
from backend.models.customer import Customer
from backend.models.payment import PaymentTransaction
from backend.services.payment_service import PaymentService


router = APIRouter(
    prefix="/payments",
    tags=["Customer Payments"],
)


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class PaymentInitiateRequest(BaseModel):
    """Request to initiate payment for an existing order."""

    idempotency_key: str = Field(
        min_length=8,
        max_length=150,
    )


class PaymentVerificationRequest(BaseModel):
    """Razorpay payment verification details."""

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


# =========================================================
# RESPONSE SERIALIZATION
# =========================================================

def _serialize_payment(payment: Any) -> dict[str, Any]:
    """Return payment information without secret credentials."""

    if payment is None:
        raise ValueError("Payment not found.")

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "payment_method": payment.payment_method,
        "provider": payment.provider,
        "provider_order_id": payment.provider_order_id,
        "provider_payment_id": payment.provider_payment_id,
        "amount": Decimal(str(payment.amount)),
        "currency": payment.currency,
        "status": payment.status,
        "failure_code": payment.failure_code,
        "failure_message": payment.failure_message,
        "created_at": payment.created_at,
    }


# =========================================================
# ERROR HANDLING
# =========================================================

def _handle_payment_error(
    db: Session,
    error: Exception,
) -> None:
    """Rollback failed database work and return a suitable HTTP error."""

    db.rollback()

    if isinstance(error, HTTPException):
        raise error

    if isinstance(error, ValueError):
        message = str(error)

        if "not found" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from error

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from error

    if isinstance(error, SQLAlchemyError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while processing payment.",
        ) from error

    if isinstance(error, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected payment error occurred.",
    ) from error


# =========================================================
# INITIATE PAYMENT
# =========================================================

@router.post(
    "/orders/{order_id}/initiate",
    summary="Initiate Razorpay or COD payment",
)
def initiate_payment(
    order_id: int,
    payload: PaymentInitiateRequest,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Initiate payment for an order belonging to the customer.

    The amount is obtained from the database order.
    The client cannot submit or modify the payment amount.
    """

    service = PaymentService(db)

    try:
        payment_data = service.initiate_payment(
            order_id=order_id,
            customer_id=current_customer.id,
            idempotency_key=payload.idempotency_key,
        )

        db.commit()

        return {
            "success": True,
            "message": "Payment initiated successfully.",
            "payment": payment_data,
        }

    except Exception as error:
        _handle_payment_error(db, error)


# =========================================================
# VERIFY RAZORPAY PAYMENT
# =========================================================

@router.post(
    "/orders/{order_id}/verify",
    summary="Verify Razorpay payment",
)
def verify_payment(
    order_id: int,
    payload: PaymentVerificationRequest,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Verify Razorpay signature and confirm the gateway payment."""

    service = PaymentService(db)

    try:
        payment_data = service.verify_payment(
            order_id=order_id,
            customer_id=current_customer.id,
            provider_order_id=payload.razorpay_order_id,
            provider_payment_id=payload.razorpay_payment_id,
            signature=payload.razorpay_signature,
        )

        db.commit()

        return {
            "success": True,
            "message": "Payment verification completed.",
            "payment": payment_data,
        }

    except Exception as error:
        _handle_payment_error(db, error)


# =========================================================
# GET ALL PAYMENTS FOR AN ORDER
# =========================================================

@router.get(
    "/orders/{order_id}",
    summary="Get payments for an order",
)
def get_order_payments(
    order_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Retrieve payment attempts belonging to the customer's order."""

    service = PaymentService(db)

    try:
        payments = service.get_order_payments(
            order_id=order_id,
            customer_id=current_customer.id,
        )

        return {
            "success": True,
            "total": len(payments),
            "items": [
                _serialize_payment(payment)
                for payment in payments
            ],
        }

    except Exception as error:
        _handle_payment_error(db, error)


# =========================================================
# GET PAYMENT DETAILS
# =========================================================

@router.get(
    "/{payment_id}",
    summary="Get payment details",
)
def get_payment(
    payment_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Retrieve one payment belonging to the authenticated customer."""

    service = PaymentService(db)

    try:
        payment = service.get_payment(
            payment_id=payment_id,
            customer_id=current_customer.id,
        )

        return {
            "success": True,
            "payment": _serialize_payment(payment),
        }

    except Exception as error:
        _handle_payment_error(db, error)
