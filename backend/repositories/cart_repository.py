
"""Shopping cart repository for Finmarket Kart Essentials.

Supports registered customer carts and guest carts.
Does not commit transactions; transaction control belongs
to the service layer.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.cart import Cart, CartItem
from backend.models.catalog import Product


class CartRepository:
    """Database operations for shopping carts and cart items."""

    MAX_ITEM_QUANTITY = 100

    def __init__(self, db: Session) -> None:
        self.db = db

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def _cart_query(self):
        """Return a cart query with its products loaded."""

        return select(Cart).options(
            selectinload(Cart.items).selectinload(
                CartItem.product
            )
        )

    def _get_active_cart(
        self,
        customer_id: int | None = None,
        guest_token_hash: str | None = None,
    ) -> Cart | None:
        """Find an active cart belonging to a customer or guest."""

        if customer_id is not None:
            statement = select(Cart).where(
                Cart.customer_id == customer_id,
                Cart.status == "active",
            )
        elif guest_token_hash is not None:
            statement = select(Cart).where(
                Cart.guest_token_hash == guest_token_hash,
                Cart.status == "active",
            )
        else:
            raise ValueError(
                "A customer ID or guest token hash is required."
            )

        return self.db.scalars(statement).first()

    def _validate_quantity(self, quantity: int) -> None:
        """Validate a requested cart quantity."""

        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("Quantity must be an integer.")

        if quantity < 1:
            raise ValueError("Quantity must be at least 1.")

        if quantity > self.MAX_ITEM_QUANTITY:
            raise ValueError(
                f"Maximum allowed quantity is "
                f"{self.MAX_ITEM_QUANTITY}."
            )

    def _get_available_product(
        self,
        product_id: int,
    ) -> Product | None:
        """Retrieve a published and active product."""

        statement = select(Product).where(
            Product.id == product_id,
            Product.is_published.is_(True),
            Product.is_active.is_(True),
        )

        return self.db.scalars(statement).first()

    # =====================================================
    # CART CREATE / RETRIEVE
    # =====================================================

    def get_cart_by_id(
        self,
        cart_id: int,
    ) -> Cart | None:
        """Retrieve a cart with its items and products."""

        statement = (
            self._cart_query()
            .where(Cart.id == cart_id)
        )

        return self.db.scalars(statement).first()

    def get_customer_cart(
        self,
        customer_id: int,
    ) -> Cart | None:
        """Retrieve an active cart belonging to a customer."""

        statement = (
            self._cart_query()
            .where(
                Cart.customer_id == customer_id,
                Cart.status == "active",
            )
        )

        return self.db.scalars(statement).first()

    def get_guest_cart(
        self,
        guest_token_hash: str,
    ) -> Cart | None:
        """Retrieve an active guest cart using its token hash."""

        if not guest_token_hash:
            raise ValueError("Guest token hash is required.")

        statement = (
            self._cart_query()
            .where(
                Cart.guest_token_hash == guest_token_hash,
                Cart.status == "active",
            )
        )

        return self.db.scalars(statement).first()

    def get_or_create_customer_cart(
        self,
        customer_id: int,
    ) -> Cart:
        """Retrieve an active customer cart or create one."""

        cart = self.get_customer_cart(customer_id)

        if cart is not None:
            return cart

        cart = Cart(
            customer_id=customer_id,
            guest_token_hash=None,
            status="active",
            currency="INR",
        )

        self.db.add(cart)
        self.db.flush()
        self.db.refresh(cart)

        return cart

    def get_or_create_guest_cart(
        self,
        guest_token_hash: str,
    ) -> Cart:
        """Retrieve an active guest cart or create one."""

        if not guest_token_hash:
            raise ValueError("Guest token hash is required.")

        cart = self.get_guest_cart(guest_token_hash)

        if cart is not None:
            return cart

        cart = Cart(
            customer_id=None,
            guest_token_hash=guest_token_hash,
            status="active",
            currency="INR",
        )

        self.db.add(cart)
        self.db.flush()
        self.db.refresh(cart)

        return cart

    # =====================================================
    # CART OWNERSHIP
    # =====================================================

    def get_customer_owned_cart(
        self,
        cart_id: int,
        customer_id: int,
    ) -> Cart | None:
        """Retrieve a cart only when it belongs to the customer."""

        statement = (
            self._cart_query()
            .where(
                Cart.id == cart_id,
                Cart.customer_id == customer_id,
                Cart.status == "active",
            )
        )

        return self.db.scalars(statement).first()

    def get_guest_owned_cart(
        self,
        cart_id: int,
        guest_token_hash: str,
    ) -> Cart | None:
        """Retrieve a guest cart only when its token hash matches."""

        statement = (
            self._cart_query()
            .where(
                Cart.id == cart_id,
                Cart.guest_token_hash == guest_token_hash,
                Cart.status == "active",
            )
        )

        return self.db.scalars(statement).first()

    # =====================================================
    # ADD PRODUCT TO CART
    # =====================================================

    def add_item(
        self,
        cart_id: int,
        product_id: int,
        quantity: int = 1,
    ) -> CartItem:
        """Add a product or increase its existing quantity.

        The product price is read from the database, never
        accepted from the frontend.
        """

        self._validate_quantity(quantity)

        cart = self.get_cart_by_id(cart_id)

        if cart is None:
            raise ValueError("Cart does not exist.")

        if cart.status != "active":
            raise ValueError("This cart is not active.")

        product = self._get_available_product(product_id)

        if product is None:
            raise ValueError(
                "Product does not exist or is unavailable."
            )

        if cart.currency != product.currency:
            raise ValueError(
                "Product currency does not match cart currency."
            )

        statement = select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id,
        )

        existing_item = self.db.scalars(statement).first()

        if existing_item is not None:
            new_quantity = existing_item.quantity + quantity

            self._validate_quantity(new_quantity)

            existing_item.quantity = new_quantity

            # Keep the stored price aligned with the current
            # catalogue price while the item is in the cart.
            existing_item.unit_price = product.price

            self.db.add(existing_item)
            self.db.flush()
            self.db.refresh(existing_item)

            return existing_item

        cart_item = CartItem(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=product.price,
        )

        self.db.add(cart_item)
        self.db.flush()
        self.db.refresh(cart_item)

        return cart_item

    # =====================================================
    # CART ITEM RETRIEVAL
    # =====================================================

    def get_cart_item(
        self,
        cart_id: int,
        item_id: int,
    ) -> CartItem | None:
        """Retrieve an item belonging to a particular cart."""

        statement = (
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(
                CartItem.id == item_id,
                CartItem.cart_id == cart_id,
            )
        )

        return self.db.scalars(statement).first()

    def get_cart_items(
        self,
        cart_id: int,
    ) -> list[CartItem]:
        """Retrieve all items in a cart."""

        statement = (
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(CartItem.cart_id == cart_id)
            .order_by(CartItem.created_at)
        )

        return list(self.db.scalars(statement).all())

    # =====================================================
    # UPDATE CART ITEM
    # =====================================================

    def update_item_quantity(
        self,
        cart_id: int,
        item_id: int,
        quantity: int,
    ) -> CartItem | None:
        """Update the quantity of an existing cart item."""

        self._validate_quantity(quantity)

        item = self.get_cart_item(cart_id, item_id)

        if item is None:
            return None

        if self._get_available_product(item.product_id) is None:
            raise ValueError("This product is no longer available.")

        item.quantity = quantity

        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)

        return item

    # =====================================================
    # REMOVE CART ITEM
    # =====================================================

    def remove_item(
        self,
        cart_id: int,
        item_id: int,
    ) -> bool:
        """Remove an item from a particular cart."""

        item = self.get_cart_item(cart_id, item_id)

        if item is None:
            return False

        self.db.delete(item)
        self.db.flush()

        return True

    def remove_product(
        self,
        cart_id: int,
        product_id: int,
    ) -> bool:
        """Remove a product from a particular cart."""

        statement = select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id,
        )

        item = self.db.scalars(statement).first()

        if item is None:
            return False

        self.db.delete(item)
        self.db.flush()

        return True

    # =====================================================
    # CART SUMMARY
    # =====================================================

    def get_item_count(
        self,
        cart_id: int,
    ) -> int:
        """Return the total number of product units in a cart."""

        statement = select(
            func.coalesce(func.sum(CartItem.quantity), 0)
        ).where(
            CartItem.cart_id == cart_id
        )

        return int(self.db.scalar(statement) or 0)

    def get_unique_item_count(
        self,
        cart_id: int,
    ) -> int:
        """Return the number of distinct cart items."""

        statement = select(
            func.count(CartItem.id)
        ).where(
            CartItem.cart_id == cart_id
        )

        return int(self.db.scalar(statement) or 0)

    def get_cart_subtotal(
        self,
        cart_id: int,
    ) -> Decimal:
        """Calculate the subtotal using stored cart item prices."""

        statement = select(
            func.coalesce(
                func.sum(
                    CartItem.unit_price * CartItem.quantity
                ),
                0,
            )
        ).where(
            CartItem.cart_id == cart_id
        )

        result = self.db.scalar(statement)

        return Decimal(str(result or 0))

    def get_cart_summary(
        self,
        cart_id: int,
    ) -> dict[str, Decimal | int]:
        """Return basic cart totals."""

        return {
            "item_count": self.get_item_count(cart_id),
            "unique_item_count": self.get_unique_item_count(
                cart_id
            ),
            "subtotal": self.get_cart_subtotal(cart_id),
        }

    # =====================================================
    # CLEAR / CONVERT CART
    # =====================================================

    def clear_cart(
        self,
        cart_id: int,
    ) -> bool:
        """Remove all items from an active cart."""

        cart = self.db.get(Cart, cart_id)

        if cart is None:
            return False

        if cart.status != "active":
            raise ValueError("Only active carts can be cleared.")

        statement = select(CartItem).where(
            CartItem.cart_id == cart_id
        )

        items = self.db.scalars(statement).all()

        for item in items:
            self.db.delete(item)

        self.db.flush()

        return True

    def convert_cart(
        self,
        cart_id: int,
    ) -> Cart | None:
        """Mark a cart as converted after successful checkout."""

        cart = self.db.get(Cart, cart_id)

        if cart is None:
            return None

        if cart.status != "active":
            raise ValueError("Only active carts can be converted.")

        cart.status = "converted"

        self.db.add(cart)
        self.db.flush()
        self.db.refresh(cart)

        return cart

    # =====================================================
    # CART ABANDONMENT
    # =====================================================

    def abandon_cart(
        self,
        cart_id: int,
    ) -> Cart | None:
        """Mark an active cart as abandoned."""

        cart = self.db.get(Cart, cart_id)

        if cart is None:
            return None

        if cart.status != "active":
            raise ValueError("Only active carts can be abandoned.")

        cart.status = "abandoned"

        self.db.add(cart)
        self.db.flush()
        self.db.refresh(cart)

        return cart
