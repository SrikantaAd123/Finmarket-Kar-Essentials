
"""Delivery partner assignment business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from backend.models.delivery import DeliveryPartner, Shipment
from backend.repositories.delivery_repository import DeliveryRepository


class DeliveryAssignmentMixin:
    """Business operations for delivery partner assignment."""

    # Attributes supplied by DeliveryService.
    db: Session
    repository: DeliveryRepository

    def _commit(self) -> None:
        """Commit the current database transaction."""
        raise NotImplementedError(
            "DeliveryService must implement _commit()."
        )

    def _rollback(self) -> None:
        """Roll back the current database transaction."""
        raise NotImplementedError(
            "DeliveryService must implement _rollback()."
        )

    def assign_delivery_partner(
        self,
        shipment_id: int,
        partner_id: int,
    ) -> Shipment:
        """Assign an available delivery partner to a shipment."""

        try:
            shipment = self.repository.get_shipment_by_id(
                shipment_id
            )

            if shipment is None:
                raise ValueError("Shipment not found.")

            if shipment.status not in {"created", "assigned"}:
                raise ValueError(
                    "Partner cannot be changed at this shipment status."
                )

            partner = self.repository.get_delivery_partner(
                partner_id
            )

            if (
                partner is None
                or not partner.is_active
                or not partner.is_available
            ):
                raise ValueError(
                    "Delivery partner is unavailable."
                )

            updated = self.repository.assign_delivery_partner(
                shipment_id,
                partner_id,
            )

            if updated is None:
                raise ValueError("Shipment not found.")

            self.repository.add_tracking_event(
                shipment_id=shipment_id,
                status="assigned",
                description="Delivery partner assigned successfully.",
                updated_by="system",
            )

            self._commit()

            result = self.repository.get_shipment_by_id(
                shipment_id
            )

            if result is None:
                raise RuntimeError(
                    "Assigned shipment could not be retrieved."
                )

            return result

        except Exception:
            self._rollback()
            raise

    def set_partner_availability(
        self,
        partner_id: int,
        is_available: bool,
    ) -> DeliveryPartner:
        """Change delivery partner availability."""

        try:
            partner = self.repository.get_delivery_partner(
                partner_id
            )

            if partner is None:
                raise ValueError("Delivery partner not found.")

            if is_available and not partner.is_active:
                raise ValueError(
                    "Inactive delivery partner cannot be made available."
                )

            updated = self.repository.set_partner_availability(
                partner_id,
                is_available,
            )

            if updated is None:
                raise ValueError("Delivery partner not found.")

            self._commit()
            return updated

        except Exception:
            self._rollback()
            raise


__all__ = ["DeliveryAssignmentMixin"]
