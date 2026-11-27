"""Customer account and address APIs for Finmarket Kart Essentials."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_customer, get_current_zitadel_user
from backend.database.connection import get_db
from backend.models.customer import Customer, CustomerAddress
from backend.repositories.customer_repository import CustomerRepository
from backend.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressListResponse,
    CustomerAddressResponse,
    CustomerAddressUpdate,
    CustomerProfileResponse,
    CustomerProfileUpdate,
)
from backend.services.customer_service import CustomerService


router = APIRouter(
    prefix="/account",
    tags=["Customer Account"],
)


# =========================================================
# SERIALIZATION HELPERS
# =========================================================


def serialize_customer(
    customer: Customer,
) -> dict[str, Any]:
    """Convert a customer model into the API response format."""

    return {
        "id": customer.id,
        "full_name": customer.full_name,
        "email": customer.email,
        "phone": customer.phone_number,
        "is_active": customer.is_active,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
    }


def serialize_address(
    address: CustomerAddress,
) -> dict[str, Any]:
    """Convert a customer address model into the API response format."""

    return {
        "id": address.id,
        "customer_id": address.customer_id,
        "label": address.address_type,
        "recipient_name": address.recipient_name,
        "phone": address.phone_number,
        "address_line1": address.address_line_1,
        "address_line2": address.address_line_2,
        "landmark": address.landmark,
        "city": address.city,
        "state": address.state,
        "postal_code": address.postal_code,
        "country": address.country,
        "is_default": address.is_default,
        "created_at": address.created_at,
        "updated_at": address.updated_at,
    }


def handle_service_error(error: ValueError) -> HTTPException:
    """Translate service validation errors into HTTP errors."""

    message = str(error)

    if "not found" in message.lower():
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    if "inactive" in message.lower():
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
    )


def address_data_to_model_fields(
    data: dict[str, Any],
) -> dict[str, Any]:
    """Map API address field names to database model field names."""

    field_mapping = {
        "label": "address_type",
        "phone": "phone_number",
        "address_line1": "address_line_1",
        "address_line2": "address_line_2",
    }

    return {
        field_mapping.get(field, field): value
        for field, value in data.items()
    }


# =========================================================
# FIRST-LOGIN CUSTOMER PROVISIONING
# =========================================================

@router.post(
    "/bootstrap",
    summary="Create or retrieve the local customer profile after ZITADEL login",
)
def bootstrap_customer(
    current_user: dict[str, Any] = Depends(get_current_zitadel_user),
    db: Session = Depends(get_db),
):
    """Provision a local customer only from a verified ZITADEL identity."""
    subject = str(current_user.get("sub") or "").strip()
    email = str(current_user.get("email") or "").strip().lower()
    claims = current_user.get("claims") or {}
    verified_value = claims.get("email_verified", False)
    email_verified = (
        verified_value is True
        or str(verified_value).strip().lower() == "true"
    )

    if not subject or not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ZITADEL did not provide a valid email and subject.",
        )

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address with ZITADEL before continuing.",
        )

    repository = CustomerRepository(db)
    created_now = False

    try:
        customer = repository.get_customer_by_zitadel_sub(subject)

        if customer is None:
            existing_email_customer = repository.get_customer_by_email(email)

            if existing_email_customer is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "A customer profile already exists for this email. "
                        "Please contact support to link the ZITADEL identity."
                    ),
                )

            full_name = (
                str(current_user.get("name") or "").strip()
                or str(current_user.get("username") or "").strip()
                or email.split("@", 1)[0]
            )

            customer, created_now = repository.get_or_create_customer(
                subject,
                {
                    "full_name": full_name[:150],
                    "email": email,
                    "email_verified": True,
                    "is_active": True,
                },
            )
            db.commit()
            db.refresh(customer)
        else:
            if not customer.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your customer account is inactive.",
                )

            # Refresh non-sensitive profile data from the verified identity.
            customer.email = email
            customer.email_verified = True
            if current_user.get("name"):
                customer.full_name = str(current_user["name"])[:150]
            db.commit()
            db.refresh(customer)

        return {
            "success": True,
            "created": created_now,
            "customer": serialize_customer(customer),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to initialize your customer account.",
        ) from error


# =========================================================
# CUSTOMER PROFILE
# =========================================================


@router.get(
    "/profile",
    response_model=CustomerProfileResponse,
    summary="Get the logged-in customer's profile",
)
def get_my_profile(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Return the authenticated customer's profile."""

    service = CustomerService(db)

    try:
        customer = service.get_customer_profile(
            current_customer.id
        )

        return serialize_customer(customer)

    except ValueError as error:
        raise handle_service_error(error) from error


