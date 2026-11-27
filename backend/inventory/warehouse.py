
"""Warehouse management service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.inventory_repository import InventoryRepository


class WarehouseService:
    """Business operations for warehouse management."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InventoryRepository(db)

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def create_warehouse(
        self,
        data: dict[str, Any],
    ):
        """Create a new warehouse."""

        required_fields = (
            "warehouse_code",
            "name",
            "address_line1",
            "city",
            "state",
            "pincode",
        )

        for field in required_fields:
            value = data.get(field)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field} is required and cannot be empty."
                )

        try:
            warehouse = self.repository.create_warehouse(data)
            self._commit()
            return warehouse
        except Exception:
            self.db.rollback()
            raise

    def get_warehouse(self, warehouse_id: int):
        """Retrieve a warehouse by its ID."""

        if warehouse_id < 1:
            raise ValueError("Warehouse ID must be positive.")

        return self.repository.get_warehouse_by_id(warehouse_id)

    def get_warehouse_by_code(self, warehouse_code: str):
        """Retrieve a warehouse using its unique code."""

        if not warehouse_code.strip():
            raise ValueError("Warehouse code cannot be empty.")

        return self.repository.get_warehouse_by_code(
            warehouse_code.strip()
        )

    def list_warehouses(
        self,
        page: int = 1,
        page_size: int = 20,
        city: str | None = None,
        active_only: bool = True,
    ) -> dict[str, Any]:
        """Return warehouses with pagination."""

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
                if page_size > 0
                else 0
            ),
        }

    def update_warehouse(
        self,
        warehouse_id: int,
        data: dict[str, Any],
    ):
        """Update warehouse information."""

        if warehouse_id < 1:
            raise ValueError("Warehouse ID must be positive.")

        if not data:
            raise ValueError("No warehouse fields provided.")

        try:
            warehouse = self.repository.update_warehouse(
                warehouse_id,
                data,
            )

            if warehouse is None:
                self.db.rollback()
                return None

            self._commit()
            return warehouse

        except Exception:
            self.db.rollback()
            raise

    def deactivate_warehouse(self, warehouse_id: int):
        """Deactivate a warehouse without deleting its history."""

        if warehouse_id < 1:
            raise ValueError("Warehouse ID must be positive.")

        try:
            warehouse = self.repository.deactivate_warehouse(
                warehouse_id
            )

            if warehouse is None:
                self.db.rollback()
                return None

            self._commit()
            return warehouse

        except Exception:
            self.db.rollback()
            raise

    def initialize_stock(
        self,
        product_id: int,
        warehouse_id: int,
        quantity_on_hand: Any = 0,
        reorder_level: Any = 5,
    ):
        """Create an initial stock record for a product."""

        if product_id < 1 or warehouse_id < 1:
            raise ValueError(
                "Product ID and warehouse ID must be positive."
            )

        try:
            stock = self.repository.create_stock_record(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_on_hand=quantity_on_hand,
                reorder_level=reorder_level,
            )

            self._commit()
            return stock

        except Exception:
            self.db.rollback()
            raise

    def get_product_stock(self, product_id: int):
        """Get product stock across all warehouses."""

        if product_id < 1:
            raise ValueError("Product ID must be positive.")

        return self.repository.get_product_stock(product_id)

    def get_warehouse_stock(
        self,
        warehouse_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get paginated stock records for a warehouse."""

        if warehouse_id < 1:
            raise ValueError("Warehouse ID must be positive.")

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
            "total_pages": (
                (total + page_size - 1) // page_size
                if page_size > 0
                else 0
            ),
        }
