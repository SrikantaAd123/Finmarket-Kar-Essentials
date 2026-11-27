
"""Inventory service for Finmarket Kart Essentials.

Business logic for warehouses, stock management, reservations,
stock movements, low-stock reports and inventory summaries.

Repository methods use flush(). This service owns commit/rollback.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.repositories.inventory_repository import (
    InventoryRepository,
)

from backend.schemas.inventory import (
    WarehouseCreate,
    WarehouseUpdate,
    InventoryStockCreate,
    StockAdjustmentRequest,
    StockReservationCreate,
    StockMovementCreate,
)


class InventoryService:
    """Business logic for inventory management."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InventoryRepository(db)

    # =====================================================
    # TRANSACTION HELPERS
    # =====================================================

    def _commit(self) -> None:
        self.db.commit()

    def _rollback(self) -> None:
        self.db.rollback()

    @staticmethod
    def _validate_id(value: int, field_name: str) -> None:
        if isinstance(value, bool) or value <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")

    @staticmethod
    def _to_dict(data: Any) -> dict[str, Any]:
        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)
        if isinstance(data, dict):
            return data.copy()
        raise TypeError("Input must be a Pydantic model or dictionary.")

    # =====================================================
    # WAREHOUSE OPERATIONS
    # =====================================================

    def create_warehouse(
        self,
        data: WarehouseCreate,
    ):
        """Register a new warehouse."""

        try:
            payload = self._to_dict(data)

            code = payload["warehouse_code"].strip()

            existing = self.repository.get_warehouse_by_code(code)

            if existing is not None:
                raise ValueError(
                    f"Warehouse code '{code}' already exists."
                )

            warehouse = self.repository.create_warehouse(payload)

            self._commit()
            return warehouse

        except Exception:
            self._rollback()
            raise

    def get_warehouse(self, warehouse_id: int):
        """Retrieve a warehouse by ID."""

        self._validate_id(warehouse_id, "Warehouse ID")

        warehouse = self.repository.get_warehouse_by_id(
            warehouse_id
        )

        if warehouse is None:
            raise ValueError("Warehouse not found.")

        return warehouse

    def get_warehouses(
        self,
        page: int = 1,
        page_size: int = 20,
        city: str | None = None,
        active_only: bool = True,
    ) -> dict[str, Any]:
        """Return paginated warehouse records."""

        warehouses, total = self.repository.get_all_warehouses(
            page=page,
            page_size=page_size,
            city=city,
            active_only=active_only,
        )

        return {
            "items": warehouses,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (
                (total + page_size - 1) // page_size
                if page_size else 0
            ),
        }

    def update_warehouse(
        self,
        warehouse_id: int,
        data: WarehouseUpdate,
    ):
        """Update warehouse information."""

        self._validate_id(warehouse_id, "Warehouse ID")

        try:
            payload = self._to_dict(data)

            warehouse = self.repository.update_warehouse(
                warehouse_id,
                payload,
            )

            if warehouse is None:
                raise ValueError("Warehouse not found.")

            self._commit()
            return warehouse

        except Exception:
            self._rollback()
            raise

    def deactivate_warehouse(self, warehouse_id: int):
        """Deactivate a warehouse without deleting its records."""

        self._validate_id(warehouse_id, "Warehouse ID")

        try:
            warehouse = self.repository.deactivate_warehouse(
                warehouse_id
            )

            if warehouse is None:
                raise ValueError("Warehouse not found.")

            self._commit()
            return warehouse

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # INVENTORY STOCK OPERATIONS
    # =====================================================

    def initialize_stock(
        self,
        data: InventoryStockCreate,
    ):
        """Initialize stock for a product in a warehouse."""

        try:
            payload = self._to_dict(data)

            self._validate_id(
                payload["product_id"],
                "Product ID",
            )
            self._validate_id(
                payload["warehouse_id"],
                "Warehouse ID",
            )

            warehouse = self.repository.get_warehouse_by_id(
                payload["warehouse_id"]
            )

            if warehouse is None:
                raise ValueError("Warehouse not found.")

            if not warehouse.is_active:
                raise ValueError("Cannot initialize stock in an inactive warehouse.")

            stock = self.repository.create_stock_record(
                product_id=payload["product_id"],
                warehouse_id=payload["warehouse_id"],
                quantity_on_hand=payload.get(
                    "quantity_on_hand",
                    Decimal("0.000"),
                ),
                reorder_level=payload.get(
                    "reorder_level",
                    Decimal("5.000"),
                ),
            )

            self._commit()
            return stock

        except Exception:
            self._rollback()
            raise

    def get_stock(self, stock_id: int):
        """Retrieve stock by stock record ID."""

        self._validate_id(stock_id, "Stock ID")

        stock = self.repository.get_stock_by_id(stock_id)

        if stock is None:
            raise ValueError("Inventory stock record not found.")

        return stock

    def get_product_stock(self, product_id: int):
        """Get product stock across all warehouses."""

        self._validate_id(product_id, "Product ID")

        return self.repository.get_product_stock(product_id)

    def get_warehouse_stock(
        self,
        warehouse_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get paginated stock records for a warehouse."""

        self._validate_id(warehouse_id, "Warehouse ID")

        if self.repository.get_warehouse_by_id(warehouse_id) is None:
            raise ValueError("Warehouse not found.")

        records, total = self.repository.get_warehouse_stock(
            warehouse_id=warehouse_id,
            page=page,
            page_size=page_size,
        )

        return {
            "items": records,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # =====================================================
    # STOCK ADJUSTMENTS
    # =====================================================

    def adjust_stock(
        self,
        data: StockAdjustmentRequest,
        performed_by: str | None = None,
    ):
        """Increase or decrease available stock."""

        try:
            payload = self._to_dict(data)

            product_id = payload["product_id"]
            warehouse_id = payload["warehouse_id"]

            self._validate_id(product_id, "Product ID")
            self._validate_id(warehouse_id, "Warehouse ID")

            warehouse = self.repository.get_warehouse_by_id(
                warehouse_id
            )

            if warehouse is None:
                raise ValueError("Warehouse not found.")

            if not warehouse.is_active:
                raise ValueError("Cannot adjust stock in an inactive warehouse.")

            stock = self.repository.adjust_stock(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=payload["quantity"],
                direction=payload["direction"],
                movement_type="adjustment",
                reference_type="manual_adjustment",
                notes=payload["reason"],
                performed_by=performed_by,
            )

            self._commit()
            return stock

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # STOCK RESERVATIONS
    # =====================================================

    def reserve_stock(
        self,
        data: StockReservationCreate,
    ):
        """Reserve available stock for an order."""

        try:
            payload = self._to_dict(data)

            stock_id = payload["stock_id"]
            warehouse_id = payload["warehouse_id"]

            self._validate_id(stock_id, "Stock ID")
            self._validate_id(warehouse_id, "Warehouse ID")

            stock = self.repository.get_stock_by_id(stock_id)

            if stock is None:
                raise ValueError("Inventory stock record not found.")

            if stock.warehouse_id != warehouse_id:
                raise ValueError(
                    "The selected stock does not belong to this warehouse."
                )

            if not stock.warehouse.is_active:
                raise ValueError("Cannot reserve stock from an inactive warehouse.")

            expires_at = payload.get("expires_at")

            if expires_at is not None:
                if expires_at.tzinfo is None:
                    raise ValueError(
                        "Reservation expiry must include a timezone."
                    )

                if expires_at <= datetime.now(timezone.utc):
                    raise ValueError(
                        "Reservation expiry must be in the future."
                    )

            reservation = self.repository.create_stock_reservation(
                product_id=stock.product_id,
                warehouse_id=warehouse_id,
                quantity=payload["quantity"],
                order_id=payload.get("order_id"),
                expires_at=expires_at,
            )

            self._commit()
            return reservation

        except Exception:
            self._rollback()
            raise

    def get_reservation(self, reservation_id: int):
        """Retrieve a reservation."""

        self._validate_id(reservation_id, "Reservation ID")

        reservation = self.repository.get_reservation_by_id(
            reservation_id
        )

        if reservation is None:
            raise ValueError("Stock reservation not found.")

        return reservation

    def get_order_reservations(self, order_id: int):
        """Retrieve all reservations associated with an order."""

        self._validate_id(order_id, "Order ID")

        return self.repository.get_order_reservations(order_id)

    def get_active_reservations(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Retrieve active reservations."""

        reservations, total = self.repository.get_active_reservations(
            page=page,
            page_size=page_size,
        )

        return {
            "items": reservations,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def confirm_reservation(self, reservation_id: int):
        """Confirm a reservation after successful payment."""

        self._validate_id(reservation_id, "Reservation ID")

        try:
            reservation = self.repository.confirm_stock_reservation(
                reservation_id
            )

            if reservation is None:
                raise ValueError("Stock reservation not found.")

            self._commit()
            return reservation

        except Exception:
            self._rollback()
            raise

    def release_reservation(self, reservation_id: int):
        """Release an active stock reservation."""

        self._validate_id(reservation_id, "Reservation ID")

        try:
            reservation = self.repository.release_stock_reservation(
                reservation_id,
                expired=False,
            )

            if reservation is None:
                raise ValueError("Stock reservation not found.")

            self._commit()
            return reservation

        except Exception:
            self._rollback()
            raise

    def expire_due_reservations(self, limit: int = 100) -> int:
        """Expire reservations whose expiry time has passed."""

        try:
            count = self.repository.expire_due_reservations(
                limit=limit
            )

            self._commit()
            return count

        except Exception:
            self._rollback()
            raise

    # =====================================================
    # STOCK MOVEMENTS
    # =====================================================

    def create_stock_movement(
        self,
        data: StockMovementCreate,
        performed_by: str | None = None,
    ):
        """Create an audit movement record.

        This records movement history only.
        It does not modify stock quantities.
        """

        try:
            payload = self._to_dict(data)

            self._validate_id(
                payload["product_id"],
                "Product ID",
            )
            self._validate_id(
                payload["warehouse_id"],
                "Warehouse ID",
            )

            movement = self.repository.create_stock_movement(
                product_id=payload["product_id"],
                warehouse_id=payload["warehouse_id"],
                movement_type=payload["movement_type"],
                direction=payload["direction"],
                quantity=payload["quantity"],
                reference_type=payload.get("reference_type"),
                reference_id=payload.get("reference_id"),
                notes=payload.get("notes"),
                performed_by=performed_by,
            )

            self._commit()
            return movement

        except Exception:
            self._rollback()
            raise

    def get_stock_movements(
        self,
        product_id: int | None = None,
        warehouse_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Retrieve filtered stock movement history."""

        if product_id is not None:
            self._validate_id(product_id, "Product ID")

        if warehouse_id is not None:
            self._validate_id(warehouse_id, "Warehouse ID")

        movements, total = self.repository.get_stock_movements(
            product_id=product_id,
            warehouse_id=warehouse_id,
            page=page,
            page_size=page_size,
        )

        return {
            "items": movements,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # =====================================================
    # LOW STOCK REPORTS
    # =====================================================

    def get_low_stock(
        self,
        warehouse_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Retrieve products at or below their reorder level."""

        if warehouse_id is not None:
            self._validate_id(warehouse_id, "Warehouse ID")

        records, total = self.repository.get_low_stock_records(
            warehouse_id=warehouse_id,
            page=page,
            page_size=page_size,
        )

        items = [
            {
                "product_id": stock.product_id,
                "warehouse_id": stock.warehouse_id,
                "quantity_on_hand": stock.quantity_on_hand,
                "quantity_reserved": stock.quantity_reserved,
                "quantity_available": stock.quantity_available,
                "reorder_level": stock.reorder_level,
            }
            for stock in records
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # =====================================================
    # INVENTORY SUMMARY
    # =====================================================

    def get_inventory_summary(
        self,
        warehouse_id: int,
    ) -> dict[str, Any]:
        """Generate an inventory summary for a warehouse."""

        self._validate_id(warehouse_id, "Warehouse ID")

        warehouse = self.repository.get_warehouse_by_id(
            warehouse_id
        )

        if warehouse is None:
            raise ValueError("Warehouse not found.")

        summary = self.repository.get_inventory_summary(
            warehouse_id=warehouse_id
        )

        low_stock_records, _ = self.repository.get_low_stock_records(
            warehouse_id=warehouse_id,
            page=1,
            page_size=100,
        )

        low_stock_items = [
            {
                "product_id": stock.product_id,
                "warehouse_id": stock.warehouse_id,
                "quantity_on_hand": stock.quantity_on_hand,
                "quantity_reserved": stock.quantity_reserved,
                "quantity_available": stock.quantity_available,
                "reorder_level": stock.reorder_level,
            }
            for stock in low_stock_records
        ]

        return {
            "warehouse_id": warehouse_id,
            "total_products": summary["stock_record_count"],
            "low_stock_products": summary["low_stock_count"],
            "total_quantity_available": summary["quantity_available"],
            "low_stock_items": low_stock_items,
        }
