
"""Customer order APIs for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
import logging
import os

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_customer
from backend.database.connection import get_db

from backend.models.customer import Customer
from backend.models.order import Order
from backend.models.payment import PaymentTransaction
from backend.models.delivery import Shipment
from backend.models.order_return import OrderReturn

from backend.schemas.order import (
    OrderCheckoutRequest,
    OrderListResponse,
    OrderResponse,
    OrderTrackingResponse,
)

from backend.services.order_service import OrderService


router = APIRouter(
    prefix="/orders",
    tags=["Customer Orders"],
)

logger = logging.getLogger("finmarket.orders")


# =========================================================
# RESPONSE SERIALIZATION
# =========================================================

def _serialize_address(
    order: Any,
    prefix: str,
) -> dict[str, Any] | None:
    """Convert an order address snapshot into response data."""

    name = getattr(order, f"{prefix}_name", None)

    if not name:
        return None

    return {
        "recipient_name": name,
        "phone": getattr(order, f"{prefix}_phone", None),
        "address_line1": getattr(
            order,
            f"{prefix}_address_line1",
            None,
        ),
        "address_line2": getattr(
            order,
            f"{prefix}_address_line2",
            None,
        ),
        "city": getattr(order, f"{prefix}_city", None),
        "state": getattr(order, f"{prefix}_state", None),
        "postal_code": getattr(
            order,
            f"{prefix}_postal_code",
            None,
        ),
        "country": getattr(
            order,
            f"{prefix}_country",
            None,
        ),
    }


def _serialize_order_item(item: Any) -> dict[str, Any]:
    """Convert an order item into response data."""

    return {
        "id": item.id,
        "product_id": item.product_id,
        "product_name": item.product_name,
        "product_sku": item.product_sku,
        "quantity": item.quantity,
        "unit_price": Decimal(str(item.unit_price)),
        "line_total": Decimal(str(item.line_total)),
    }


def _serialize_tracking_event(event: Any) -> dict[str, Any]:
    """Convert a tracking event into response data."""

    return {
        "id": event.id,
        "status": event.status,
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "updated_by": event.updated_by,
        "created_at": event.created_at,
    }


def _serialize_order(order: Any) -> dict[str, Any]:
    """Convert an order and its related data into response data."""

    if order is None:
        raise ValueError("Order not found.")

    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_id": order.customer_id,
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "currency": order.currency,
        "subtotal": Decimal(str(order.subtotal)),
        "tax_amount": Decimal(str(order.tax_amount)),
        "delivery_fee": Decimal(str(order.delivery_fee)),
        "discount_amount": Decimal(str(order.discount_amount)),
        "total_amount": Decimal(str(order.total_amount)),
        "customer_notes": order.customer_notes,
        "cancellation_reason": order.cancellation_reason,
        "shipping_address": _serialize_address(
            order,
            "shipping",
        ),
        "billing_address": _serialize_address(
            order,
            "billing",
        ),
        "items": [
            _serialize_order_item(item)
            for item in order.items
        ],
        "tracking_events": [
            _serialize_tracking_event(event)
            for event in order.tracking_events
        ],
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


# =========================================================
# ERROR HANDLING
# =========================================================

def _handle_order_error(
    db: Session,
    error: Exception,
) -> None:
    """Rollback a failed database transaction and raise HTTP error."""

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
        logger.exception(
            "Database error while processing order"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "A database error occurred while processing the order."
            ),
        ) from error

    logger.exception(
        "Unexpected error while processing order"
    )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=(
            "An unexpected error occurred while processing the order."
        ),
    ) from error


# =========================================================
# ORDER EMAIL NOTIFICATIONS
# =========================================================

def _send_order_email_safely(
    recipient: str,
    subject: str,
    message: str,
) -> None:
    """Send an order email without rolling back a successful order."""

    if not recipient or "@" not in recipient:
        return

    try:
        from backend.notifications.email import send_email

        send_email(
            recipient,
            subject,
            message,
        )

        logger.info(
            "Order notification email queued successfully for %s",
            recipient,
        )

    except Exception:
        logger.exception(
            "Order notification email could not be delivered to %s",
            recipient,
        )


# =========================================================
# CHECKOUT
# =========================================================

@router.post(
    "/checkout",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order",
)
def checkout(
    payload: OrderCheckoutRequest,
    background_tasks: BackgroundTasks,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Create an order from the authenticated customer's cart."""

    service = OrderService(db)

    try:
        order = service.checkout(
            customer_id=current_customer.id,
            checkout_data=payload,
        )

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Order creation failed.",
            )

        order_id = order.id

        db.commit()

        saved_order = service.get_order(
            order_id=order_id,
            customer_id=current_customer.id,
        )

        if saved_order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Created order could not be retrieved.",
            )

        order_number = str(saved_order.order_number)
        order_total = str(saved_order.total_amount)

        customer_email = str(
            getattr(current_customer, "email", "") or ""
        )

        customer_name = str(
            getattr(current_customer, "full_name", "") or "Customer"
        )

        customer_message = (
            f"Hello {customer_name},\n\n"
            "Thank you for shopping with FINMARKET Kart Essentials.\n"
            f"Your order {order_number} has been placed successfully.\n"
            f"Order total: INR {order_total}\n"
            f"Payment method: {saved_order.payment_method}\n"
            f"Order status: {saved_order.status}\n\n"
            "You can sign in to your account to view your order status.\n"
            "Thank you,\nFINMARKET Kart Essentials"
        )

        if customer_email:
            background_tasks.add_task(
                _send_order_email_safely,
                customer_email,
                f"FINMARKET order confirmation - {order_number}",
                customer_message,
            )

        admin_email = (
            os.getenv("ORDER_NOTIFICATION_EMAIL", "").strip()
            or os.getenv("ADMIN_NOTIFICATION_EMAIL", "").strip()
        )

        if admin_email:
            admin_message = (
                "A new FINMARKET order has been placed.\n\n"
                f"Order: {order_number}\n"
                f"Customer: {customer_name} ({customer_email})\n"
                f"Total: INR {order_total}\n"
                f"Payment method: {saved_order.payment_method}\n"
                f"Status: {saved_order.status}"
            )

            background_tasks.add_task(
                _send_order_email_safely,
                admin_email,
                f"New FINMARKET order - {order_number}",
                admin_message,
            )

        return _serialize_order(saved_order)

    except Exception as error:
        _handle_order_error(db, error)


