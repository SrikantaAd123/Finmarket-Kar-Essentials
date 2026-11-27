
"""Delivery management service for Finmarket Kart Essentials."""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy.orm import Session

from backend.delivery import (
    DeliveryAssignmentMixin,
    DeliverySlotsMixin,
    PincodeMixin,
    TrackingMixin,
)
from backend.models.delivery import (
    DeliveryPartner,
    Shipment,
)
from backend.models.order import Order
from backend.repositories.delivery_repository import DeliveryRepository


class DeliveryService(
    DeliveryAssignmentMixin,
    DeliverySlotsMixin,
    PincodeMixin,
    TrackingMixin,
):
    """Business logic layer for delivery management."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DeliveryRepository(db)

    # =====================================================
    # TRANSACTION HELPERS
    # =====================================================

    def _commit(self) -> None:
        """Commit the current database transaction."""
        self.db.commit()

    def _rollback(self) -> None:
        """Roll back the current database transaction."""
        self.db.rollback()

    @staticmethod
    def _data_dict(data: Any) -> dict[str, Any]:
        """Convert a Pydantic schema or dictionary into data."""

        if isinstance(data, dict):
            return data.copy()

        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)

        raise TypeError(
            "Invalid delivery data provided."
        )

    # =====================================================
    # DELIVERY PARTNER MANAGEMENT
    # =====================================================

    def create_delivery_partner(
        self,
        data: Any,
    ) -> DeliveryPartner:
        """Register a new delivery partner."""

        try:
            payload = self._data_dict(data)

            partner_code = payload.get("partner_code")

            if not isinstance(partner_code, str):
                raise ValueError(
                    "Delivery partner code is required."
                )

            partner_code = partner_code.strip()

            if not partner_code:
                raise ValueError(
                    "Delivery partner code cannot be empty."
                )

            payload["partner_code"] = partner_code

            existing = (
                self.repository.get_delivery_partner_by_code(
                    partner_code
                )
            )

            if existing is not None:
                raise ValueError(
                    "Delivery partner code already exists."
                )

            partner = self.repository.create_delivery_partner(
                payload
            )

            self._commit()
            return partner

        except Exception:
            self._rollback()
            raise

    def get_delivery_partner(
        self,
        partner_id: int,
    ) -> DeliveryPartner:
        """Retrieve a delivery partner."""

        partner = self.repository.get_delivery_partner(
            partner_id
        )

        if partner is None:
            raise ValueError(
                "Delivery partner not found."
            )

        return partner

    def get_available_delivery_partners(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DeliveryPartner], int]:
        """Retrieve available delivery partners."""

        return self.repository.get_available_delivery_partners(
            page=page,
            page_size=page_size,
        )

    def update_delivery_partner(
        self,
        partner_id: int,
        data: Any,
    ) -> DeliveryPartner:
        """Update delivery partner information."""

        try:
            partner = self.repository.get_delivery_partner(
                partner_id
            )

            if partner is None:
                raise ValueError(
                    "Delivery partner not found."
                )

            payload = self._data_dict(data)

            updated = self.repository.update_delivery_partner(
                partner_id,
                payload,
            )

            if updated is None:
                raise ValueError(
                    "Delivery partner not found."
                )

            self._commit()
            return updated

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # SHIPMENT MANAGEMENT
    # =====================================================

    def create_shipment(
        self,
        data: Any,
    ) -> Shipment:
        """Create a shipment for an existing order."""

        try:
            payload = self._data_dict(data)

            order_id = payload.get("order_id")

            if order_id is None:
                raise ValueError(
                    "Order ID is required."
                )

            order = self.db.get(
                Order,
                order_id,
            )

            if order is None:
                raise ValueError(
                    "Order not found."
                )

            existing = self.repository.get_shipment_by_order_id(
                order_id
            )

            if existing is not None:
                raise ValueError(
                    "A shipment already exists for this order."
                )

            payload["tracking_number"] = (
                "FMK" + secrets.token_hex(10).upper()
            )

            shipment = self.repository.create_shipment(
                payload
            )

            if payload.get("delivery_partner_id") is not None:
                shipment.status = "assigned"

                tracking_description = (
                    "Shipment created and delivery partner assigned."
                )
            else:
                tracking_description = (
                    "Shipment created successfully."
                )

            self.repository.add_tracking_event(
                shipment_id=shipment.id,
                status=shipment.status,
                description=tracking_description,
                updated_by="system",
            )

            self._commit()

            saved = self.repository.get_shipment_by_id(
                shipment.id
            )

            if saved is None:
                raise RuntimeError(
                    "Created shipment could not be retrieved."
                )

            return saved

        except Exception:
            self._rollback()
            raise

    def get_shipment(
        self,
        shipment_id: int,
    ) -> Shipment:
        """Retrieve shipment by ID."""

        shipment = self.repository.get_shipment_by_id(
            shipment_id
        )

        if shipment is None:
            raise ValueError(
                "Shipment not found."
            )

        return shipment

    def get_shipment_by_order_id(
        self,
        order_id: int,
    ) -> Shipment:
        """Retrieve shipment by order ID."""

        shipment = self.repository.get_shipment_by_order_id(
            order_id
        )

        if shipment is None:
            raise ValueError(
                "Shipment not found for this order."
            )

        return shipment

    def get_shipment_by_number(
        self,
        shipment_number: str,
    ) -> Shipment:
        """Retrieve shipment by shipment number."""

        shipment = self.repository.get_shipment_by_number(
            shipment_number
        )

        if shipment is None:
            raise ValueError(
                "Shipment not found."
            )

        return shipment

    def get_shipment_by_tracking_number(
        self,
        tracking_number: str,
    ) -> Shipment:
        """Retrieve shipment using tracking number."""

        shipment = (
            self.repository.get_shipment_by_tracking_number(
                tracking_number
            )
        )

        if shipment is None:
            raise ValueError(
                "Shipment not found."
            )

        return shipment

    def get_all_shipments(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        delivery_partner_id: int | None = None,
    ) -> tuple[list[Shipment], int]:
        """Retrieve paginated shipment records."""

        return self.repository.get_all_shipments(
            page=page,
            page_size=page_size,
            status=status,
            delivery_partner_id=delivery_partner_id,
        )

    # =====================================================
    # DELIVERY STATISTICS
    # =====================================================

    def count_shipments_by_status(
        self,
        status: str,
    ) -> int:
        """Count shipments by status."""

        return self.repository.count_shipments_by_status(
            status
        )

    def count_available_delivery_partners(self) -> int:
        """Count available delivery partners."""

        return (
            self.repository.count_available_delivery_partners()
        )


__all__ = ["DeliveryService"]