@router.patch(
    "/profile",
    response_model=CustomerProfileResponse,
    summary="Update the logged-in customer's profile",
)
def update_my_profile(
    payload: CustomerProfileUpdate,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Update editable profile fields for the authenticated customer."""

    service = CustomerService(db)

    try:
        update_data = payload.model_dump(
            exclude_unset=True,
        )

        # The API schema uses "phone"; the service uses "phone_number".
        if "phone" in update_data:
            update_data["phone_number"] = update_data.pop("phone")

        customer = service.update_customer_profile(
            current_customer.id,
            update_data,
        )

        db.commit()
        db.refresh(customer)

        return serialize_customer(customer)

    except ValueError as error:
        db.rollback()
        raise handle_service_error(error) from error

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update customer profile.",
        ) from error


# =========================================================
# CUSTOMER ADDRESS OPERATIONS
# =========================================================


@router.get(
    "/addresses",
    response_model=CustomerAddressListResponse,
    summary="Get the customer's saved addresses",
)
def list_my_addresses(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Return all active addresses belonging to the customer."""

    service = CustomerService(db)

    try:
        addresses = service.get_customer_addresses(
            current_customer.id
        )

        return {
            "items": [
                serialize_address(address)
                for address in addresses
            ],
            "total": len(addresses),
        }

    except ValueError as error:
        raise handle_service_error(error) from error


@router.get(
    "/addresses/default",
    response_model=CustomerAddressResponse | None,
    summary="Get the customer's default address",
)
def get_my_default_address(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Return the customer's default active address, if available."""

    service = CustomerService(db)

    try:
        address = service.get_default_address(
            current_customer.id
        )

        if address is None:
            return None

        return serialize_address(address)

    except ValueError as error:
        raise handle_service_error(error) from error


@router.post(
    "/addresses",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a customer delivery address",
)
def create_my_address(
    payload: CustomerAddressCreate,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Create a delivery address for the authenticated customer."""

    service = CustomerService(db)

    try:
        address_data = payload.model_dump()

        address_data = address_data_to_model_fields(
            address_data
        )

        address = service.create_address(
            current_customer.id,
            address_data,
        )

        db.commit()
        db.refresh(address)

        return serialize_address(address)

    except ValueError as error:
        db.rollback()
        raise handle_service_error(error) from error

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create customer address.",
        ) from error


@router.patch(
    "/addresses/{address_id}",
    response_model=CustomerAddressResponse,
    summary="Update a saved customer address",
)
def update_my_address(
    address_id: int,
    payload: CustomerAddressUpdate,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Update an address only if it belongs to the logged-in customer."""

    service = CustomerService(db)

    try:
        address_data = payload.model_dump(
            exclude_unset=True,
        )

        address_data = address_data_to_model_fields(
            address_data
        )

        address = service.update_address(
            address_id,
            current_customer.id,
            address_data,
        )

        db.commit()
        db.refresh(address)

        return serialize_address(address)

    except ValueError as error:
        db.rollback()
        raise handle_service_error(error) from error

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update customer address.",
        ) from error


@router.patch(
    "/addresses/{address_id}/default",
    response_model=CustomerAddressResponse,
    summary="Set a saved address as default",
)
def set_my_default_address(
    address_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Set an address as default after checking customer ownership."""

    service = CustomerService(db)

    try:
        address = service.set_default_address(
            address_id,
            current_customer.id,
        )

        db.commit()
        db.refresh(address)

        return serialize_address(address)

    except ValueError as error:
        db.rollback()
        raise handle_service_error(error) from error

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to set the default address.",
        ) from error


@router.delete(
    "/addresses/{address_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a saved customer address",
)
def delete_my_address(
    address_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Delete an address belonging to the authenticated customer."""

    service = CustomerService(db)

    try:
        service.delete_address(
            address_id,
            current_customer.id,
        )

        db.commit()

        return {
            "success": True,
            "message": "Customer address deleted successfully.",
        }

    except ValueError as error:
        db.rollback()
        raise handle_service_error(error) from error

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete customer address.",
        ) from error


# =========================================================
# CUSTOMER ACCOUNT STATISTICS
# =========================================================


@router.get(
    "/statistics",
    summary="Get customer account statistics",
)
def get_my_account_statistics(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Return basic account statistics for the authenticated customer."""

    service = CustomerService(db)

    try:
        customer = service.get_customer_profile(
            current_customer.id
        )

        address_count = service.get_customer_address_count(
            current_customer.id
        )

        return {
            "customer_id": customer.id,
            "saved_address_count": address_count,
            "account_active": customer.is_active,
            "email_verified": customer.email_verified,
            "phone_verified": customer.phone_verified,
        }

    except ValueError as error:
        raise handle_service_error(error) from error