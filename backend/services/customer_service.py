
"""Customer service for Finmarket Kart Essentials.

Handles:
- Customer profile creation and retrieval
- ZITADEL customer synchronization
- Customer profile updates
- Customer address management
- Default address management
- Customer address validation

Database operations are delegated to CustomerRepository.
Transaction commits are managed by the caller.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.customer_repository import CustomerRepository


class CustomerService:
    """Business logic layer for customer management."""

    PROFILE_FIELDS = {
        "full_name",
        "email",
        "phone_number",
        "profile_image_url",
    }

    ADDRESS_FIELDS = {
        "address_type",
        "recipient_name",
        "phone_number",
        "address_line_1",
        "address_line_2",
        "landmark",
        "city",
        "state",
        "country",
        "postal_code",
        "is_default",
    }

    ADDRESS_TYPES = {
        "home",
        "work",
        "other",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CustomerRepository(db)

    # =====================================================
    # COMMON VALIDATION HELPERS
    # =====================================================

    @staticmethod
    def _model_data(
        data: Any,
        *,
        exclude_unset: bool = True,
    ) -> dict[str, Any]:
        """Convert a Pydantic model or dictionary into a dictionary."""

        if isinstance(data, dict):
            return data.copy()

        if hasattr(data, "model_dump"):
            return data.model_dump(
                exclude_unset=exclude_unset,
            )

        raise TypeError(
            "Input must be a dictionary or Pydantic model."
        )

    @staticmethod
    def _validate_id(
        value: int,
        field_name: str = "ID",
    ) -> None:
        """Validate a database identifier."""

        if isinstance(value, bool) or value <= 0:
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

    @staticmethod
    def _validate_required_text(
        value: Any,
        field_name: str,
    ) -> str:
        """Validate a required text field."""

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field_name} is required."
            )

        return value.strip()

    @staticmethod
    def _validate_email(email: str) -> str:
        """Normalize and validate an email address."""

        normalized = email.strip().lower()

        email_pattern = (
            r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
            r"@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
        )

        if not re.fullmatch(email_pattern, normalized):
            raise ValueError(
                "Please provide a valid email address."
            )

        if len(normalized) > 255:
            raise ValueError(
                "Email address cannot exceed 255 characters."
            )

        return normalized

    @staticmethod
    def _validate_phone(
        phone_number: str | None,
        *,
        required: bool = False,
    ) -> str | None:
        """Validate a phone number without converting it to an integer."""

        if phone_number is None:
            if required:
                raise ValueError("Phone number is required.")
            return None

        phone = phone_number.strip()

        if not phone:
            if required:
                raise ValueError("Phone number is required.")
            return None

        if len(phone) > 20:
            raise ValueError(
                "Phone number cannot exceed 20 characters."
            )

        if not re.fullmatch(r"\+?[0-9\s()-]+", phone):
            raise ValueError(
                "Phone number contains invalid characters."
            )

        digits = re.sub(r"\D", "", phone)

        if not 7 <= len(digits) <= 15:
            raise ValueError(
                "Phone number must contain between 7 and 15 digits."
            )

        return phone

    # =====================================================
    # CUSTOMER PROFILE OPERATIONS
    # =====================================================

    def create_customer(
        self,
        zitadel_sub: str,
        data: Any,
    ):
        """Create a customer profile linked to a ZITADEL subject."""

        subject = self._validate_required_text(
            zitadel_sub,
            "ZITADEL subject",
        )

        if len(subject) > 255:
            raise ValueError(
                "ZITADEL subject cannot exceed 255 characters."
            )

        customer_data = self._model_data(data)

        customer_data["full_name"] = (
            self._validate_required_text(
                customer_data.get("full_name"),
                "Full name",
            )
        )

        customer_data["email"] = self._validate_email(
            customer_data.get("email", "")
        )

        customer_data["phone_number"] = self._validate_phone(
            customer_data.get("phone_number")
        )

        customer_data.pop("id", None)
        customer_data.pop("zitadel_sub", None)
        customer_data.pop("created_at", None)
        customer_data.pop("updated_at", None)
        customer_data.pop("last_login_at", None)

        customer_data.setdefault("is_active", True)
        customer_data.setdefault("email_verified", False)
        customer_data.setdefault("phone_verified", False)

        existing = self.repository.get_customer_by_zitadel_sub(
            subject
        )

        if existing is not None:
            raise ValueError(
                "A customer profile already exists for this ZITADEL account."
            )

        existing_email = self.repository.get_customer_by_email(
            customer_data["email"]
        )

        if existing_email is not None:
            raise ValueError(
                "A customer with this email address already exists."
            )

        customer_data["zitadel_sub"] = subject

        return self.repository.create_customer(customer_data)

    def get_or_create_customer(
        self,
        zitadel_sub: str,
        defaults: Any,
    ):
        """Get an existing customer or create one from ZITADEL claims."""

        subject = self._validate_required_text(
            zitadel_sub,
            "ZITADEL subject",
        )

        if len(subject) > 255:
            raise ValueError(
                "ZITADEL subject cannot exceed 255 characters."
            )

        customer_data = self._model_data(defaults)

        customer_data["full_name"] = (
            self._validate_required_text(
                customer_data.get("full_name"),
                "Full name",
            )
        )

        customer_data["email"] = self._validate_email(
            customer_data.get("email", "")
        )

        customer_data["phone_number"] = self._validate_phone(
            customer_data.get("phone_number")
        )

        # Only the repository creates the customer.
        # This method preserves its (customer, created) return format.
        customer_data.pop("id", None)
        customer_data.pop("zitadel_sub", None)
        customer_data.pop("created_at", None)
        customer_data.pop("updated_at", None)
        customer_data.pop("last_login_at", None)

        customer_data.setdefault("is_active", True)
        customer_data.setdefault("email_verified", False)
        customer_data.setdefault("phone_verified", False)

        customer, created = self.repository.get_or_create_customer(
            zitadel_sub=subject,
            defaults=customer_data,
        )

        if not customer.is_active:
            raise ValueError(
                "This customer account is inactive."
            )

        return customer, created

    def get_customer(self, customer_id: int):
        """Retrieve a customer using the database ID."""

        self._validate_id(customer_id, "Customer ID")

        customer = self.repository.get_customer_by_id(
            customer_id
        )

        if customer is None:
            raise ValueError("Customer not found.")

        return customer

    def get_customer_by_zitadel_sub(
        self,
        zitadel_sub: str,
    ):
        """Retrieve a customer using the ZITADEL subject."""

        subject = self._validate_required_text(
            zitadel_sub,
            "ZITADEL subject",
        )

        customer = self.repository.get_customer_by_zitadel_sub(
            subject
        )

        if customer is None:
            raise ValueError("Customer not found.")

        return customer

    def get_customer_by_email(self, email: str):
        """Retrieve a customer using their email address."""

        normalized_email = self._validate_email(email)

        customer = self.repository.get_customer_by_email(
            normalized_email
        )

        if customer is None:
            raise ValueError("Customer not found.")

        return customer

    def get_customer_profile(self, customer_id: int):
        """Retrieve an active customer's profile."""

        customer = self.get_customer(customer_id)

        if not customer.is_active:
            raise ValueError("Customer account is inactive.")

        return customer

    def update_customer_profile(
        self,
        customer_id: int,
        data: Any,
    ):
        """Update editable customer profile fields."""

        self._validate_id(customer_id, "Customer ID")

        self.get_customer_profile(customer_id)

        update_data = self._model_data(data)

        if not update_data:
            raise ValueError(
                "No customer profile fields were provided."
            )

        invalid_fields = set(update_data) - self.PROFILE_FIELDS

        if invalid_fields:
            raise ValueError(
                "These customer fields cannot be updated through "
                "the profile operation: "
                + ", ".join(sorted(invalid_fields))
            )

        if "full_name" in update_data:
            update_data["full_name"] = (
                self._validate_required_text(
                    update_data["full_name"],
                    "Full name",
                )
            )

        if "email" in update_data:
            normalized_email = self._validate_email(
                update_data["email"]
            )

            existing = self.repository.get_customer_by_email(
                normalized_email
            )

            if (
                existing is not None
                and existing.id != customer_id
            ):
                raise ValueError(
                    "This email address is already used by another customer."
                )

            update_data["email"] = normalized_email

        if "phone_number" in update_data:
            update_data["phone_number"] = self._validate_phone(
                update_data["phone_number"]
            )

        if "profile_image_url" in update_data:
            image_url = update_data["profile_image_url"]

            if image_url is not None:
                image_url = self._validate_required_text(
                    image_url,
                    "Profile image URL",
                )

                if len(image_url) > 500:
                    raise ValueError(
                        "Profile image URL cannot exceed 500 characters."
                    )

                update_data["profile_image_url"] = image_url

        customer = self.repository.update_customer(
            customer_id,
            update_data,
        )

        if customer is None:
            raise ValueError("Customer not found.")

        return customer

    # =====================================================
    # CUSTOMER ADDRESS OPERATIONS
    # =====================================================

    def create_address(
        self,
        customer_id: int,
        data: Any,
    ):
        """Create a delivery address for a customer."""

        self._validate_id(customer_id, "Customer ID")

        self.get_customer_profile(customer_id)

        address_data = self._model_data(data)

        self._validate_address_data(
            address_data,
            creating=True,
        )

        return self.repository.create_address(
            customer_id,
            address_data,
        )

    def get_address(
        self,
        address_id: int,
        customer_id: int,
    ):
        """Retrieve an address owned by a customer."""

        self._validate_id(address_id, "Address ID")
        self._validate_id(customer_id, "Customer ID")

        self.get_customer_profile(customer_id)

        address = self.repository.get_address_by_id(
            address_id,
            customer_id,
        )

        if address is None or not address.is_active:
            raise ValueError("Customer address not found.")

        return address

    def get_customer_addresses(self, customer_id: int):
        """Retrieve all active addresses for a customer."""

        self._validate_id(customer_id, "Customer ID")

        self.get_customer_profile(customer_id)

        addresses = self.repository.get_customer_addresses(
            customer_id
        )

        return [
            address
            for address in addresses
            if address.is_active
        ]

    def get_default_address(self, customer_id: int):
        """Retrieve the customer's default active address."""

        self._validate_id(customer_id, "Customer ID")

        self.get_customer_profile(customer_id)

        address = self.repository.get_default_address(
            customer_id
        )

        if address is None or not address.is_active:
            return None

        return address

    def update_address(
        self,
        address_id: int,
        customer_id: int,
        data: Any,
    ):
        """Update an address belonging to the customer."""

        self._validate_id(address_id, "Address ID")
        self._validate_id(customer_id, "Customer ID")

        self.get_address(address_id, customer_id)

        address_data = self._model_data(data)

        if not address_data:
            raise ValueError(
                "No address fields were provided."
            )

        self._validate_address_data(
            address_data,
            creating=False,
        )

        address = self.repository.update_address(
            address_id,
            customer_id,
            address_data,
        )

        if address is None:
            raise ValueError("Customer address not found.")

        return address

    def set_default_address(
        self,
        address_id: int,
        customer_id: int,
    ):
        """Set an address as the customer's default address."""

        self._validate_id(address_id, "Address ID")
        self._validate_id(customer_id, "Customer ID")

        address = self.get_address(
            address_id,
            customer_id,
        )

        if not address.is_active:
            raise ValueError(
                "An inactive address cannot be made default."
            )

        result = self.repository.set_default_address(
            address_id,
            customer_id,
        )

        if result is None:
            raise ValueError("Customer address not found.")

        return result

    def delete_address(
        self,
        address_id: int,
        customer_id: int,
    ) -> bool:
        """Delete a customer-owned address.

        If the deleted address was the default, another active
        address is selected as the new default when available.
        """

        self._validate_id(address_id, "Address ID")
        self._validate_id(customer_id, "Customer ID")

        address = self.get_address(
            address_id,
            customer_id,
        )

        was_default = address.is_default

        deleted = self.repository.delete_address(
            address_id,
            customer_id,
        )

        if not deleted:
            raise ValueError("Customer address not found.")

        if was_default:
            remaining_addresses = (
                self.repository.get_customer_addresses(
                    customer_id
                )
            )

            next_address = next(
                (
                    item
                    for item in remaining_addresses
                    if item.is_active
                ),
                None,
            )

            if next_address is not None:
                self.repository.set_default_address(
                    next_address.id,
                    customer_id,
                )

        return True

    # =====================================================
    # ADDRESS VALIDATION
    # =====================================================

    def _validate_address_data(
        self,
        data: dict[str, Any],
        *,
        creating: bool,
    ) -> None:
        """Validate customer address fields."""

        invalid_fields = set(data) - self.ADDRESS_FIELDS

        if invalid_fields:
            raise ValueError(
                "Unsupported address fields: "
                + ", ".join(sorted(invalid_fields))
            )

        required_fields = {
            "recipient_name",
            "phone_number",
            "address_line_1",
            "city",
            "state",
            "postal_code",
        }

        if creating:
            missing_fields = {
                field
                for field in required_fields
                if field not in data
                or data[field] is None
                or (
                    isinstance(data[field], str)
                    and not data[field].strip()
                )
            }

            if missing_fields:
                raise ValueError(
                    "Required address fields are missing: "
                    + ", ".join(sorted(missing_fields))
                )

        for field in (
            "recipient_name",
            "address_line_1",
            "city",
            "state",
            "postal_code",
        ):
            if field in data:
                data[field] = self._validate_required_text(
                    data[field],
                    field.replace("_", " ").title(),
                )

        if "phone_number" in data:
            data["phone_number"] = self._validate_phone(
                data["phone_number"],
                required=True,
            )

        if "address_type" in data:
            address_type = self._validate_required_text(
                data["address_type"],
                "Address type",
            ).lower()

            if address_type not in self.ADDRESS_TYPES:
                raise ValueError(
                    "Address type must be home, work, or other."
                )

            data["address_type"] = address_type

        if "country" in data:
            data["country"] = self._validate_required_text(
                data["country"],
                "Country",
            )

        for field in (
            "address_line_2",
            "landmark",
        ):
            if field in data and data[field] is not None:
                data[field] = data[field].strip() or None

        if "postal_code" in data:
            postal_code = data["postal_code"]

            if len(postal_code) > 10:
                raise ValueError(
                    "Postal code cannot exceed 10 characters."
                )

            if not re.fullmatch(r"[A-Za-z0-9 -]+", postal_code):
                raise ValueError(
                    "Postal code contains invalid characters."
                )

        if (
            "is_default" in data
            and not isinstance(data["is_default"], bool)
        ):
            raise ValueError(
                "is_default must be a boolean value."
            )

    # =====================================================
    # CUSTOMER STATISTICS
    # =====================================================

    def get_customer_address_count(
        self,
        customer_id: int,
    ) -> int:
        """Return the number of saved addresses for a customer."""

        self._validate_id(customer_id, "Customer ID")

        self.get_customer_profile(customer_id)

        return self.repository.count_customer_addresses(
            customer_id
        )



