
"""Customer shopping cart API for Finmarket Kart Essentials."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_customer
from backend.database.connection import get_db
from backend.models.customer import Customer
from backend.schemas.cart import (
    AddToCartRequest,
    CartOperationResponse,
    CartResponse,
    CartSummaryResponse,
    UpdateCartItemRequest,
)
from backend.services.cart_service import CartService


router = APIRouter(
    prefix="/cart",
    tags=["Shopping Cart"],
)


# =========================================================
# RESPONSE SERIALIZATION
# =========================================================

def _fallback_cart_product_image(product: Any) -> str:
    """Use the same checked-in sample image set as the public catalogue."""
    name = str(getattr(product, "name", "") or "").lower()
    category = str(
        getattr(getattr(product, "category", None), "name", "") or ""
    ).lower()

    rules = (
        (("apple", "orange"), "apple.jpg"),
        (("banana",), "banana.jpg"),
        (("tomato",), "tomato.jpg"),
        (("potato", "chips"), "potato.jpg"),
        (("onion",), "onion.jpg"),
        (("carrot",), "carrot.jpg"),
        (("spinach", "broccoli", "capsicum", "cauliflower"), "spinach.jpg"),
        (("milk", "paneer", "curd", "yogurt"), "milk.jpg"),
        (("butter", "cheese"), "butter.jpg"),
        (("egg",), "eggs.jpg"),
        (("bread", "bun", "cookie", "biscuit", "cake", "rusk"), "bread.jpg"),
        (("rice", "poha", "oat", "flour", "ragi"), "rice.jpg"),
        (("moong",), "moong-dal.jpg"),
        (("dal", "lentil", "chana", "rajma", "urad", "masoor"), "toor-dal.jpg"),
        (("oil",), "cooking-oil.jpg"),
        (("sugar", "salt", "turmeric", "chilli", "masala", "coriander"), "sugar.jpg"),
        (("tea", "coffee", "juice", "drink"), "tea.jpg"),
    )
    for keywords, filename in rules:
        if any(keyword in name for keyword in keywords):
            return f"/static/images/products/{filename}"

    category_rules = (
        (("fruit", "vegetable"), "/static/images/banners/fruits-vegetables.jpg"),
        (("dairy", "egg"), "/static/images/products/milk.jpg"),
        (("bakery", "bread"), "/static/images/products/bread.jpg"),
        (("rice", "grain"), "/static/images/products/rice.jpg"),
        (("pulse", "lentil"), "/static/images/products/toor-dal.jpg"),
        (("snack", "beverage"), "/static/images/banners/snacks-beverages.jpg"),
        (("personal", "care"), "/static/images/categories/beauty-personal-care.jpg"),
        (("household", "home"), "/static/images/categories/home-kitchen-living.jpg"),
    )
    for keywords, image_url in category_rules:
        if any(keyword in category for keyword in keywords):
            return image_url

    return "/static/images/logo/finmarket-kart-essentials-icon.png"


def _serialize_product(product: Any) -> dict:
    """Convert a product model into the cart product response."""

    images = getattr(product, "images", []) or []

    primary_image = next(
        (image for image in images if image.is_primary),
        images[0] if images else None,
    )

    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "slug": product.slug,
        "price": product.price,
        "currency": product.currency,
        "unit": product.unit,
        "image_url": (
            getattr(product, "image_url", None)
            or (primary_image.image_url if primary_image is not None else None)
            or _fallback_cart_product_image(product)
        ),
        "is_active": product.is_active,
    }


def _serialize_cart_item(item: Any) -> dict:
    """Convert a cart item into a response dictionary."""

    if item.product is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product in this cart is no longer available.",
        )

    return {
        "id": item.id,
        "cart_id": item.cart_id,
        "product_id": item.product_id,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "line_total": item.line_total,
        "product": _serialize_product(item.product),
    }


def _serialize_cart(
    cart: Any,
    service: CartService,
) -> dict:
    """Build the complete customer cart response."""

    summary = service.get_cart_summary(
        cart.id,
        customer_id=cart.customer_id,
    )

    return {
        "id": cart.id,
        "customer_id": cart.customer_id,
        "status": cart.status,
        "currency": cart.currency,
        "items": [
            _serialize_cart_item(item)
            for item in cart.items
        ],
        "item_count": summary["item_count"],
        "subtotal": summary["subtotal"],
    }


# =========================================================
# ERROR HANDLING
# =========================================================

def _handle_cart_error(
    db: Session,
    error: Exception,
) -> None:
    """Rollback failed operations and return safe API errors."""

    db.rollback()

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
            detail="A database error occurred while processing the cart.",
        ) from error

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to complete the cart operation.",
    ) from error


def _get_or_create_cart(
    service: CartService,
    customer_id: int,
    db: Session,
):
    """Get the customer's active cart or create one."""

    cart = service.get_or_create_customer_cart(customer_id)

    db.commit()

    # Reload with cart items and products.
    return service.get_customer_cart(customer_id)


