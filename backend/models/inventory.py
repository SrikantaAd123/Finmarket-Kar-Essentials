
"""Inventory management models for Finmarket Kart Essentials."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
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
    from backend.models.catalog import Product
    from backend.models.order import Order


# =========================================================
# WAREHOUSE MODEL
# =========================================================

class Warehouse(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
    ActiveStatusMixin,
):
    """Physical warehouse or inventory storage location."""

    __tablename__ = "warehouses"

    __table_args__ = (
        UniqueConstraint(
            "warehouse_code",
            name="uq_warehouses_code",
        ),
        Index(
            "ix_warehouses_city",
            "city",
        ),
    )

    warehouse_code: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    address_line1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    address_line2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    pincode: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="India",
        server_default="India",
    )

    contact_person: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    contact_phone: Mapped[str | None] = mapped_column(
        String(25),
        nullable=True,
    )

    stock_records: Mapped[list[InventoryStock]] = relationship(
        "InventoryStock",
        back_populates="warehouse",
    )

    reservations: Mapped[list[StockReservation]] = relationship(
        "StockReservation",
        back_populates="warehouse",
    )

    movements: Mapped[list[StockMovement]] = relationship(
        "StockMovement",
        back_populates="warehouse",
    )

    def __repr__(self) -> str:
        return (
            f"<Warehouse("
            f"id={self.id}, "
            f"code={self.warehouse_code!r}"
            f")>"
        )


# =========================================================
# INVENTORY STOCK MODEL
# =========================================================

class InventoryStock(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Current stock quantities for a product in a warehouse."""

    __tablename__ = "inventory_stock"

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "warehouse_id",
            name="uq_inventory_stock_product_warehouse",
        ),
        CheckConstraint(
            "quantity_on_hand >= 0",
            name="on_hand_nonnegative",
        ),
        CheckConstraint(
            "quantity_reserved >= 0",
            name="reserved_nonnegative",
        ),
        CheckConstraint(
            "quantity_reserved <= quantity_on_hand",
            name="reserved_not_exceed_on_hand",
        ),
        CheckConstraint(
            "reorder_level >= 0",
            name="reorder_nonnegative",
        ),
        Index(
            "ix_inventory_stock_warehouse_id",
            "warehouse_id",
        ),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity_on_hand: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=Decimal("0.000"),
        server_default="0.000",
    )

    quantity_reserved: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=Decimal("0.000"),
        server_default="0.000",
    )

    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=Decimal("5.000"),
        server_default="5.000",
    )

    product: Mapped[Product] = relationship(
        "Product",
    )

    warehouse: Mapped[Warehouse] = relationship(
        "Warehouse",
        back_populates="stock_records",
    )

    @property
    def quantity_available(self) -> Decimal:
        """Calculate stock available for new orders."""
        return self.quantity_on_hand - self.quantity_reserved

    @property
    def is_low_stock(self) -> bool:
        """Check whether stock has reached its reorder level."""
        return self.quantity_available <= self.reorder_level

    def __repr__(self) -> str:
        return (
            f"<InventoryStock("
            f"id={self.id}, "
            f"product_id={self.product_id}, "
            f"available={self.quantity_available}"
            f")>"
        )


# =========================================================
# STOCK RESERVATION MODEL
# =========================================================

class StockReservation(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Stock held temporarily or committed for an order."""

    __tablename__ = "stock_reservations"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        ),
        CheckConstraint(
            "status IN ('active', 'confirmed', 'released', 'expired')",
            name="status",
        ),
        Index(
            "ix_stock_reservations_order_id",
            "order_id",
        ),
        Index(
            "ix_stock_reservations_status",
            "status",
        ),
        Index(
            "ix_stock_reservations_expires_at",
            "expires_at",
        ),
    )

    stock_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_stock.id", ondelete="RESTRICT"),
        nullable=False,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        server_default="active",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    stock: Mapped[InventoryStock] = relationship(
        "InventoryStock",
    )

    order: Mapped[Order | None] = relationship(
        "Order",
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )

    warehouse: Mapped[Warehouse] = relationship(
        "Warehouse",
        back_populates="reservations",
    )

    def __repr__(self) -> str:
        return (
            f"<StockReservation("
            f"id={self.id}, "
            f"quantity={self.quantity}, "
            f"status={self.status!r}"
            f")>"
        )


# =========================================================
# STOCK MOVEMENT MODEL
# =========================================================

class StockMovement(
    CommerceBase,
    PrimaryKeyMixin,
    TimestampMixin,
):
    """Auditable record of inventory quantity changes."""

    __tablename__ = "stock_movements"

    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('purchase', 'sale', 'return', "
            "'adjustment', 'transfer_in', 'transfer_out', "
            "'damage', 'reservation', 'release')",
            name="movement_type",
        ),
        CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        ),
        Index(
            "ix_stock_movements_product_id",
            "product_id",
        ),
        Index(
            "ix_stock_movements_warehouse_id",
            "warehouse_id",
        ),
        Index(
            "ix_stock_movements_created_at",
            "created_at",
        ),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )

    movement_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    # IN = stock received.
    # OUT = stock removed.

    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
    )

    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    reference_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    performed_by: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    product: Mapped[Product] = relationship(
        "Product",
    )

    warehouse: Mapped[Warehouse] = relationship(
        "Warehouse",
        back_populates="movements",
    )

    def __repr__(self) -> str:
        return (
            f"<StockMovement("
            f"id={self.id}, "
            f"type={self.movement_type!r}, "
            f"direction={self.direction!r}, "
            f"quantity={self.quantity}"
            f")>"
        )


__all__ = [
    "Warehouse",
    "InventoryStock",
    "StockReservation",
    "StockMovement",
]
