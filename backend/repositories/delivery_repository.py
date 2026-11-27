
"""Delivery repository for Finmarket Kart Essentials.

Manages delivery partners, serviceable pincodes, delivery slots,
shipments and shipment tracking events.

Uses flush() rather than commit(). Transaction control belongs
to the service layer.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from backend.models.delivery import (
    DeliveryPartner,
    ServiceablePincode,
    DeliverySlot,
    Shipment,
    ShipmentTracking,
)


class DeliveryRepository:
    """Database operations for delivery management."""

    SHIPMENT_STATUSES = {
        "created",
        "assigned",
        "picked_up",
        "in_transit",
        "out_for_delivery",
        "delivered",
        "failed",
        "returned",
        "cancelled",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    # =====================================================
    # VALIDATION HELPERS
    # =====================================================

    @staticmethod
    def _validate_pagination(
        page: int,
        page_size: int,
    ) -> None:
        if isinstance(page, bool) or page < 1:
            raise ValueError("Page must be at least 1.")

        if isinstance(page_size, bool) or page_size < 1:
            raise ValueError("Page size must be at least 1.")

        if page_size > 100:
            raise ValueError(
                "Page size cannot exceed 100."
            )

    def _validate_shipment_status(
        self,
        status: str,
    ) -> None:
        if status not in self.SHIPMENT_STATUSES:
            raise ValueError(
                f"Invalid shipment status: {status}"
            )

    # =====================================================
    # INTERNAL SHIPMENT QUERY
    # =====================================================

    def _shipment_query(self):
        """Load shipment relationships and tracking events."""

        return select(Shipment).options(
            selectinload(Shipment.order),
            selectinload(Shipment.delivery_partner),
            selectinload(Shipment.delivery_slot),
            selectinload(Shipment.tracking_events),
        )

    # =====================================================
    # DELIVERY PARTNER OPERATIONS
    # =====================================================

    def create_delivery_partner(
        self,
        data: dict[str, Any],
    ) -> DeliveryPartner:
        """Create a delivery partner."""

        partner_data = data.copy()
        partner = DeliveryPartner(**partner_data)

        self.db.add(partner)
        self.db.flush()
        self.db.refresh(partner)

        return partner

    def get_delivery_partner(
        self,
        partner_id: int,
    ) -> DeliveryPartner | None:
        """Retrieve a delivery partner by ID."""

        return self.db.get(
            DeliveryPartner,
            partner_id,
        )

    def get_delivery_partner_by_code(
        self,
        partner_code: str,
    ) -> DeliveryPartner | None:
        """Retrieve a partner using its unique partner code."""

        statement = select(DeliveryPartner).where(
            DeliveryPartner.partner_code == partner_code
        )

        return self.db.scalars(statement).first()

    def get_available_delivery_partners(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DeliveryPartner], int]:
        """Retrieve active and available delivery partners."""

        self._validate_pagination(page, page_size)

        filters: list[ColumnElement[bool]] = [
            DeliveryPartner.is_active.is_(True),
            DeliveryPartner.is_available.is_(True),
        ]

        count_statement = (
            select(func.count(DeliveryPartner.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            select(DeliveryPartner)
            .where(*filters)
            .order_by(DeliveryPartner.full_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        partners = list(self.db.scalars(statement).all())

        return partners, int(total)

    def update_delivery_partner(
        self,
        partner_id: int,
        data: dict[str, Any],
    ) -> DeliveryPartner | None:
        """Update delivery partner information."""

        partner = self.get_delivery_partner(partner_id)

        if partner is None:
            return None

        update_data = data.copy()

        protected = {
            "id",
            "created_at",
        }

        for field in protected:
            update_data.pop(field, None)

        valid_fields = {
            attribute.key
            for attribute in DeliveryPartner.__mapper__.column_attrs
        }

        invalid = set(update_data) - valid_fields

        if invalid:
            raise ValueError(
                "Invalid delivery partner fields: "
                + ", ".join(sorted(invalid))
            )

        for field, value in update_data.items():
            setattr(partner, field, value)

        self.db.add(partner)
        self.db.flush()
        self.db.refresh(partner)

        return partner

    def set_partner_availability(
        self,
        partner_id: int,
        is_available: bool,
    ) -> DeliveryPartner | None:
        """Change delivery partner availability."""

        partner = self.get_delivery_partner(partner_id)

        if partner is None:
            return None

        partner.is_available = is_available

        self.db.add(partner)
        self.db.flush()
        self.db.refresh(partner)

        return partner

    # =====================================================
    # SERVICEABLE PINCODE OPERATIONS
    # =====================================================

    def create_serviceable_pincode(
        self,
        data: dict[str, Any],
    ) -> ServiceablePincode:
        """Add a serviceable delivery pincode."""

        pincode_data = data.copy()
        pincode = pincode_data.get("pincode")

        if not pincode:
            raise ValueError("Pincode is required.")

        pincode_data["pincode"] = str(pincode).strip()

        record = ServiceablePincode(**pincode_data)

        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)

        return record

    def get_serviceable_pincode(
        self,
        pincode: str,
    ) -> ServiceablePincode | None:
        """Find an active serviceable pincode."""

        statement = select(ServiceablePincode).where(
            ServiceablePincode.pincode == str(pincode).strip(),
            ServiceablePincode.is_active.is_(True),
        )

        return self.db.scalars(statement).first()

    def check_pincode_serviceability(
        self,
        pincode: str,
    ) -> dict[str, Any]:
        """Check whether a postal area is serviceable."""

        record = self.get_serviceable_pincode(pincode)

        if record is None:
            return {
                "is_serviceable": False,
                "pincode": str(pincode).strip(),
                "delivery_fee": Decimal("0.00"),
                "minimum_order_amount": Decimal("0.00"),
                "estimated_delivery_days": None,
                "is_cod_available": False,
            }

        return {
            "is_serviceable": True,
            "pincode": record.pincode,
            "city": record.city,
            "state": record.state,
            "country": record.country,
            "delivery_fee": record.delivery_fee,
            "minimum_order_amount": record.minimum_order_amount,
            "estimated_delivery_days": record.estimated_delivery_days,
            "is_cod_available": record.is_cod_available,
        }

    def get_all_serviceable_pincodes(
        self,
        page: int = 1,
        page_size: int = 50,
        city: str | None = None,
    ) -> tuple[list[ServiceablePincode], int]:
        """Retrieve serviceable pincodes."""

        self._validate_pagination(page, page_size)

        filters: list[ColumnElement[bool]] = [
            ServiceablePincode.is_active.is_(True)
        ]

        if city:
            filters.append(
                ServiceablePincode.city == city
            )

        count_statement = (
            select(func.count(ServiceablePincode.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            select(ServiceablePincode)
            .where(*filters)
            .order_by(ServiceablePincode.city.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        records = list(self.db.scalars(statement).all())

        return records, int(total)

    def update_serviceable_pincode(
        self,
        pincode_id: int,
        data: dict[str, Any],
    ) -> ServiceablePincode | None:
        """Update serviceable pincode information."""

        record = self.db.get(
            ServiceablePincode,
            pincode_id,
        )

        if record is None:
            return None

        update_data = data.copy()

        protected = {
            "id",
            "created_at",
        }

        for field in protected:
            update_data.pop(field, None)

        valid_fields = {
            attribute.key
            for attribute in ServiceablePincode.__mapper__.column_attrs
        }

        invalid = set(update_data) - valid_fields

        if invalid:
            raise ValueError(
                "Invalid pincode fields: "
                + ", ".join(sorted(invalid))
            )

        for field, value in update_data.items():
            setattr(record, field, value)

        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)

        return record

    # =====================================================
    # DELIVERY SLOT OPERATIONS
    # =====================================================

    def create_delivery_slot(
        self,
        data: dict[str, Any],
    ) -> DeliverySlot:
        """Create a delivery time slot."""

        slot = DeliverySlot(**data.copy())

        self.db.add(slot)
        self.db.flush()
        self.db.refresh(slot)

        return slot

    def get_delivery_slot(
        self,
        slot_id: int,
    ) -> DeliverySlot | None:
        """Retrieve a delivery slot by ID."""

        return self.db.get(
            DeliverySlot,
            slot_id,
        )

    def get_available_delivery_slots(
        self,
        delivery_date: date,
    ) -> list[DeliverySlot]:
        """Retrieve active slots with remaining capacity."""

        statement = (
            select(DeliverySlot)
            .where(
                DeliverySlot.delivery_date == delivery_date,
                DeliverySlot.is_active.is_(True),
                DeliverySlot.reserved_count < DeliverySlot.capacity,
            )
            .order_by(DeliverySlot.start_time.asc())
        )

        return list(self.db.scalars(statement).all())

    def reserve_delivery_slot(
        self,
        slot_id: int,
    ) -> DeliverySlot:
        """Atomically reserve one place in a delivery slot."""

        statement = (
            update(DeliverySlot)
            .where(
                DeliverySlot.id == slot_id,
                DeliverySlot.is_active.is_(True),
                DeliverySlot.reserved_count < DeliverySlot.capacity,
            )
            .values(
                reserved_count=DeliverySlot.reserved_count + 1
            )
        )

        result = cast(
            CursorResult[Any],
            self.db.execute(statement),
        )

        if result.rowcount != 1:
            raise ValueError(
                "Delivery slot does not exist, is inactive "
                "or has no remaining capacity."
            )

        self.db.flush()

        slot = self.get_delivery_slot(slot_id)

        if slot is None:
            raise RuntimeError(
                "Reserved delivery slot could not be retrieved."
            )

        return slot

    def release_delivery_slot(
        self,
        slot_id: int,
    ) -> DeliverySlot:
        """Release one previously reserved slot."""

        statement = (
            update(DeliverySlot)
            .where(
                DeliverySlot.id == slot_id,
                DeliverySlot.reserved_count > 0,
            )
            .values(
                reserved_count=DeliverySlot.reserved_count - 1
            )
        )

        result = cast(
            CursorResult[Any],
            self.db.execute(statement),
        )

        if result.rowcount != 1:
            raise ValueError(
                "Delivery slot does not exist or has no "
                "reservation to release."
            )

        self.db.flush()

        slot = self.get_delivery_slot(slot_id)

        if slot is None:
            raise RuntimeError(
                "Released delivery slot could not be retrieved."
            )

        return slot

    # =====================================================
    # SHIPMENT CREATION
    # =====================================================

    def create_shipment(
        self,
        data: dict[str, Any],
    ) -> Shipment:
        """Create a shipment for an order.

        A delivery slot is reserved atomically when supplied.
        The service layer should generate the shipment number.
        """

        shipment_data = data.copy()

        order_id = shipment_data.get("order_id")

        if order_id is None:
            raise ValueError("Order ID is required.")

        existing = self.get_shipment_by_order_id(order_id)

        if existing is not None:
            raise ValueError(
                "A shipment already exists for this order."
            )

        partner_id = shipment_data.get("delivery_partner_id")
        slot_id = shipment_data.get("delivery_slot_id")

        if partner_id is not None:
            partner = self.get_delivery_partner(partner_id)

            if (
                partner is None
                or not partner.is_active
                or not partner.is_available
            ):
                raise ValueError(
                    "Delivery partner is unavailable."
                )

        if slot_id is not None:
            self.reserve_delivery_slot(slot_id)

        shipment = Shipment(**shipment_data)

        self.db.add(shipment)
        self.db.flush()
        self.db.refresh(shipment)

        if partner_id is not None:
            partner = self.get_delivery_partner(partner_id)

            if partner is not None:
                partner.is_available = False
                self.db.add(partner)
                self.db.flush()

        return shipment

    # =====================================================
    # SHIPMENT RETRIEVAL
    # =====================================================

    def get_shipment_by_id(
        self,
        shipment_id: int,
    ) -> Shipment | None:
        """Retrieve a shipment with its relationships."""

        statement = (
            self._shipment_query()
            .where(Shipment.id == shipment_id)
        )

        return self.db.scalars(statement).first()

    def get_shipment_by_order_id(
        self,
        order_id: int,
    ) -> Shipment | None:
        """Retrieve the shipment associated with an order."""

        statement = (
            self._shipment_query()
            .where(Shipment.order_id == order_id)
        )

        return self.db.scalars(statement).first()

    def get_shipment_by_number(
        self,
        shipment_number: str,
    ) -> Shipment | None:
        """Retrieve a shipment using its unique shipment number."""

        statement = (
            self._shipment_query()
            .where(
                Shipment.shipment_number == shipment_number
            )
        )

        return self.db.scalars(statement).first()

    def get_shipment_by_tracking_number(
        self,
        tracking_number: str,
    ) -> Shipment | None:
        """Retrieve a shipment using its tracking number."""

        statement = (
            self._shipment_query()
            .where(
                Shipment.tracking_number == tracking_number
            )
        )

        return self.db.scalars(statement).first()

    def get_all_shipments(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        delivery_partner_id: int | None = None,
    ) -> tuple[list[Shipment], int]:
        """Retrieve filtered and paginated shipments."""

        self._validate_pagination(page, page_size)

        filters: list[ColumnElement[bool]] = []

        if status is not None:
            self._validate_shipment_status(status)
            filters.append(
                Shipment.status == status
            )

        if delivery_partner_id is not None:
            filters.append(
                Shipment.delivery_partner_id == delivery_partner_id
            )

        count_statement = (
            select(func.count(Shipment.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            self._shipment_query()
            .where(*filters)
            .order_by(
                Shipment.created_at.desc(),
                Shipment.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        shipments = list(self.db.scalars(statement).all())

        return shipments, int(total)

    # =====================================================
    # SHIPMENT ASSIGNMENT
    # =====================================================

    def assign_delivery_partner(
        self,
        shipment_id: int,
        partner_id: int,
    ) -> Shipment | None:
        """Assign an available delivery partner to a shipment."""

        shipment = self.get_shipment_by_id(shipment_id)

        if shipment is None:
            return None

        if shipment.status not in {
            "created",
            "assigned",
        }:
            raise ValueError(
                "Partner cannot be changed at this shipment status."
            )

        partner = self.get_delivery_partner(partner_id)

        if (
            partner is None
            or not partner.is_active
            or not partner.is_available
        ):
            raise ValueError(
                "Delivery partner is unavailable."
            )

        old_partner_id = shipment.delivery_partner_id

        if old_partner_id == partner_id:
            return shipment

        if old_partner_id is not None:
            old_partner = self.get_delivery_partner(
                old_partner_id
            )

            if old_partner is not None:
                old_partner.is_available = True
                self.db.add(old_partner)

        partner.is_available = False
        shipment.delivery_partner_id = partner_id
        shipment.status = "assigned"

        self.db.add_all([partner, shipment])
        self.db.flush()
        self.db.refresh(shipment)

        return shipment

    # =====================================================
    # SHIPMENT STATUS
    # =====================================================

    def update_shipment_status(
        self,
        shipment_id: int,
        status: str,
        failure_reason: str | None = None,
        delivery_proof_url: str | None = None,
    ) -> Shipment | None:
        """Update shipment status and relevant timestamps."""

        self._validate_shipment_status(status)

        shipment = self.db.get(
            Shipment,
            shipment_id,
        )

        if shipment is None:
            return None

        now = datetime.now(timezone.utc)

        shipment.status = status

        if status == "picked_up" and shipment.picked_up_at is None:
            shipment.picked_up_at = now

        if status == "delivered":
            shipment.delivered_at = now

            if delivery_proof_url is not None:
                shipment.delivery_proof_url = delivery_proof_url

        if status == "failed":
            shipment.failure_reason = failure_reason

        if status in {
            "delivered",
            "failed",
            "returned",
            "cancelled",
        }:
            if shipment.delivery_partner_id is not None:
                partner = self.get_delivery_partner(
                    shipment.delivery_partner_id
                )

                if partner is not None:
                    partner.is_available = True
                    self.db.add(partner)

        if (
            status == "cancelled"
            and shipment.delivery_slot_id is not None
        ):
            self.release_delivery_slot(
                shipment.delivery_slot_id
            )
            shipment.delivery_slot_id = None

        self.db.add(shipment)
        self.db.flush()
        self.db.refresh(shipment)

        return shipment

    # =====================================================
    # SHIPMENT TRACKING
    # =====================================================

    def add_tracking_event(
        self,
        shipment_id: int,
        status: str,
        description: str,
        location: str | None = None,
        updated_by: str | None = None,
        event_time: datetime | None = None,
    ) -> ShipmentTracking:
        """Create a shipment tracking event."""

        self._validate_shipment_status(status)

        shipment = self.db.get(
            Shipment,
            shipment_id,
        )

        if shipment is None:
            raise ValueError("Shipment does not exist.")

        event = ShipmentTracking(
            shipment_id=shipment_id,
            status=status,
            description=description,
            location=location,
            updated_by=updated_by,
            event_time=event_time or datetime.now(timezone.utc),
        )

        self.db.add(event)
        self.db.flush()
        self.db.refresh(event)

        return event

    def get_shipment_tracking(
        self,
        shipment_id: int,
    ) -> list[ShipmentTracking]:
        """Retrieve shipment tracking history."""

        statement = (
            select(ShipmentTracking)
            .where(
                ShipmentTracking.shipment_id == shipment_id
            )
            .order_by(
                ShipmentTracking.event_time.asc(),
                ShipmentTracking.id.asc(),
            )
        )

        return list(self.db.scalars(statement).all())

    # =====================================================
    # DELIVERY STATISTICS
    # =====================================================

    def count_shipments_by_status(
        self,
        status: str,
    ) -> int:
        """Count shipments by status."""

        self._validate_shipment_status(status)

        statement = select(
            func.count(Shipment.id)
        ).where(
            Shipment.status == status
        )

        return int(self.db.scalar(statement) or 0)

    def count_available_delivery_partners(self) -> int:
        """Count active and available delivery partners."""

        statement = select(
            func.count(DeliveryPartner.id)
        ).where(
            DeliveryPartner.is_active.is_(True),
            DeliveryPartner.is_available.is_(True),
        )

        return int(self.db.scalar(statement) or 0)
