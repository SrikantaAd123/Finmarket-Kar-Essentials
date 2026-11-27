
"""Administrator APIs for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_admin
from backend.database.connection import get_db

from backend.models.customer import Customer
from backend.models.catalog import Product
from backend.models.order import Order
from backend.models.payment import PaymentTransaction, PaymentRefund
from backend.models.inventory import InventoryStock

from backend.payments.webhook_retry import WebhookRetryService
from backend.services.order_service import OrderService


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class AdminOrderStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=255)


# =========================================================
# ORDER SERIALIZATION
# =========================================================

def _serialize_admin_order(
    order: Order | None,
) -> dict[str, Any]:
    """Convert an order and related records into JSON-safe data."""

    if order is None:
        raise ValueError("Order not found.")

    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_id": order.customer_id,

        "customer": {
            "id": order.customer.id,
            "full_name": order.customer.full_name,
            "email": order.customer.email,
            "phone_number": order.customer.phone_number,
        } if order.customer else None,

        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "currency": order.currency,

        "subtotal": str(order.subtotal),
        "tax_amount": str(order.tax_amount),
        "delivery_fee": str(order.delivery_fee),
        "discount_amount": str(order.discount_amount),
        "total_amount": str(order.total_amount),

        "customer_notes": order.customer_notes,
        "cancellation_reason": order.cancellation_reason,

        "shipping_address": {
            "name": order.shipping_name,
            "phone": order.shipping_phone,
            "address_line1": order.shipping_address_line1,
            "address_line2": order.shipping_address_line2,
            "city": order.shipping_city,
            "state": order.shipping_state,
            "postal_code": order.shipping_postal_code,
            "country": order.shipping_country,
        },

        "billing_address": {
            "name": order.billing_name,
            "phone": order.billing_phone,
            "address_line1": order.billing_address_line1,
            "address_line2": order.billing_address_line2,
            "city": order.billing_city,
            "state": order.billing_state,
            "postal_code": order.billing_postal_code,
            "country": order.billing_country,
        } if order.billing_name else None,

        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "product_sku": item.product_sku,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(item.line_total),
            }
            for item in order.items
        ],

        "payments": [
            {
                "id": payment.id,
                "payment_method": payment.payment_method,
                "provider": payment.provider,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "captured_at": (
                    payment.captured_at.isoformat()
                    if payment.captured_at else None
                ),
            }
            for payment in order.payments
        ],

        "tracking_events": [
            {
                "id": event.id,
                "status": event.status,
                "title": event.title,
                "description": event.description,
                "location": event.location,
                "updated_by": event.updated_by,
                "created_at": (
                    event.created_at.isoformat()
                    if event.created_at else None
                ),
            }
            for event in order.tracking_events
        ],

        "created_at": (
            order.created_at.isoformat()
            if order.created_at else None
        ),

        "updated_at": (
            order.updated_at.isoformat()
            if order.updated_at else None
        ),
    }


# =========================================================
# PAYMENT WEBHOOK RETRY
# =========================================================

@router.post(
    "/payments/webhooks/retry",
    summary="Retry pending Razorpay webhook events",
)
def retry_payment_webhooks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retry unprocessed payment webhook events."""

    try:
        service = WebhookRetryService(db)

        result = service.retry_pending_events(
            page=page,
            page_size=page_size,
        )

        return {
            "success": True,
            "message": "Webhook retry operation completed.",
            "admin": current_admin.get("email"),
            **result,
        }

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to retry webhook events.",
        ) from exc


# =========================================================
# ADMIN DASHBOARD OVERVIEW
# =========================================================

