
"""Stock movement and adjustment service."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.inventory_repository import InventoryRepository


class StockMovementService:
    """Business operations for inventory stock movements."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InventoryRepository(db)

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
    ):
        """Change stock and record the corresponding movement.

        direction:
            IN  - Increase stock.
            OUT - Decrease available stock.
        """

        if product_id < 1 or warehouse_id < 1:
            raise ValueError(
                "Product ID and warehouse ID must be positive."
            )

        if direction not in {"IN", "OUT"}:
            raise ValueError("Direction must be IN or OUT.")

        try:
            stock = self.repository.adjust_stock(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=Decimal(str(quantity)),
                direction=direction,
                movement_type=movement_type,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=notes,
                performed_by=performed_by,
            )

            self.db.commit()
            return stock

        except Exception:
            self.db.rollback()
            raise

    def receive_stock(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: Decimal,
        reference_type: str | None = "purchase",
        reference_id: str | None = None,
        notes: str | None = None,
        performed_by: str | None = None,
    ):
        """Record incoming stock, such as a supplier delivery."""

        return self.adjust_stock(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            direction="IN",
            movement_type="purchase",
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            performed_by=performed_by,
        )

    def remove_stock(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: Decimal,
        movement_type: str = "adjustment",
        reference_type: str | None = None,
        reference_id: str | None = None,
        notes: str | None = None,
        performed_by: str | None = None,
    ):
        """Record an outgoing stock adjustment."""

        if movement_type not in {
            "sale",
            "adjustment",
            "transfer_out",
            "damage",
        }:
            raise ValueError(
                "Invalid outgoing stock movement type."
            )

        return self.adjust_stock(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            direction="OUT",
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            performed_by=performed_by,
        )

    def record_movement(
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
    ):
        """Create an audit-only movement record.

        This does not modify InventoryStock.
        Use adjust_stock() when quantities must change.
        """

        try:
            movement = self.repository.create_stock_movement(
                product_id=product_id,
                warehouse_id=warehouse_id,
                movement_type=movement_type,
                direction=direction,
                quantity=Decimal(str(quantity)),
                reference_type=reference_type,
                reference_id=reference_id,
                notes=notes,
                performed_by=performed_by,
            )

            self.db.commit()
            return movement

        except Exception:
            self.db.rollback()
            raise

    def get_movement_history(
        self,
        product_id: int | None = None,
        warehouse_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Retrieve paginated stock movement history."""

        if product_id is not None and product_id < 1:
            raise ValueError("Product ID must be positive.")

        if warehouse_id is not None and warehouse_id < 1:
            raise ValueError("Warehouse ID must be positive.")

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
            "total_pages": (
                (total + page_size - 1) // page_size
                if page_size > 0
                else 0
            ),
        }
