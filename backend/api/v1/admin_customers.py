
"""Administrator customer management APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_admin
from backend.database.connection import get_db
from backend.models.customer import Customer
from backend.services.admin_customer_service import AdminCustomerService


router = APIRouter(
    prefix="/admin/customers",
    tags=["Admin Customers"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class CustomerStatusUpdate(BaseModel):
    is_active: bool


# =========================================================
# SERIALIZATION
# =========================================================

def serialize_customer(customer: Customer) -> dict[str, Any]:
    """Convert customer information into JSON-safe data."""

    return {
        "id": customer.id,
        "full_name": customer.full_name,
        "email": customer.email,
        "phone_number": customer.phone_number,
        "profile_image_url": customer.profile_image_url,
        "is_active": customer.is_active,
        "email_verified": customer.email_verified,
        "phone_verified": customer.phone_verified,
        "created_at": (
            customer.created_at.isoformat()
            if customer.created_at else None
        ),
        "updated_at": (
            customer.updated_at.isoformat()
            if customer.updated_at else None
        ),
        "last_login_at": (
            customer.last_login_at.isoformat()
            if customer.last_login_at else None
        ),
    }


def serialize_customer_address(address: Any) -> dict[str, Any]:
    """Serialize a customer address."""

    return {
        "id": address.id,
        "address_type": address.address_type,
        "recipient_name": address.recipient_name,
        "phone_number": address.phone_number,
        "address_line_1": address.address_line_1,
        "address_line_2": address.address_line_2,
        "landmark": address.landmark,
        "city": address.city,
        "state": address.state,
        "country": address.country,
        "postal_code": address.postal_code,
        "is_default": address.is_default,
        "is_active": address.is_active,
    }


# =========================================================
# LIST AND SEARCH CUSTOMERS
# =========================================================

@router.get(
    "",
    summary="List and search customers",
)
def list_admin_customers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return filtered and paginated customers."""

    try:
        service = AdminCustomerService(db)

        customers, total = service.list_customers(
            page=page,
            page_size=page_size,
            search=search,
            is_active=is_active,
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
            "customers": [
                serialize_customer(customer)
                for customer in customers
            ],
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# CUSTOMER DETAILS
# =========================================================

@router.get(
    "/{customer_id}",
    summary="Get customer details",
)
def get_admin_customer(
    customer_id: int,
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return customer profile, addresses and order summary."""

    try:
        service = AdminCustomerService(db)

        customer = service.get_customer_details(customer_id)

        result = serialize_customer(customer)

        result["addresses"] = [
            serialize_customer_address(address)
            for address in customer.addresses
        ]

        result["order_summary"] = {
            "total_orders": len(customer.orders),
            "orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "payment_status": order.payment_status,
                    "total_amount": str(order.total_amount),
                    "currency": order.currency,
                    "created_at": (
                        order.created_at.isoformat()
                        if order.created_at else None
                    ),
                }
                for order in sorted(
                    customer.orders,
                    key=lambda item: item.created_at,
                    reverse=True,
                )
            ],
        }

        return {
            "success": True,
            "customer": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# =========================================================
# CUSTOMER ORDER HISTORY
# =========================================================

@router.get(
    "/{customer_id}/orders",
    summary="Get customer order history",
)
def get_admin_customer_orders(
    customer_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return paginated order history for a customer."""

    try:
        service = AdminCustomerService(db)

        orders, total = service.get_customer_orders(
            customer_id=customer_id,
            page=page,
            page_size=page_size,
        )

        return {
            "success": True,
            "customer_id": customer_id,
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
                    "status": order.status,
                    "payment_status": order.payment_status,
                    "payment_method": order.payment_method,
                    "total_amount": str(order.total_amount),
                    "currency": order.currency,
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
            status_code=404,
            detail=str(exc),
        ) from exc


# =========================================================
# ACTIVATE / DEACTIVATE CUSTOMER
# =========================================================

@router.patch(
    "/{customer_id}/status",
    summary="Activate or deactivate a customer",
)
def update_admin_customer_status(
    customer_id: int,
    payload: CustomerStatusUpdate,
    current_admin: dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Change a customer's active status."""

    try:
        service = AdminCustomerService(db)

        customer = service.update_customer_status(
            customer_id=customer_id,
            is_active=payload.is_active,
        )

        db.commit()
        db.refresh(customer)

        return {
            "success": True,
            "message": (
                "Customer activated successfully."
                if customer.is_active
                else "Customer deactivated successfully."
            ),
            "customer": serialize_customer(customer),
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
            detail="Unable to update customer status.",
        ) from exc