# =========================================================
# CUSTOMER ORDER HISTORY
# =========================================================

@router.get(
    "",
    response_model=OrderListResponse,
    summary="Get customer orders",
)
def get_customer_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    order_status: str | None = Query(
        default=None,
        alias="status",
    ),
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Retrieve paginated orders belonging to the customer."""

    service = OrderService(db)

    try:
        orders, total = service.get_customer_orders(
            customer_id=current_customer.id,
            page=page,
            page_size=page_size,
            status=order_status,
        )

        return {
            "items": [
                _serialize_order(order)
                for order in orders
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    except Exception as error:
        _handle_order_error(db, error)


# =========================================================
# GET ORDER BY ORDER NUMBER
# =========================================================

@router.get(
    "/number/{order_number}",
    response_model=OrderResponse,
    summary="Get order by order number",
)
def get_order_by_number(
    order_number: str,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Retrieve an order using its unique order number."""

    service = OrderService(db)

    try:
        order = service.get_order_by_number(
            order_number=order_number,
            customer_id=current_customer.id,
        )

        return _serialize_order(order)

    except Exception as error:
        _handle_order_error(db, error)


# =========================================================
# GET ORDER BY ID
# =========================================================

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order details",
)
def get_order(
    order_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Retrieve a specific order belonging to the customer."""

    service = OrderService(db)

    try:
        order = service.get_order(
            order_id=order_id,
            customer_id=current_customer.id,
        )

        return _serialize_order(order)

    except Exception as error:
        _handle_order_error(db, error)


# =========================================================
# DELETE CUSTOMER ORDER
# =========================================================

@router.delete(
    "/{order_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an eligible unpaid customer order",
)
def delete_customer_order(
    order_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """
    Permanently delete an eligible unpaid order.

    Conditions:
    - Authenticated customer must own the order.
    - Order status must be pending.
    - Payment status must be pending or failed.
    - No payment transaction records may exist.
    - No shipment records may exist.
    - No return records may exist.
    """

    try:
        # Lock the order row while checking eligibility.
        order = (
            db.query(Order)
            .filter(
                Order.id == order_id,
                Order.customer_id == current_customer.id,
            )
            .with_for_update()
            .first()
        )

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found.",
            )

        # Validate order status.
        if str(order.status).lower() != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Only pending orders can be permanently deleted."
                ),
            )

        # Validate payment status.
        if str(order.payment_status).lower() not in {
            "pending",
            "failed",
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Paid or refunded orders cannot be deleted."
                ),
            )

        # -------------------------------------------------
        # CHECK PAYMENT TRANSACTIONS
        # -------------------------------------------------

        payment_exists = (
            db.query(PaymentTransaction.id)
            .filter(
                PaymentTransaction.order_id == order_id
            )
            .first()
        )

        if payment_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This order has payment transaction records "
                    "and cannot be permanently deleted."
                ),
            )

        # -------------------------------------------------
        # CHECK SHIPMENT
        # -------------------------------------------------

        shipment_exists = (
            db.query(Shipment.id)
            .filter(
                Shipment.order_id == order_id
            )
            .first()
        )

        if shipment_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This order has shipment records "
                    "and cannot be permanently deleted."
                ),
            )

        # -------------------------------------------------
        # CHECK RETURNS
        # -------------------------------------------------

        return_exists = (
            db.query(OrderReturn.id)
            .filter(
                OrderReturn.order_id == order_id
            )
            .first()
        )

        if return_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This order has return records "
                    "and cannot be permanently deleted."
                ),
            )

        # -------------------------------------------------
        # DELETE ORDER
        # -------------------------------------------------

        deleted_order_number = order.order_number

        db.delete(order)
        db.commit()

        logger.info(
            "Customer %s deleted order %s (ID: %s)",
            current_customer.id,
            deleted_order_number,
            order_id,
        )

        return {
            "success": True,
            "message": "Order deleted successfully.",
            "order_id": order_id,
            "order_number": deleted_order_number,
        }

    except Exception as error:
        _handle_order_error(db, error)


# =========================================================
# ORDER TRACKING
# =========================================================

@router.get(
    "/{order_id}/tracking",
    response_model=OrderTrackingResponse,
    summary="Get order tracking history",
)
def get_order_tracking(
    order_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Retrieve tracking events for a customer's order."""

    service = OrderService(db)

    try:
        events = service.get_order_tracking(
            order_id=order_id,
            customer_id=current_customer.id,
        )

        return {
            "items": [
                _serialize_tracking_event(event)
                for event in events
            ],
            "total": len(events),
        }

    except Exception as error:
        _handle_order_error(db, error)


# =========================================================
# ORDER TOTAL
# =========================================================

@router.get(
    "/{order_id}/total",
    summary="Get order total",
)
def get_order_total(
    order_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Retrieve the stored total for a customer's order."""

    service = OrderService(db)

    try:
        total = service.get_order_total(
            order_id=order_id,
            customer_id=current_customer.id,
        )

        return {
            "order_id": order_id,
            "total_amount": total,
        }

    except Exception as error:
        _handle_order_error(db, error)
