
"""Customer repository for Finmarket Kart Essentials.

Handles customer profiles and customer-owned addresses.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models.customer import Customer, CustomerAddress


class CustomerRepository:
    """Database operations for customers and their addresses."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # =====================================================
    # CUSTOMER READ OPERATIONS
    # =====================================================

    def get_customer_by_id(
        self,
        customer_id: int,
    ) -> Customer | None:
        """Retrieve a customer using the primary key."""

        return self.db.get(Customer, customer_id)

    def get_customer_by_zitadel_sub(
        self,
        zitadel_sub: str,
    ) -> Customer | None:
        """Retrieve a customer using their ZITADEL subject."""

        statement = select(Customer).where(
            Customer.zitadel_sub == zitadel_sub
        )

        return self.db.scalars(statement).first()

    def get_customer_by_email(
        self,
        email: str,
    ) -> Customer | None:
        """Retrieve a customer using their email address."""

        statement = select(Customer).where(
            Customer.email == email.strip().lower()
        )

        return self.db.scalars(statement).first()

    # =====================================================
    # CUSTOMER CREATE OPERATIONS
    # =====================================================

    def create_customer(
        self,
        data: dict[str, Any],
    ) -> Customer:
        """Create a customer profile."""

        customer_data = data.copy()

        if customer_data.get("email"):
            customer_data["email"] = (
                customer_data["email"].strip().lower()
            )

        customer = Customer(**customer_data)

        self.db.add(customer)
        self.db.flush()
        self.db.refresh(customer)

        return customer

    def get_or_create_customer(
        self,
        zitadel_sub: str,
        defaults: dict[str, Any],
    ) -> tuple[Customer, bool]:
        """Find a customer by ZITADEL subject or create one.

        Returns:
            A tuple containing (customer, created).
        """

        customer = self.get_customer_by_zitadel_sub(
            zitadel_sub
        )

        if customer is not None:
            return customer, False

        customer_data = defaults.copy()
        customer_data["zitadel_sub"] = zitadel_sub

        customer = self.create_customer(customer_data)

        return customer, True

    # =====================================================
    # CUSTOMER UPDATE OPERATIONS
    # =====================================================

    def update_customer(
        self,
        customer_id: int,
        data: dict[str, Any],
    ) -> Customer | None:
        """Update customer profile information."""

        customer = self.get_customer_by_id(customer_id)

        if customer is None:
            return None

        update_data = data.copy()

        if update_data.get("email"):
            update_data["email"] = (
                update_data["email"].strip().lower()
            )

        # Do not allow identity or primary-key changes
        # through a normal profile update.
        protected_fields = {
            "id",
            "zitadel_sub",
            "created_at",
        }

        for field in protected_fields:
            update_data.pop(field, None)

        self._validate_customer_fields(update_data)

        for field, value in update_data.items():
            setattr(customer, field, value)

        self.db.add(customer)
        self.db.flush()
        self.db.refresh(customer)

        return customer

    def _validate_customer_fields(
        self,
        data: dict[str, Any],
    ) -> None:
        """Validate customer model column names."""

        valid_fields = {
            attribute.key
            for attribute in Customer.__mapper__.column_attrs
        }

        invalid_fields = set(data) - valid_fields

        if invalid_fields:
            raise ValueError(
                "Invalid customer fields: "
                + ", ".join(sorted(invalid_fields))
            )

    # =====================================================
    # ADDRESS READ OPERATIONS
    # =====================================================

    def get_address_by_id(
        self,
        address_id: int,
        customer_id: int,
    ) -> CustomerAddress | None:
        """Retrieve an address only if it belongs to the customer."""

        statement = select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer_id,
        )

        return self.db.scalars(statement).first()

    def get_customer_addresses(
        self,
        customer_id: int,
    ) -> list[CustomerAddress]:
        """Retrieve all addresses belonging to a customer."""

        statement = (
            select(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id
            )
            .order_by(
                CustomerAddress.is_default.desc(),
                CustomerAddress.id.desc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def get_default_address(
        self,
        customer_id: int,
    ) -> CustomerAddress | None:
        """Retrieve the customer's default delivery address."""

        statement = select(CustomerAddress).where(
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.is_default.is_(True),
        )

        return self.db.scalars(statement).first()

    # =====================================================
    # ADDRESS CREATE OPERATIONS
    # =====================================================

    def create_address(
        self,
        customer_id: int,
        data: dict[str, Any],
    ) -> CustomerAddress:
        """Create a delivery address for a customer."""

        customer = self.get_customer_by_id(customer_id)

        if customer is None:
            raise ValueError("Customer does not exist.")

        address_data = data.copy()

        make_default = address_data.pop(
            "is_default",
            False,
        )

        # The first saved address becomes the default.
        has_addresses = self.db.scalar(
            select(CustomerAddress.id)
            .where(
                CustomerAddress.customer_id == customer_id
            )
            .limit(1)
        )

        if not has_addresses:
            make_default = True

        if make_default:
            self._clear_default_addresses(customer_id)

        address = CustomerAddress(
            customer_id=customer_id,
            is_default=make_default,
            **address_data,
        )

        self.db.add(address)
        self.db.flush()
        self.db.refresh(address)

        return address

    # =====================================================
    # ADDRESS UPDATE OPERATIONS
    # =====================================================

    def update_address(
        self,
        address_id: int,
        customer_id: int,
        data: dict[str, Any],
    ) -> CustomerAddress | None:
        """Update an address owned by a specific customer."""

        address = self.get_address_by_id(
            address_id,
            customer_id,
        )

        if address is None:
            return None

        update_data = data.copy()

        make_default = update_data.pop(
            "is_default",
            None,
        )

        if make_default is True:
            self._clear_default_addresses(customer_id)
            address.is_default = True

        self._validate_address_fields(update_data)

        for field, value in update_data.items():
            setattr(address, field, value)

        self.db.add(address)
        self.db.flush()
        self.db.refresh(address)

        return address

    def set_default_address(
        self,
        address_id: int,
        customer_id: int,
    ) -> CustomerAddress | None:
        """Set an address as the customer's default address."""

        address = self.get_address_by_id(
            address_id,
            customer_id,
        )

        if address is None:
            return None

        self._clear_default_addresses(customer_id)

        address.is_default = True

        self.db.add(address)
        self.db.flush()
        self.db.refresh(address)

        return address

    def _clear_default_addresses(
        self,
        customer_id: int,
    ) -> None:
        """Remove the default flag from all customer addresses."""

        statement = (
            update(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_default.is_(True),
            )
            .values(is_default=False)
        )

        self.db.execute(statement)
        self.db.flush()

    def _validate_address_fields(
        self,
        data: dict[str, Any],
    ) -> None:
        """Validate customer address model column names."""

        valid_fields = {
            attribute.key
            for attribute in CustomerAddress.__mapper__.column_attrs
        }

        protected_fields = {
            "id",
            "customer_id",
            "created_at",
        }

        invalid_fields = (
            set(data) - valid_fields
        ) | (
            set(data) & protected_fields
        )

        if invalid_fields:
            raise ValueError(
                "Invalid or protected address fields: "
                + ", ".join(sorted(invalid_fields))
            )

    # =====================================================
    # ADDRESS DELETE OPERATIONS
    # =====================================================

    def delete_address(
        self,
        address_id: int,
        customer_id: int,
    ) -> bool:
        """Delete an address belonging to a customer."""

        address = self.get_address_by_id(
            address_id,
            customer_id,
        )

        if address is None:
            return False

        self.db.delete(address)
        self.db.flush()

        return True

    # =====================================================
    # CUSTOMER COUNTS
    # =====================================================

    def count_customer_addresses(
        self,
        customer_id: int,
    ) -> int:
        """Count addresses belonging to a customer."""

        from sqlalchemy import func

        statement = (
            select(func.count(CustomerAddress.id))
            .where(
                CustomerAddress.customer_id == customer_id
            )
        )

        return self.db.scalar(statement) or 0