# =========================================================
# GET CUSTOMER CART
# =========================================================

@router.get(
    "",
    response_model=CartResponse,
    summary="Get the current customer's shopping cart",
)
def get_cart(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        service = CartService(db)

        cart = _get_or_create_cart(
            service,
            current_customer.id,
            db,
        )

        return _serialize_cart(cart, service)

    except (ValueError, SQLAlchemyError) as exc:
        _handle_cart_error(db, exc)


# =========================================================
# GET CART SUMMARY
# =========================================================

@router.get(
    "/summary",
    response_model=CartSummaryResponse,
    summary="Get the current customer's cart summary",
)
def get_cart_summary(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        service = CartService(db)

        cart = _get_or_create_cart(
            service,
            current_customer.id,
            db,
        )

        summary = service.get_cart_summary(
            cart.id,
            customer_id=current_customer.id,
        )

        return {
            "cart_id": cart.id,
            "item_count": summary["item_count"],
            "subtotal": summary["subtotal"],
            "currency": cart.currency,
        }

    except (ValueError, SQLAlchemyError) as exc:
        _handle_cart_error(db, exc)


# =========================================================
# ADD PRODUCT TO CART
# =========================================================

@router.post(
    "/items",
    response_model=CartOperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a product to the shopping cart",
)
def add_cart_item(
    payload: AddToCartRequest,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        service = CartService(db)

        service.add_item(
            product_id=payload.product_id,
            quantity=payload.quantity,
            customer_id=current_customer.id,
        )

        db.commit()

        cart = service.get_customer_cart(current_customer.id)

        return {
            "success": True,
            "message": "Product added to your cart successfully.",
            "cart": _serialize_cart(cart, service),
        }

    except (ValueError, SQLAlchemyError) as exc:
        _handle_cart_error(db, exc)


# =========================================================
# UPDATE CART ITEM QUANTITY
# =========================================================

@router.patch(
    "/items/{item_id}",
    response_model=CartOperationResponse,
    summary="Update a cart item's quantity",
)
def update_cart_item(
    item_id: int,
    payload: UpdateCartItemRequest,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        service = CartService(db)

        cart = service.get_customer_cart(current_customer.id)

        service.update_item_quantity(
            cart_id=cart.id,
            item_id=item_id,
            quantity=payload.quantity,
            customer_id=current_customer.id,
        )

        db.commit()

        cart = service.get_customer_cart(current_customer.id)

        return {
            "success": True,
            "message": "Cart item quantity updated successfully.",
            "cart": _serialize_cart(cart, service),
        }

    except (ValueError, SQLAlchemyError) as exc:
        _handle_cart_error(db, exc)


# =========================================================
# REMOVE CART ITEM
# =========================================================

@router.delete(
    "/items/{item_id}",
    response_model=CartOperationResponse,
    summary="Remove an item from the shopping cart",
)
def remove_cart_item(
    item_id: int,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        service = CartService(db)

        cart = service.get_customer_cart(current_customer.id)

        service.remove_item(
            cart_id=cart.id,
            item_id=item_id,
            customer_id=current_customer.id,
        )

        db.commit()

        cart = service.get_customer_cart(current_customer.id)

        return {
            "success": True,
            "message": "Product removed from your cart.",
            "cart": _serialize_cart(cart, service),
        }

    except (ValueError, SQLAlchemyError) as exc:
        _handle_cart_error(db, exc)


# =========================================================
# CLEAR CUSTOMER CART
# =========================================================

@router.delete(
    "",
    response_model=CartOperationResponse,
    summary="Remove all items from the shopping cart",
)
def clear_cart(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        service = CartService(db)

        cart = service.get_customer_cart(current_customer.id)

        service.clear_cart(
            cart_id=cart.id,
            customer_id=current_customer.id,
        )

        db.commit()

        cart = service.get_customer_cart(current_customer.id)

        return {
            "success": True,
            "message": "Your shopping cart has been cleared.",
            "cart": _serialize_cart(cart, service),
        }

    except (ValueError, SQLAlchemyError) as exc:
        _handle_cart_error(db, exc)
