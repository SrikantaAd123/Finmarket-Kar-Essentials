
"""Inventory repository for Finmarket Kart Essentials.

Manages warehouses, inventory stock, stock reservations
and auditable stock movements.

Uses flush() rather than commit(). Transaction management
belongs to the service layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.inventory import (
    Warehouse,
    InventoryStock,
    StockReservation,
    StockMovement,
)


class InventoryRepository:
    """Database operations for inventory management."""

    RESERVATION_STATUSES = {
        "active",
        "confirmed",
        "released",
        "expired",
    }

    MOVEMENT_TYPES = {
        "purchase",
        "sale",
        "return",
        "adjustment",
        "transfer_in",
        "transfer_out",
        "damage",
        "reservation",
        "release",
    }

    MOVEMENT_DIRECTIONS = {
        "IN",
        "OUT",
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

    @staticmethod
    def _validate_quantity(
        quantity: Decimal,
    ) -> Decimal:
        value = Decimal(str(quantity))

        if not value.is_finite() or value <= 0:
            raise ValueError(
                "Quantity must be a positive finite number."
            )

        if value != value.quantize(Decimal("0.001")):
            raise ValueError(
                "Quantity cannot have more than three decimal places."
            )

        return value

    @staticmethod
    def _validate_nonnegative_quantity(
        quantity: Decimal,
    ) -> Decimal:
        value = Decimal(str(quantity))

        if not value.is_finite() or value < 0:
            raise ValueError(
                "Quantity cannot be negative or non-finite."
            )

        if value != value.quantize(Decimal("0.001")):
            raise ValueError(
                "Quantity cannot have more than three decimal places."
            )

        return value

    def _validate_reservation_status(
        self,
        status: str,
    ) -> None:
        if status not in self.RESERVATION_STATUSES:
            raise ValueError(
                f"Invalid reservation status: {status}"
            )

    def _validate_movement_type(
        self,
        movement_type: str,
    ) -> None:
        if movement_type not in self.MOVEMENT_TYPES:
            raise ValueError(
                f"Invalid movement type: {movement_type}"
            )

    def _validate_movement_direction(
        self,
        direction: str,
    ) -> None:
        if direction not in self.MOVEMENT_DIRECTIONS:
            raise ValueError(
                "Movement direction must be IN or OUT."
            )

    # =====================================================
    # WAREHOUSE OPERATIONS
    # =====================================================

    def create_warehouse(
        self,
        data: dict[str, Any],
    ) -> Warehouse:
        """Create a warehouse."""

        warehouse_data = data.copy()

        warehouse = Warehouse(**warehouse_data)

        self.db.add(warehouse)
        self.db.flush()
        self.db.refresh(warehouse)

        return warehouse

    def get_warehouse_by_id(
        self,
        warehouse_id: int,
    ) -> Warehouse | None:
        """Retrieve a warehouse by ID."""

        return self.db.get(
            Warehouse,
            warehouse_id,
        )

    def get_warehouse_by_code(
        self,
        warehouse_code: str,
    ) -> Warehouse | None:
        """Retrieve a warehouse using its unique code."""

        statement = select(Warehouse).where(
            Warehouse.warehouse_code == warehouse_code
        )

        return self.db.scalars(statement).first()

    def get_all_warehouses(
        self,
        page: int = 1,
        page_size: int = 20,
        city: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[Warehouse], int]:
        """Retrieve warehouses with pagination."""

        self._validate_pagination(page, page_size)

        statement = select(Warehouse)

        if active_only:
            statement = statement.where(
                Warehouse.is_active.is_(True)
            )

        if city:
            statement = statement.where(
                Warehouse.city == city
            )

        count_statement = (
            select(func.count(Warehouse.id))
            .select_from(Warehouse)
        )

        if active_only:
            count_statement = count_statement.where(
                Warehouse.is_active.is_(True)
            )

        if city:
            count_statement = count_statement.where(
                Warehouse.city == city
            )

        total = self.db.scalar(count_statement) or 0

        statement = (
            statement
            .order_by(Warehouse.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        warehouses = list(self.db.scalars(statement).all())

        return warehouses, int(total)

    def update_warehouse(
        self,
        warehouse_id: int,
        data: dict[str, Any],
    ) -> Warehouse | None:
        """Update warehouse information."""

        warehouse = self.get_warehouse_by_id(warehouse_id)

        if warehouse is None:
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
            for attribute in Warehouse.__mapper__.column_attrs
        }

        invalid = set(update_data) - valid_fields

        if invalid:
            raise ValueError(
                "Invalid warehouse fields: "
                + ", ".join(sorted(invalid))
            )

        for field, value in update_data.items():
            setattr(warehouse, field, value)

        self.db.add(warehouse)
        self.db.flush()
        self.db.refresh(warehouse)

        return warehouse

    def deactivate_warehouse(
        self,
        warehouse_id: int,
    ) -> Warehouse | None:
        """Deactivate a warehouse without deleting its records."""

        warehouse = self.get_warehouse_by_id(warehouse_id)

        if warehouse is None:
            return None

        warehouse.is_active = False

        self.db.add(warehouse)
        self.db.flush()
        self.db.refresh(warehouse)

        return warehouse

    # =====================================================
    # INVENTORY STOCK RETRIEVAL
    # =====================================================

    def get_stock_by_id(
        self,
        stock_id: int,
    ) -> InventoryStock | None:
        """Retrieve stock by its primary key."""

        statement = (
            select(InventoryStock)
            .options(
                selectinload(InventoryStock.product),
                selectinload(InventoryStock.warehouse),
            )
            .where(InventoryStock.id == stock_id)
        )

        return self.db.scalars(statement).first()

    def get_stock_by_product_and_warehouse(
        self,
        product_id: int,
        warehouse_id: int,
    ) -> InventoryStock | None:
        """Find stock for a product in a particular warehouse."""

        statement = (
            select(InventoryStock)
            .options(
                selectinload(InventoryStock.product),
                selectinload(InventoryStock.warehouse),
            )
            .where(
                InventoryStock.product_id == product_id,
                InventoryStock.warehouse_id == warehouse_id,
            )
        )

        return self.db.scalars(statement).first()

    def get_product_stock(
        self,
        product_id: int,
    ) -> list[InventoryStock]:
        """Retrieve stock for a product across all warehouses."""

        statement = (
            select(InventoryStock)
            .options(
                selectinload(InventoryStock.warehouse)
            )
            .where(
                InventoryStock.product_id == product_id
            )
            .order_by(InventoryStock.warehouse_id.asc())
        )

        return list(self.db.scalars(statement).all())

    def get_warehouse_stock(
        self,
        warehouse_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[InventoryStock], int]:
        """Retrieve all stock records in a warehouse."""

        self._validate_pagination(page, page_size)

        filters = [
            InventoryStock.warehouse_id == warehouse_id
        ]

        count_statement = (
            select(func.count(InventoryStock.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            select(InventoryStock)
            .options(
                selectinload(InventoryStock.product)
            )
            .where(*filters)
            .order_by(InventoryStock.product_id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        records = list(self.db.scalars(statement).all())

        return records, int(total)

    # =====================================================
    # CREATE AND INITIALIZE STOCK
    # =====================================================

    def create_stock_record(
        self,
        product_id: int,
        warehouse_id: int,
        quantity_on_hand: Decimal = Decimal("0.000"),
        reorder_level: Decimal = Decimal("5.000"),
    ) -> InventoryStock:
        """Create an inventory stock record."""

        on_hand = self._validate_nonnegative_quantity(
            quantity_on_hand
        )

        reorder = self._validate_nonnegative_quantity(
            reorder_level
        )

        existing = self.get_stock_by_product_and_warehouse(
            product_id,
            warehouse_id,
        )

        if existing is not None:
            raise ValueError(
                "Stock record already exists for this product "
                "and warehouse."
            )

        stock = InventoryStock(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity_on_hand=on_hand,
            quantity_reserved=Decimal("0.000"),
            reorder_level=reorder,
        )

        self.db.add(stock)
        self.db.flush()
        self.db.refresh(stock)

        return stock

    # =====================================================
    # STOCK ADJUSTMENT
    # =====================================================

    def adjust_stock(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: Decimal,
        direction: str,
        movement_type: str = "adjustment",
        reference_type: str | None = None,
        reference_id: str | None = None,
        notes: str | None = None,
        performed_by: str | None = None,
    ) -> InventoryStock:
        """Increase or decrease stock and create an audit movement.

        Uses row-level locking to protect the stock record
        during the adjustment.
        """

        amount = self._validate_quantity(quantity)

        self._validate_movement_direction(direction)
        self._validate_movement_type(movement_type)

        stock_statement = (
            select(InventoryStock)
            .where(
                InventoryStock.product_id == product_id,
                InventoryStock.warehouse_id == warehouse_id,
            )
            .with_for_update()
        )

        stock = self.db.scalars(stock_statement).first()

        if stock is None:
            raise ValueError(
                "Inventory stock record does not exist."
            )

        if direction == "IN":
            stock.quantity_on_hand += amount

        else:
            available = (
                stock.quantity_on_hand
                - stock.quantity_reserved
            )

            if amount > available:
                raise ValueError(
                    f"Insufficient available stock. "
                    f"Available: {available}"
                )

            stock.quantity_on_hand -= amount

        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            direction=direction,
            quantity=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            performed_by=performed_by,
        )

        self.db.add_all([stock, movement])
        self.db.flush()
        self.db.refresh(stock)

        return stock

    # =====================================================
    # STOCK RESERVATION
    # =====================================================

    def create_stock_reservation(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: Decimal,
        order_id: int | None = None,
        expires_at: datetime | None = None,
    ) -> StockReservation:
        """Reserve available stock for a customer order.

        Locks the inventory row and creates the reservation
        in the same transaction.
        """

        amount = self._validate_quantity(quantity)

        stock_statement = (
            select(InventoryStock)
            .where(
                InventoryStock.product_id == product_id,
                InventoryStock.warehouse_id == warehouse_id,
            )
            .with_for_update()
        )

        stock = self.db.scalars(stock_statement).first()

        if stock is None:
            raise ValueError(
                "Inventory stock record does not exist."
            )

        available = (
            stock.quantity_on_hand
            - stock.quantity_reserved
        )

        if amount > available:
            raise ValueError(
                f"Insufficient stock. Available: {available}"
            )

        stock.quantity_reserved += amount

        reservation = StockReservation(
            stock_id=stock.id,
            warehouse_id=warehouse_id,
            order_id=order_id,
            quantity=amount,
            status="active",
            expires_at=expires_at,
        )

        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type="reservation",
            direction="OUT",
            quantity=amount,
            reference_type="reservation",
            notes="Stock reserved for an order.",
        )

        self.db.add_all([
            stock,
            reservation,
            movement,
        ])

        self.db.flush()
        self.db.refresh(reservation)

        return reservation

    def get_reservation_by_id(
        self,
        reservation_id: int,
    ) -> StockReservation | None:
        """Retrieve a stock reservation by ID."""

        statement = (
            select(StockReservation)
            .options(
                selectinload(StockReservation.stock),
                selectinload(StockReservation.warehouse),
                selectinload(StockReservation.order),
            )
            .where(
                StockReservation.id == reservation_id
            )
        )

        return self.db.scalars(statement).first()

    def get_order_reservations(
        self,
        order_id: int,
    ) -> list[StockReservation]:
        """Retrieve all reservations for an order."""

        statement = (
            select(StockReservation)
            .where(
                StockReservation.order_id == order_id
            )
            .order_by(StockReservation.created_at.asc())
        )

        return list(self.db.scalars(statement).all())

    def get_active_reservations(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[StockReservation], int]:
        """Retrieve active stock reservations."""

        self._validate_pagination(page, page_size)

        filters = [
            StockReservation.status == "active"
        ]

        count_statement = (
            select(func.count(StockReservation.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            select(StockReservation)
            .options(
                selectinload(StockReservation.stock),
                selectinload(StockReservation.warehouse),
            )
            .where(*filters)
            .order_by(StockReservation.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        reservations = list(
            self.db.scalars(statement).all()
        )

        return reservations, int(total)

    # =====================================================
    # CONFIRM STOCK RESERVATION
    # =====================================================

    def confirm_stock_reservation(
        self,
        reservation_id: int,
    ) -> StockReservation | None:
        """Confirm a reservation after successful order payment.

        Deducts reserved quantity from both on-hand and reserved
        stock and records the completed sale.
        """

        reservation_statement = (
            select(StockReservation)
            .where(
                StockReservation.id == reservation_id
            )
            .with_for_update()
        )

        reservation = self.db.scalars(
            reservation_statement
        ).first()

        if reservation is None:
            return None

        if reservation.status == "confirmed":
            return reservation

        if reservation.status != "active":
            raise ValueError(
                "Only active reservations can be confirmed."
            )

        stock_statement = (
            select(InventoryStock)
            .where(
                InventoryStock.id == reservation.stock_id
            )
            .with_for_update()
        )

        stock = self.db.scalars(stock_statement).first()

        if stock is None:
            raise ValueError(
                "Inventory stock record does not exist."
            )

        if stock.quantity_reserved < reservation.quantity:
            raise ValueError(
                "Reserved stock quantity is inconsistent."
            )

        if stock.quantity_on_hand < reservation.quantity:
            raise ValueError(
                "On-hand stock is insufficient to confirm reservation."
            )

        stock.quantity_reserved -= reservation.quantity
        stock.quantity_on_hand -= reservation.quantity

        reservation.status = "confirmed"
        reservation.confirmed_at = datetime.now(timezone.utc)

        movement = StockMovement(
            product_id=stock.product_id,
            warehouse_id=stock.warehouse_id,
            movement_type="sale",
            direction="OUT",
            quantity=reservation.quantity,
            reference_type="reservation",
            reference_id=str(reservation.id),
            notes="Reserved stock confirmed for completed order.",
        )

        self.db.add_all([
            stock,
            reservation,
            movement,
        ])

        self.db.flush()
        self.db.refresh(reservation)

        return reservation

    # =====================================================
    # RELEASE OR EXPIRE RESERVATION
    # =====================================================

    def release_stock_reservation(
        self,
        reservation_id: int,
        expired: bool = False,
    ) -> StockReservation | None:
        """Release a reservation or mark it expired.

        Restores available stock by reducing quantity_reserved.
        It does not increase quantity_on_hand because the stock
        was never physically removed.
        """

        reservation_statement = (
            select(StockReservation)
            .where(
                StockReservation.id == reservation_id
            )
            .with_for_update()
        )

        reservation = self.db.scalars(
            reservation_statement
        ).first()

        if reservation is None:
            return None

        if reservation.status in {
            "released",
            "expired",
        }:
            return reservation

        if reservation.status != "active":
            raise ValueError(
                "Only active reservations can be released."
            )

        stock_statement = (
            select(InventoryStock)
            .where(
                InventoryStock.id == reservation.stock_id
            )
            .with_for_update()
        )

        stock = self.db.scalars(stock_statement).first()

        if stock is None:
            raise ValueError(
                "Inventory stock record does not exist."
            )

        if stock.quantity_reserved < reservation.quantity:
            raise ValueError(
                "Reserved stock quantity is inconsistent."
            )

        stock.quantity_reserved -= reservation.quantity

        reservation.status = (
            "expired" if expired else "released"
        )

        reservation.released_at = datetime.now(timezone.utc)

        movement = StockMovement(
            product_id=stock.product_id,
            warehouse_id=stock.warehouse_id,
            movement_type="release",
            direction="IN",
            quantity=reservation.quantity,
            reference_type="reservation",
            reference_id=str(reservation.id),
            notes=(
                "Stock reservation expired."
                if expired
                else "Stock reservation released."
            ),
        )

        self.db.add_all([
            stock,
            reservation,
            movement,
        ])

        self.db.flush()
        self.db.refresh(reservation)

        return reservation

    def expire_due_reservations(
        self,
        limit: int = 100,
    ) -> int:
        """Expire active reservations whose expiry time has passed.

        Intended to be called by a scheduled background job.
        Each reservation is released through the normal workflow.
        """

        if limit < 1 or limit > 500:
            raise ValueError(
                "Limit must be between 1 and 500."
            )

        now = datetime.now(timezone.utc)

        statement = (
            select(StockReservation.id)
            .where(
                StockReservation.status == "active",
                StockReservation.expires_at.is_not(None),
                StockReservation.expires_at <= now,
            )
            .order_by(StockReservation.expires_at.asc())
            .limit(limit)
        )

        reservation_ids = list(
            self.db.scalars(statement).all()
        )

        expired_count = 0

        for reservation_id in reservation_ids:
            reservation = self.release_stock_reservation(
                reservation_id,
                expired=True,
            )

            if reservation is not None and reservation.status == "expired":
                expired_count += 1

        return expired_count

    # =====================================================
    # STOCK MOVEMENT HISTORY
    # =====================================================

    def create_stock_movement(
        self,
        product_id: int,
        warehouse_id: int,
        movement_type: str,
        direction: str,
        quantity: Decimal,
        reference_type: str | None = None,
        reference_id: str | None = None,
        notes: str | None = None,
        performed_by: str | None = None,
    ) -> StockMovement:
        """Create a stock movement audit record.

        This method only creates the audit record.
        Use adjust_stock() when stock quantities must also change.
        """

        amount = self._validate_quantity(quantity)

        self._validate_movement_type(movement_type)
        self._validate_movement_direction(direction)

        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            direction=direction,
            quantity=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            performed_by=performed_by,
        )

        self.db.add(movement)
        self.db.flush()
        self.db.refresh(movement)

        return movement

    def get_stock_movements(
        self,
        product_id: int | None = None,
        warehouse_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[StockMovement], int]:
        """Retrieve filtered stock movement history."""

        self._validate_pagination(page, page_size)

        statement = (
            select(StockMovement)
            .options(
                selectinload(StockMovement.product),
                selectinload(StockMovement.warehouse),
            )
        )

        count_statement = select(
            func.count(StockMovement.id)
        )

        if product_id is not None:
            statement = statement.where(
                StockMovement.product_id == product_id
            )
            count_statement = count_statement.where(
                StockMovement.product_id == product_id
            )

        if warehouse_id is not None:
            statement = statement.where(
                StockMovement.warehouse_id == warehouse_id
            )
            count_statement = count_statement.where(
                StockMovement.warehouse_id == warehouse_id
            )

        total = self.db.scalar(count_statement) or 0

        statement = (
            statement
            .order_by(
                StockMovement.created_at.desc(),
                StockMovement.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        movements = list(self.db.scalars(statement).all())

        return movements, int(total)

    # =====================================================
    # LOW STOCK REPORTS
    # =====================================================

    def get_low_stock_records(
        self,
        warehouse_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[InventoryStock], int]:
        """Retrieve stock records at or below reorder level."""

        self._validate_pagination(page, page_size)

        filters = [
            (
                InventoryStock.quantity_on_hand
                - InventoryStock.quantity_reserved
            ) <= InventoryStock.reorder_level
        ]

        if warehouse_id is not None:
            filters.append(
                InventoryStock.warehouse_id == warehouse_id
            )

        count_statement = (
            select(func.count(InventoryStock.id))
            .where(*filters)
        )

        total = self.db.scalar(count_statement) or 0

        statement = (
            select(InventoryStock)
            .options(
                selectinload(InventoryStock.product),
                selectinload(InventoryStock.warehouse),
            )
            .where(*filters)
            .order_by(
                InventoryStock.quantity_on_hand.asc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        records = list(self.db.scalars(statement).all())

        return records, int(total)

    # =====================================================
    # INVENTORY SUMMARY
    # =====================================================

    def get_inventory_summary(
        self,
        warehouse_id: int | None = None,
    ) -> dict[str, Any]:
        """Calculate inventory quantities and stock counts."""

        filters = []

        if warehouse_id is not None:
            filters.append(
                InventoryStock.warehouse_id == warehouse_id
            )

        statement = select(
            func.count(InventoryStock.id),
            func.coalesce(
                func.sum(InventoryStock.quantity_on_hand),
                0,
            ),
            func.coalesce(
                func.sum(InventoryStock.quantity_reserved),
                0,
            ),
            func.coalesce(
                func.sum(
                    InventoryStock.quantity_on_hand
                    - InventoryStock.quantity_reserved
                ),
                0,
            ),
        ).where(*filters)

        result = self.db.execute(statement).one()

        stock_count = int(result[0] or 0)
        quantity_on_hand = Decimal(str(result[1] or 0))
        quantity_reserved = Decimal(str(result[2] or 0))
        quantity_available = Decimal(str(result[3] or 0))

        low_stock_query = select(
            func.count(InventoryStock.id)
        ).where(
            (
                InventoryStock.quantity_on_hand
                - InventoryStock.quantity_reserved
            ) <= InventoryStock.reorder_level
        )

        if warehouse_id is not None:
            low_stock_query = low_stock_query.where(
                InventoryStock.warehouse_id == warehouse_id
            )

        low_stock_count = int(
            self.db.scalar(low_stock_query) or 0
        )

        return {
            "stock_record_count": stock_count,
            "quantity_on_hand": quantity_on_hand,
            "quantity_reserved": quantity_reserved,
            "quantity_available": quantity_available,
            "low_stock_count": low_stock_count,
        }