@router.get(
    "/dashboard/overview",
    summary="Get administrator dashboard overview",
)
def get_dashboard_overview(
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return key commerce statistics for the admin dashboard."""

    # Customer statistics

    total_customers = db.scalar(
        select(func.count(Customer.id))
    ) or 0

    active_customers = db.scalar(
        select(func.count(Customer.id)).where(
            Customer.is_active.is_(True)
        )
    ) or 0

    # Product statistics

    total_products = db.scalar(
        select(func.count(Product.id))
    ) or 0

    published_products = db.scalar(
        select(func.count(Product.id)).where(
            Product.is_published.is_(True)
        )
    ) or 0

    # Order statistics

    total_orders = db.scalar(
        select(func.count(Order.id))
    ) or 0

    order_status_rows = db.execute(
        select(
            Order.status,
            func.count(Order.id),
        ).group_by(Order.status)
    ).all()

    order_status_breakdown = {
        status: int(count)
        for status, count in order_status_rows
    }

    # Inventory statistics

    total_stock_records = db.scalar(
        select(func.count(InventoryStock.id))
    ) or 0

    low_stock_records = db.scalar(
        select(func.count(InventoryStock.id)).where(
            (
                InventoryStock.quantity_on_hand
                - InventoryStock.quantity_reserved
            ) <= InventoryStock.reorder_level
        )
    ) or 0

    # Payment statistics (INR)

    gross_revenue = db.scalar(
        select(
            func.coalesce(
                func.sum(PaymentTransaction.amount),
                0,
            )
        ).where(
            PaymentTransaction.currency == "INR",
            PaymentTransaction.status.in_(
                ["captured", "partially_refunded", "refunded"]
            ),
        )
    )

    processed_refunds = db.scalar(
        select(
            func.coalesce(
                func.sum(PaymentRefund.amount),
                0,
            )
        ).where(
            PaymentRefund.currency == "INR",
            PaymentRefund.status == "processed",
        )
    )

    gross_revenue = Decimal(str(gross_revenue or 0))
    processed_refunds = Decimal(str(processed_refunds or 0))

    net_revenue = gross_revenue - processed_refunds

    captured_payment_count = db.scalar(
        select(func.count(PaymentTransaction.id)).where(
            PaymentTransaction.currency == "INR",
            PaymentTransaction.status.in_(
                ["captured", "partially_refunded", "refunded"]
            ),
        )
    ) or 0

    return {
        "success": True,
        "dashboard": {
            "customers": {
                "total": int(total_customers),
                "active": int(active_customers),
            },
            "products": {
                "total": int(total_products),
                "published": int(published_products),
            },
            "orders": {
                "total": int(total_orders),
                "status_breakdown": order_status_breakdown,
            },
            "inventory": {
                "total_stock_records": int(total_stock_records),
                "low_stock_records": int(low_stock_records),
            },
            "payments": {
                "currency": "INR",
                "captured_payment_count": int(captured_payment_count),
                "gross_revenue": str(gross_revenue),
                "processed_refunds": str(processed_refunds),
                "net_revenue": str(net_revenue),
            },
        },
    }


# =========================================================
# ADMIN ORDER LISTING
# =========================================================

@router.get(
    "/orders",
    summary="List and filter customer orders",
)
def get_admin_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    payment_status: str | None = Query(default=None),
    customer_id: int | None = Query(default=None, ge=1),
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return paginated orders for administrators."""

    try:
        service = OrderService(db)

        orders, total = service.get_all_orders(
            page=page,
            page_size=page_size,
            status=status,
            payment_status=payment_status,
            customer_id=customer_id,
        )

        return {
            "success": True,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (
                    (total + page_size - 1) // page_size
                ),
            },
            "orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "customer_id": order.customer_id,
                    "customer_name": (
                        order.customer.full_name
                        if order.customer else None
                    ),
                    "status": order.status,
                    "payment_status": order.payment_status,
                    "payment_method": order.payment_method,
                    "currency": order.currency,
                    "total_amount": str(order.total_amount),
                    "created_at": (
                        order.created_at.isoformat()
                        if order.created_at else None
                    ),
                }
                for order in orders
            ],
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# ADMIN ORDER RETRIEVAL BY ORDER NUMBER
# =========================================================

@router.get(
    "/orders/number/{order_number}",
    summary="Get an order by order number",
)
def get_admin_order_by_number(
    order_number: str,
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve complete order information using order number."""

    try:
        order = OrderService(db).get_admin_order_by_number(
            order_number
        )

        return {
            "success": True,
            "order": _serialize_admin_order(order),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# =========================================================
# ADMIN ORDER RETRIEVAL BY ID
# =========================================================

@router.get(
    "/orders/{order_id}",
    summary="Get complete order details",
)
def get_admin_order(
    order_id: int,
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve an order and its related records."""

    try:
        order = OrderService(db).get_admin_order(order_id)

        return {
            "success": True,
            "order": _serialize_admin_order(order),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# =========================================================
# ADMIN ORDER STATUS UPDATE
# =========================================================

@router.patch(
    "/orders/{order_id}/status",
    summary="Update order status",
)
def update_admin_order_status(
    order_id: int,
    payload: AdminOrderStatusUpdate,
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update order status and record its tracking event."""

    try:
        service = OrderService(db)

        admin_identifier = (
            current_admin.get("email")
            or current_admin.get("sub")
            or "admin"
        )

        order = service.update_order_status(
            order_id=order_id,
            new_status=payload.status.strip(),
            updated_by=admin_identifier,
            description=payload.description,
            location=payload.location,
        )

        db.commit()
        db.refresh(order)

        return {
            "success": True,
            "message": "Order status updated successfully.",
            "order": _serialize_admin_order(order),
        }

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to update order status.",
        ) from exc
