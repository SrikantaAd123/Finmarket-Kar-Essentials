
"""Shipment status and tracking business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.models.delivery import Shipment, ShipmentTracking
from backend.repositories.delivery_repository import DeliveryRepository


class TrackingMixin:
    """Business operations for shipment status and tracking."""

    db: Session
    repository: DeliveryRepository

    SHIPMENT_TRANSITIONS = {
        "created": {"assigned", "cancelled"},
        "assigned": {"picked_up", "cancelled", "failed"},
        "picked_up": {"in_transit", "failed"},
        "in_transit": {"out_for_delivery", "failed", "returned"},
        "out_for_delivery": {"delivered", "failed", "returned"},
        "failed": {"assigned", "returned", "cancelled"},
        "delivered": set(),
        "returned": set(),
        "cancelled": set(),
    }

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

    @staticmethod
    def _data_dict(data: Any) -> dict[str, Any]:
        """Convert a Pydantic schema or dictionary into a dictionary."""

        if isinstance(data, dict):
            return data.copy()

        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)

        raise TypeError(
            "Input must be a dictionary or Pydantic model."
        )

    def update_shipment_status(
        self,
        shipment_id: int,
        status: str,
        description: str,
        location: str | None = None,
        updated_by: str | None = None,
        failure_reason: str | None = None,
        delivery_proof_url: str | None = None,
    ) -> Shipment:
        """Update shipment status and create a tracking event."""

        try:
            shipment = self.repository.get_shipment_by_id(
                shipment_id
            )

            if shipment is None:
                raise ValueError("Shipment not found.")

            allowed = self.SHIPMENT_TRANSITIONS.get(
                shipment.status,
                set(),
            )

            if status not in allowed:
                raise ValueError(
                    f"Cannot change shipment status from "
                    f"'{shipment.status}' to '{status}'."
                )

            if status == "failed" and not failure_reason:
                failure_reason = description

            updated = self.repository.update_shipment_status(
                shipment_id=shipment_id,
                status=status,
                failure_reason=failure_reason,
                delivery_proof_url=delivery_proof_url,
            )

            if updated is None:
                raise ValueError("Shipment not found.")

            self.repository.add_tracking_event(
                shipment_id=shipment_id,
                status=status,
                description=description,
                location=location,
                updated_by=updated_by,
            )

            self._commit()

            result = self.repository.get_shipment_by_id(
                shipment_id
            )

            if result is None:
                raise RuntimeError(
                    "Updated shipment could not be retrieved."
                )

            return result

        except Exception:
            self._rollback()
            raise

    def add_tracking_event(
        self,
        shipment_id: int,
        data: Any,
    ) -> ShipmentTracking:
        """Add a tracking event to a shipment."""

        try:
            shipment = self.repository.get_shipment_by_id(
                shipment_id
            )

            if shipment is None:
                raise ValueError("Shipment not found.")

            payload = self._data_dict(data)

            required_fields = {"status", "description"}
            missing_fields = required_fields - payload.keys()

            if missing_fields:
                raise ValueError(
                    "Missing tracking event fields: "
                    + ", ".join(sorted(missing_fields))
                )

            event = self.repository.add_tracking_event(
                shipment_id=shipment_id,
                status=payload["status"],
                description=payload["description"],
                location=payload.get("location"),
                updated_by=payload.get("updated_by"),
                event_time=payload.get("event_time"),
            )

            self._commit()
            return event

        except Exception:
            self._rollback()
            raise

    def get_shipment_tracking(
        self,
        shipment_id: int,
    ) -> list[ShipmentTracking]:
        """Retrieve tracking history for a shipment."""

        shipment = self.repository.get_shipment_by_id(
            shipment_id
        )

        if shipment is None:
            raise ValueError("Shipment not found.")

        return self.repository.get_shipment_tracking(
            shipment_id
        )


__all__ = ["TrackingMixin"]
