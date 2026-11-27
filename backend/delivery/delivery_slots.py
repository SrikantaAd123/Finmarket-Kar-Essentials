
"""Delivery slot management business logic."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.delivery import DeliverySlot
from backend.repositories.delivery_repository import DeliveryRepository


class DeliverySlotsMixin:
    """Business operations for delivery time slots."""

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

    def create_delivery_slot(
        self,
        data: Any,
    ) -> DeliverySlot:
        """Create a delivery time slot."""

        try:
            payload = self._data_dict(data)

            required_fields = {
                "delivery_date",
                "start_time",
                "end_time",
                "capacity",
            }

            missing_fields = required_fields - payload.keys()

            if missing_fields:
                raise ValueError(
                    "Missing delivery slot fields: "
                    + ", ".join(sorted(missing_fields))
                )

            delivery_date = payload["delivery_date"]
            start_time = payload["start_time"]
            end_time = payload["end_time"]
            capacity = payload["capacity"]

            if delivery_date < date.today():
                raise ValueError(
                    "Delivery slot date cannot be in the past."
                )

            if end_time <= start_time:
                raise ValueError(
                    "Delivery slot end time must be after start time."
                )

            if isinstance(capacity, bool) or capacity <= 0:
                raise ValueError(
                    "Delivery slot capacity must be greater than zero."
                )

            overlapping = self.db.scalars(
                select(DeliverySlot).where(
                    DeliverySlot.delivery_date == delivery_date,
                    DeliverySlot.is_active.is_(True),
                    DeliverySlot.start_time < end_time,
                    DeliverySlot.end_time > start_time,
                )
            ).first()

            if overlapping is not None:
                raise ValueError(
                    "Delivery slot overlaps an existing active slot."
                )

            slot = self.repository.create_delivery_slot(
                payload
            )

            self._commit()
            return slot

        except Exception:
            self._rollback()
            raise

    def get_delivery_slot(
        self,
        slot_id: int,
    ) -> DeliverySlot:
        """Retrieve a delivery slot by ID."""

        slot = self.repository.get_delivery_slot(slot_id)

        if slot is None:
            raise ValueError("Delivery slot not found.")

        return slot

    def get_available_delivery_slots(
        self,
        delivery_date: date,
    ) -> list[DeliverySlot]:
        """Retrieve delivery slots with available capacity."""

        if delivery_date < date.today():
            raise ValueError(
                "Cannot retrieve slots for a past date."
            )

        return self.repository.get_available_delivery_slots(
            delivery_date
        )

    def update_delivery_slot(
        self,
        slot_id: int,
        data: Any,
    ) -> DeliverySlot:
        """Update delivery slot information."""

        try:
            slot = self.repository.get_delivery_slot(slot_id)

            if slot is None:
                raise ValueError("Delivery slot not found.")

            payload = self._data_dict(data)

            new_date = payload.get(
                "delivery_date",
                slot.delivery_date,
            )
            new_start = payload.get(
                "start_time",
                slot.start_time,
            )
            new_end = payload.get(
                "end_time",
                slot.end_time,
            )
            new_capacity = payload.get(
                "capacity",
                slot.capacity,
            )

            if new_date < date.today():
                raise ValueError(
                    "Delivery slot date cannot be in the past."
                )

            if new_end <= new_start:
                raise ValueError(
                    "Delivery slot end time must be after start time."
                )

            if (
                isinstance(new_capacity, bool)
                or new_capacity < slot.reserved_count
            ):
                raise ValueError(
                    "Capacity cannot be less than reserved count."
                )

            if new_capacity <= 0:
                raise ValueError(
                    "Delivery slot capacity must be greater than zero."
                )

            overlap = self.db.scalars(
                select(DeliverySlot).where(
                    DeliverySlot.id != slot_id,
                    DeliverySlot.delivery_date == new_date,
                    DeliverySlot.is_active.is_(True),
                    DeliverySlot.start_time < new_end,
                    DeliverySlot.end_time > new_start,
                )
            ).first()

            if overlap is not None:
                raise ValueError(
                    "Updated slot overlaps another active slot."
                )

            for field, value in payload.items():
                setattr(slot, field, value)

            self.db.add(slot)
            self.db.flush()
            self.db.refresh(slot)

            self._commit()
            return slot

        except Exception:
            self._rollback()
            raise


__all__ = ["DeliverySlotsMixin"]
