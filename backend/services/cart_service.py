
"""Shopping cart service for Finmarket Kart Essentials.

Handles:
- Registered customer carts
- Guest shopping carts
- Adding products to carts
- Updating cart item quantities
- Removing cart items
- Cart summaries and totals
- Clearing and converting carts
- Abandoning carts

Database operations are delegated to CartRepository.
Transaction commits are managed by the caller.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.cart_repository import CartRepository


class CartService:
    """Business logic layer for shopping cart management."""

    MAX_ITEM_QUANTITY = 100

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CartRepository(db)

    # =====================================================
    # COMMON VALIDATION HELPERS
    # =====================================================

    @staticmethod
    def _validate_id(
        value: int,
        field_name: str = "ID",
    ) -> None:
        """Validate a positive database identifier."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        """Validate the requested product quantity."""

        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError(
                "Quantity must be an integer."
            )

        if quantity < 1:
            raise ValueError(
                "Quantity must be at least 1."
            )

        if quantity > CartService.MAX_ITEM_QUANTITY:
            raise ValueError(
                f"Maximum allowed quantity is "
                f"{CartService.MAX_ITEM_QUANTITY}."
            )

    @staticmethod
    def _validate_guest_token(
        guest_token_hash: str,
    ) -> str:
        """Validate an already-hashed guest token."""

        if (
            not isinstance(guest_token_hash, str)
            or not guest_token_hash.strip()
        ):
            raise ValueError(
                "A valid guest token hash is required."
            )

        return guest_token_hash.strip()

    @staticmethod
    def _validate_owner(
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> None:
        """Ensure exactly one cart owner is provided."""

        if customer_id is not None and guest_token_hash is not None:
            raise ValueError(
                "Provide either a customer ID or a guest token, not both."
            )

        if customer_id is None and guest_token_hash is None:
            raise ValueError(
                "A customer ID or guest token is required."
            )

        if customer_id is not None:
            CartService._validate_id(
                customer_id,
                "Customer ID",
            )

        if guest_token_hash is not None:
            CartService._validate_guest_token(
                guest_token_hash
            )

    # =====================================================
    # CART CREATE / RETRIEVE
    # =====================================================

    def get_or_create_customer_cart(
        self,
        customer_id: int,
    ):
        """Get an active customer cart or create one."""

        self._validate_id(customer_id, "Customer ID")

        return self.repository.get_or_create_customer_cart(
            customer_id
        )

    def get_or_create_guest_cart(
        self,
        guest_token_hash: str,
    ):
        """Get an active guest cart or create one."""

        token_hash = self._validate_guest_token(
            guest_token_hash
        )

        return self.repository.get_or_create_guest_cart(
            token_hash
        )

    def get_customer_cart(self, customer_id: int):
        """Retrieve an existing customer cart."""

        self._validate_id(customer_id, "Customer ID")

        cart = self.repository.get_customer_cart(
            customer_id
        )

        if cart is None:
            raise ValueError(
                "No active shopping cart was found for this customer."
            )

        return cart

    def get_guest_cart(self, guest_token_hash: str):
        """Retrieve an existing guest cart."""

        token_hash = self._validate_guest_token(
            guest_token_hash
        )

        cart = self.repository.get_guest_cart(
            token_hash
        )

        if cart is None:
            raise ValueError(
                "No active shopping cart was found for this guest."
            )

        return cart

    def get_cart(
        self,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Retrieve an active cart belonging to its owner."""

        self._validate_owner(
            customer_id,
            guest_token_hash,
        )

        if customer_id is not None:
            return self.get_customer_cart(customer_id)

        return self.get_guest_cart(
            guest_token_hash  # type: ignore[arg-type]
        )

    def get_cart_by_id(self, cart_id: int):
        """Retrieve a cart by its database ID."""

        self._validate_id(cart_id, "Cart ID")

        cart = self.repository.get_cart_by_id(cart_id)

        if cart is None:
            raise ValueError("Shopping cart not found.")

        return cart

    # =====================================================
    # CART OWNERSHIP
    # =====================================================

    def get_owned_cart(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Retrieve a cart only when it belongs to the given owner."""

        self._validate_id(cart_id, "Cart ID")

        self._validate_owner(
            customer_id,
            guest_token_hash,
        )

        if customer_id is not None:
            cart = self.repository.get_customer_owned_cart(
                cart_id,
                customer_id,
            )
        else:
            token_hash = self._validate_guest_token(
                guest_token_hash  # type: ignore[arg-type]
            )

            cart = self.repository.get_guest_owned_cart(
                cart_id,
                token_hash,
            )

        if cart is None:
            raise ValueError(
                "Shopping cart not found or access is not permitted."
            )

        return cart

    # =====================================================
    # ADD PRODUCT TO CART
    # =====================================================

    def add_item(
        self,
        product_id: int,
        quantity: int = 1,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Add a product to the owner's cart.

        Product prices are obtained from the database.
        Frontend-supplied prices are never accepted.
        """

        self._validate_id(product_id, "Product ID")
        self._validate_quantity(quantity)

        self._validate_owner(
            customer_id,
            guest_token_hash,
        )

        if customer_id is not None:
            cart = self.repository.get_or_create_customer_cart(
                customer_id
            )
        else:
            token_hash = self._validate_guest_token(
                guest_token_hash  # type: ignore[arg-type]
            )

            cart = self.repository.get_or_create_guest_cart(
                token_hash
            )

        return self.repository.add_item(
            cart_id=cart.id,
            product_id=product_id,
            quantity=quantity,
        )

    def add_item_to_cart(
        self,
        cart_id: int,
        product_id: int,
        quantity: int = 1,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Add a product to an existing owned cart."""

        self._validate_id(cart_id, "Cart ID")
        self._validate_id(product_id, "Product ID")
        self._validate_quantity(quantity)

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        return self.repository.add_item(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
        )

    # =====================================================
    # CART ITEM RETRIEVAL
    # =====================================================

    def get_cart_item(
        self,
        cart_id: int,
        item_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Retrieve one item after checking cart ownership."""

        self._validate_id(cart_id, "Cart ID")
        self._validate_id(item_id, "Cart item ID")

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        item = self.repository.get_cart_item(
            cart_id,
            item_id,
        )

        if item is None:
            raise ValueError(
                "Cart item not found."
            )

        return item

    def get_cart_items(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Retrieve all items in an owned cart."""

        self._validate_id(cart_id, "Cart ID")

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        return self.repository.get_cart_items(cart_id)

    # =====================================================
    # UPDATE CART ITEM
    # =====================================================

    def update_item_quantity(
        self,
        cart_id: int,
        item_id: int,
        quantity: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Update the quantity of a product in the cart."""

        self._validate_id(cart_id, "Cart ID")
        self._validate_id(item_id, "Cart item ID")
        self._validate_quantity(quantity)

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        item = self.repository.update_item_quantity(
            cart_id=cart_id,
            item_id=item_id,
            quantity=quantity,
        )

        if item is None:
            raise ValueError(
                "Cart item not found."
            )

        return item

    # =====================================================
    # REMOVE CART ITEM
    # =====================================================

    def remove_item(
        self,
        cart_id: int,
        item_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> bool:
        """Remove an item from an owned cart."""

        self._validate_id(cart_id, "Cart ID")
        self._validate_id(item_id, "Cart item ID")

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        deleted = self.repository.remove_item(
            cart_id,
            item_id,
        )

        if not deleted:
            raise ValueError(
                "Cart item not found."
            )

        return True

    def remove_product(
        self,
        cart_id: int,
        product_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> bool:
        """Remove a product from an owned cart."""

        self._validate_id(cart_id, "Cart ID")
        self._validate_id(product_id, "Product ID")

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        deleted = self.repository.remove_product(
            cart_id,
            product_id,
        )

        if not deleted:
            raise ValueError(
                "Product was not found in this cart."
            )

        return True

    # =====================================================
    # CART SUMMARY
    # =====================================================

    def get_cart_summary(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> dict[str, Any]:
        """Return cart items and calculated totals."""

        self._validate_id(cart_id, "Cart ID")

        cart = self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        summary = self.repository.get_cart_summary(
            cart_id
        )

        return {
            "cart_id": cart.id,
            "customer_id": cart.customer_id,
            "currency": cart.currency,
            "status": cart.status,
            "item_count": summary["item_count"],
            "unique_item_count": summary["unique_item_count"],
            "subtotal": summary["subtotal"],
        }

    def get_cart_item_count(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> int:
        """Return the total quantity of products in the cart."""

        self._validate_id(cart_id, "Cart ID")

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        return self.repository.get_item_count(cart_id)

    def get_unique_item_count(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> int:
        """Return the number of distinct products in the cart."""

        self._validate_id(cart_id, "Cart ID")

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        return self.repository.get_unique_item_count(
            cart_id
        )

    def get_cart_subtotal(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> Decimal:
        """Return the cart subtotal."""

        self._validate_id(cart_id, "Cart ID")

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        return self.repository.get_cart_subtotal(cart_id)

    # =====================================================
    # CLEAR CART
    # =====================================================

    def clear_cart(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> bool:
        """Remove every item from an owned active cart."""

        self._validate_id(cart_id, "Cart ID")

        self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        cleared = self.repository.clear_cart(cart_id)

        if not cleared:
            raise ValueError(
                "Shopping cart could not be cleared."
            )

        return True

    # =====================================================
    # CONVERT CART
    # =====================================================

    def convert_cart(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Mark an owned cart as converted after checkout."""

        self._validate_id(cart_id, "Cart ID")

        cart = self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        summary = self.repository.get_cart_summary(cart_id)

        if summary["item_count"] <= 0:
            raise ValueError(
                "An empty cart cannot be converted."
            )

        converted_cart = self.repository.convert_cart(
            cart.id
        )

        if converted_cart is None:
            raise ValueError(
                "Shopping cart could not be converted."
            )

        return converted_cart

    # =====================================================
    # ABANDON CART
    # =====================================================

    def abandon_cart(
        self,
        cart_id: int,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ):
        """Mark an owned active cart as abandoned."""

        self._validate_id(cart_id, "Cart ID")

        cart = self.get_owned_cart(
            cart_id,
            customer_id,
            guest_token_hash,
        )

        abandoned_cart = self.repository.abandon_cart(
            cart.id
        )

        if abandoned_cart is None:
            raise ValueError(
                "Shopping cart could not be abandoned."
            )

        return abandoned_cart
