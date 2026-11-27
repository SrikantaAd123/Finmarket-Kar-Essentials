
"""Serviceable pincode management business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.delivery import ServiceablePincode
from backend.repositories.delivery_repository import DeliveryRepository


class PincodeMixin:
    """Business operations for serviceable delivery pincodes."""

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

    def create_serviceable_pincode(
        self,
        data: Any,
    ) -> ServiceablePincode:
        """Register a serviceable delivery pincode."""

        try:
            payload = self._data_dict(data)

            pincode = payload.get("pincode")

            if not isinstance(pincode, str) or not pincode.strip():
                raise ValueError("Pincode is required.")

            payload["pincode"] = pincode.strip()

            existing = self.db.scalars(
                select(ServiceablePincode).where(
                    ServiceablePincode.pincode == payload["pincode"]
                )
            ).first()

            if existing is not None:
                raise ValueError(
                    "Pincode is already registered."
                )

            record = self.repository.create_serviceable_pincode(
                payload
            )

            self._commit()
            return record

        except Exception:
            self._rollback()
            raise

    def check_pincode_serviceability(
        self,
        pincode: str,
    ) -> dict[str, Any]:
        """Check delivery availability for a pincode."""

        if not isinstance(pincode, str) or not pincode.strip():
            raise ValueError("A valid pincode is required.")

        result = self.repository.check_pincode_serviceability(
            pincode.strip()
        )

        result["message"] = (
            "Delivery is available for this pincode."
            if result["is_serviceable"]
            else "Sorry, delivery is not available for this pincode."
        )

        return result

    def get_serviceable_pincodes(
        self,
        page: int = 1,
        page_size: int = 50,
        city: str | None = None,
    ) -> tuple[list[ServiceablePincode], int]:
        """Retrieve active serviceable pincodes."""

        return self.repository.get_all_serviceable_pincodes(
            page=page,
            page_size=page_size,
            city=city,
        )

    def update_serviceable_pincode(
        self,
        pincode_id: int,
        data: Any,
    ) -> ServiceablePincode:
        """Update pincode configuration."""

        try:
            payload = self._data_dict(data)

            if "pincode" in payload:
                new_pincode = payload["pincode"]

                if (
                    not isinstance(new_pincode, str)
                    or not new_pincode.strip()
                ):
                    raise ValueError(
                        "Pincode cannot be empty."
                    )

                payload["pincode"] = new_pincode.strip()

                existing = self.db.scalars(
                    select(ServiceablePincode).where(
                        ServiceablePincode.pincode
                        == payload["pincode"],
                        ServiceablePincode.id != pincode_id,
                    )
                ).first()

                if existing is not None:
                    raise ValueError(
                        "Pincode is already registered."
                    )

            record = self.repository.update_serviceable_pincode(
                pincode_id,
                payload,
            )

            if record is None:
                raise ValueError(
                    "Serviceable pincode not found."
                )

            self._commit()
            return record

        except Exception:
            self._rollback()
            raise


__all__ = ["PincodeMixin"]
