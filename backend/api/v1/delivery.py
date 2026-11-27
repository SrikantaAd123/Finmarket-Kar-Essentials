
"""
Customer delivery APIs for Finmarket Kart Essentials.

Endpoints:
- Check delivery serviceability by pincode.
- View available delivery slots.
- Track a shipment by tracking number.
- View shipment tracking history.

Customer authentication is required for shipment tracking.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_customer
from backend.database.connection import get_db
from backend.models.customer import Customer
from backend.models.delivery import (
    DeliverySlot,
    Shipment,
    ShipmentTracking,
)
from backend.repositories.delivery_repository import (
    DeliveryRepository,
)


router = APIRouter(
    prefix="/delivery",
    tags=["Customer Delivery"],
)


# =========================================================
# RESPONSE SCHEMAS
# =========================================================

class DeliveryServiceabilityResponse(BaseModel):
    """Pincode serviceability result."""

    is_serviceable: bool
    pincode: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    delivery_fee: Decimal
    minimum_order_amount: Decimal
    estimated_delivery_days: int | None = None
    is_cod_available: bool


class DeliverySlotResponse(BaseModel):
    """Available delivery time slot."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    delivery_date: date
    start_time: time
    end_time: time
    capacity: int
    reserved_count: int


class ShipmentTrackingEventResponse(BaseModel):
    """Individual shipment tracking event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    status: str
    description: str
    location: str | None = None
    updated_by: str | None = None
    event_time: datetime | None = None


class ShipmentTrackingResponse(BaseModel):
    """Shipment details and tracking history."""

    id: int
    shipment_number: str
    order_id: int
    status: str
    tracking_number: str | None = None
    estimated_delivery_at: datetime | None = None
    picked_up_at: datetime | None = None
    delivered_at: datetime | None = None
    delivery_notes: str | None = None
    delivery_proof_url: str | None = None
    failure_reason: str | None = None
    tracking_events: list[ShipmentTrackingEventResponse] = []


# =========================================================
# ERROR HANDLING
# =========================================================

def _handle_delivery_error(
    db: Session,
    error: Exception,
) -> None:
    """Rollback and translate errors into HTTP responses."""

    db.rollback()

    if isinstance(error, HTTPException):
        raise error

    if isinstance(error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    if isinstance(error, SQLAlchemyError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while processing delivery.",
        ) from error

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected delivery error occurred.",
    ) from error


# =========================================================
# SERIALIZATION
# =========================================================

def _serialize_tracking_event(
    event: ShipmentTracking,
) -> dict:
    """Convert a tracking event into response data."""

    return {
        "id": event.id,
        "shipment_id": event.shipment_id,
        "status": event.status,
        "description": event.description,
        "location": event.location,
        "updated_by": event.updated_by,
        "event_time": event.event_time,
    }


def _serialize_shipment(
    shipment: Shipment,
) -> dict:
    """Convert shipment and tracking events into response data."""

    return {
        "id": shipment.id,
        "shipment_number": shipment.shipment_number,
        "order_id": shipment.order_id,
        "status": shipment.status,
        "tracking_number": shipment.tracking_number,
        "estimated_delivery_at": shipment.estimated_delivery_at,
        "picked_up_at": shipment.picked_up_at,
        "delivered_at": shipment.delivered_at,
        "delivery_notes": shipment.delivery_notes,
        "delivery_proof_url": shipment.delivery_proof_url,
        "failure_reason": shipment.failure_reason,
        "tracking_events": [
            _serialize_tracking_event(event)
            for event in shipment.tracking_events
        ],
    }


# =========================================================
# CHECK PINCODE SERVICEABILITY
# =========================================================

@router.get(
    "/serviceability/{pincode}",
    response_model=DeliveryServiceabilityResponse,
    summary="Check delivery serviceability",
)
def check_delivery_serviceability(
    pincode: str,
    db: Session = Depends(get_db),
):
    """
    Check whether delivery is available for a pincode.

    This endpoint does not require customer authentication.
    """

    if not pincode.isdigit() or not 4 <= len(pincode) <= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid postal pincode.",
        )

    repository = DeliveryRepository(db)

    try:
        result = repository.check_pincode_serviceability(
            pincode
        )

        return result

    except Exception as error:
        _handle_delivery_error(db, error)


# =========================================================
# GET AVAILABLE DELIVERY SLOTS
# =========================================================

@router.get(
    "/slots",
    response_model=list[DeliverySlotResponse],
    summary="Get available delivery slots",
)
def get_available_delivery_slots(
    delivery_date: date = Query(
        ...,
        description="Delivery date in YYYY-MM-DD format.",
    ),
    db: Session = Depends(get_db),
):
    """
    Retrieve active delivery slots with available capacity.
    """

    if delivery_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery date cannot be in the past.",
        )

    repository = DeliveryRepository(db)

    try:
        slots: list[DeliverySlot] = (
            repository.get_available_delivery_slots(
                delivery_date
            )
        )

        return slots

    except Exception as error:
        _handle_delivery_error(db, error)


# =========================================================
# TRACK SHIPMENT BY TRACKING NUMBER
# =========================================================

@router.get(
    "/track/{tracking_number}",
    response_model=ShipmentTrackingResponse,
    summary="Track a shipment",
)
def track_shipment(
    tracking_number: str,
    current_customer: Customer = Depends(
        get_current_customer
    ),
    db: Session = Depends(get_db),
):
    """
    Retrieve shipment tracking information.

    A customer can only view shipments belonging to their
    own orders.
    """

    repository = DeliveryRepository(db)

    try:
        shipment = repository.get_shipment_by_tracking_number(
            tracking_number
        )

        if shipment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found.",
            )

        # Check ownership through the related order.
        if (
            shipment.order is None
            or shipment.order.customer_id != current_customer.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found.",
            )

        return _serialize_shipment(shipment)

    except Exception as error:
        _handle_delivery_error(db, error)


# =========================================================
# GET SHIPMENT BY ORDER ID
# =========================================================

@router.get(
    "/orders/{order_id}/shipment",
    response_model=ShipmentTrackingResponse,
    summary="Get shipment for an order",
)
def get_order_shipment(
    order_id: int,
    current_customer: Customer = Depends(
        get_current_customer
    ),
    db: Session = Depends(get_db),
):
    """
    Retrieve shipment information for the authenticated
    customer's order.
    """

    if order_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order ID must be greater than zero.",
        )

    repository = DeliveryRepository(db)

    try:
        shipment = repository.get_shipment_by_order_id(
            order_id
        )

        if (
            shipment is None
            or shipment.order is None
            or shipment.order.customer_id != current_customer.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found for this order.",
            )

        return _serialize_shipment(shipment)

    except Exception as error:
        _handle_delivery_error(db, error)


# =========================================================
# GET SHIPMENT TRACKING HISTORY
# =========================================================

@router.get(
    "/orders/{order_id}/tracking",
    response_model=list[ShipmentTrackingEventResponse],
    summary="Get shipment tracking history",
)
def get_shipment_tracking_history(
    order_id: int,
    current_customer: Customer = Depends(
        get_current_customer
    ),
    db: Session = Depends(get_db),
):
    """
    Retrieve tracking events for an authenticated customer's order.
    """

    if order_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order ID must be greater than zero.",
        )

    repository = DeliveryRepository(db)

    try:
        shipment = repository.get_shipment_by_order_id(
            order_id
        )

        if (
            shipment is None
            or shipment.order is None
            or shipment.order.customer_id != current_customer.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found for this order.",
            )

        events = repository.get_shipment_tracking(
            shipment.id
        )

        return [
            _serialize_tracking_event(event)
            for event in events
        ]

    except Exception as error:
        _handle_delivery_error(db, error)
