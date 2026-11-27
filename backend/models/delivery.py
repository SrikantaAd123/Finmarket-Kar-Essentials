
"""
Delivery management models for Finmarket Kart Essentials.

Contains:
- DeliveryPartner
- ServiceablePincode
- DeliverySlot
- Shipment
- ShipmentTracking
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.commerce_base import CommerceBase

from backend.models.mixins import (
    ActiveStatusMixin,
    PrimaryKeyMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    from backend.models.order import Order


# =========================================================
# DELIVERY PARTNER MODEL
# =========================================================

class DeliveryPartner(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
    ActiveStatusMixin,
):
    """Stores delivery company or delivery agent information."""

    __tablename__ = "delivery_partners"

    __table_args__ = (
        UniqueConstraint(
            "partner_code",
            name="uq_delivery_partners_code",
        ),
        Index(
            "ix_delivery_partners_phone",
            "phone",
        ),
        Index(
            "ix_delivery_partners_vehicle_number",
            "vehicle_number",
        ),
    )

    partner_code: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    vehicle_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    vehicle_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    rating: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )

    shipments: Mapped[list[Shipment]] = relationship(
        "Shipment",
        back_populates="delivery_partner",
    )

    def __repr__(self) -> str:
        return (
            f"<DeliveryPartner("
            f"id={self.id}, "
            f"name={self.full_name!r}"
            f")>"
        )


# =========================================================
# SERVICEABLE PINCODE MODEL
# =========================================================

class ServiceablePincode(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
    ActiveStatusMixin,
):
    """Stores postal areas supported by Finmarket deliveries."""

    __tablename__ = "serviceable_pincodes"

    __table_args__ = (
        UniqueConstraint(
            "pincode",
            name="uq_serviceable_pincodes_pincode",
        ),
        CheckConstraint(
            "delivery_fee >= 0",
            name="fee_nonnegative",
        ),
        CheckConstraint(
            "minimum_order_amount >= 0",
            name="minimum_nonnegative",
        ),
        Index(
            "ix_serviceable_pincodes_city",
            "city",
        ),
    )

    pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="India",
        server_default="India",
    )

    delivery_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    minimum_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    estimated_delivery_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    is_cod_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    def __repr__(self) -> str:
        return (
            f"<ServiceablePincode("
            f"id={self.id}, "
            f"pincode={self.pincode!r}"
            f")>"
        )


# =========================================================
# DELIVERY SLOT MODEL
# =========================================================

class DeliverySlot(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
    ActiveStatusMixin,
):
    """Stores available delivery time windows."""

    __tablename__ = "delivery_slots"

    __table_args__ = (
        CheckConstraint(
            "end_time > start_time",
            name="valid_time",
        ),
        CheckConstraint(
            "capacity > 0",
            name="capacity_positive",
        ),
        CheckConstraint(
            "reserved_count >= 0 AND reserved_count <= capacity",
            name="reserved_count_valid",
        ),
        Index(
            "ix_delivery_slots_delivery_date",
            "delivery_date",
        ),
    )

    delivery_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reserved_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    shipments: Mapped[list[Shipment]] = relationship(
        "Shipment",
        back_populates="delivery_slot",
    )

    def __repr__(self) -> str:
        return (
            f"<DeliverySlot("
            f"id={self.id}, "
            f"date={self.delivery_date}"
            f")>"
        )


# =========================================================
# SHIPMENT MODEL
# =========================================================

class Shipment(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Represents the physical delivery of an order."""

    __tablename__ = "shipments"

    __table_args__ = (
        UniqueConstraint(
            "shipment_number",
            name="uq_shipments_shipment_number",
        ),
        UniqueConstraint(
            "order_id",
            name="uq_shipments_order_id",
        ),
        CheckConstraint(
            "status IN ("
            "'created', 'assigned', 'picked_up', "
            "'in_transit', 'out_for_delivery', "
            "'delivered', 'failed', 'returned', 'cancelled'"
            ")",
            name="status",
        ),
        Index(
            "ix_shipments_delivery_partner_id",
            "delivery_partner_id",
        ),
        Index(
            "ix_shipments_status",
            "status",
        ),
    )

    shipment_number: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    delivery_partner_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "delivery_partners.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    delivery_slot_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "delivery_slots.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="created",
        server_default="created",
    )

    tracking_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    estimated_delivery_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    picked_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivery_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    delivery_proof_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -----------------------------------------------------
    # ORDER RELATIONSHIP
    # -----------------------------------------------------

    order: Mapped[Order] = relationship(
        "Order",
        back_populates="shipment",
    )

    # -----------------------------------------------------
    # DELIVERY PARTNER RELATIONSHIP
    # -----------------------------------------------------

    delivery_partner: Mapped[DeliveryPartner | None] = relationship(
        "DeliveryPartner",
        back_populates="shipments",
    )

    # -----------------------------------------------------
    # DELIVERY SLOT RELATIONSHIP
    # -----------------------------------------------------

    delivery_slot: Mapped[DeliverySlot | None] = relationship(
        "DeliverySlot",
        back_populates="shipments",
    )

    # -----------------------------------------------------
    # SHIPMENT TRACKING RELATIONSHIP
    # -----------------------------------------------------

    tracking_events: Mapped[list[ShipmentTracking]] = relationship(
        "ShipmentTracking",
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="ShipmentTracking.created_at",
    )

    def __repr__(self) -> str:
        return (
            f"<Shipment("
            f"id={self.id}, "
            f"number={self.shipment_number!r}, "
            f"status={self.status!r}"
            f")>"
        )


# =========================================================
# SHIPMENT TRACKING MODEL
# =========================================================

class ShipmentTracking(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Stores shipment movement and delivery tracking events."""

    __tablename__ = "shipment_tracking"

    __table_args__ = (
        Index(
            "ix_shipment_tracking_shipment_id",
            "shipment_id",
        ),
        Index(
            "ix_shipment_tracking_status",
            "status",
        ),
    )

    shipment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "shipments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    updated_by: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    shipment: Mapped[Shipment] = relationship(
        "Shipment",
        back_populates="tracking_events",
    )

    def __repr__(self) -> str:
        return (
            f"<ShipmentTracking("
            f"id={self.id}, "
            f"shipment_id={self.shipment_id}, "
            f"status={self.status!r}"
            f")>"
        )


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "DeliveryPartner",
    "ServiceablePincode",
    "DeliverySlot",
    "Shipment",
    "ShipmentTracking",
]
