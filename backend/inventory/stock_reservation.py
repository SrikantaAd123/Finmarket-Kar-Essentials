
"""Stock reservation service."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.inventory_repository import InventoryRepository


class StockReservationService:
    """Business operations for reserving and releasing stock."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InventoryRepository(db)

    def reserve_stock(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: Decimal,
        order_id: int | None = None,
        expires_at: datetime | None = None,
    ):
        """Reserve available stock for an order."""

        if product_id < 1 or warehouse_id < 1:
            raise ValueError(
                "Product ID and warehouse ID must be positive."
            )

        if order_id is not None and order_id < 1:
            raise ValueError("Order ID must be positive.")

        if expires_at is not None:
            if expires_at.tzinfo is None:
                raise ValueError(
                    "Reservation expiry must be timezone-aware."
                )

            if expires_at <= datetime.now(timezone.utc):
                raise ValueError(
                    "Reservation expiry must be in the future."
                )

        try:
            reservation = self.repository.create_stock_reservation(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=Decimal(str(quantity)),
                order_id=order_id,
                expires_at=expires_at,
            )

            self.db.commit()
            return reservation

        except Exception:
            self.db.rollback()
            raise

    def get_reservation(self, reservation_id: int):
        """Retrieve a reservation by ID."""

        if reservation_id < 1:
            raise ValueError("Reservation ID must be positive.")

        return self.repository.get_reservation_by_id(
            reservation_id
        )

    def get_order_reservations(
        self,
        order_id: int,
    ):
        """Retrieve all stock reservations for an order."""

        if order_id < 1:
            raise ValueError("Order ID must be positive.")

        return self.repository.get_order_reservations(order_id)

    def list_active_reservations(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List active reservations with pagination."""

        reservations, total = self.repository.get_active_reservations(
            page=page,
            page_size=page_size,
        )

        return {
            "items": reservations,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (
                (total + page_size - 1) // page_size
                if page_size > 0
                else 0
            ),
        }

    def confirm_reservation(self, reservation_id: int):
        """Confirm a reservation after successful order processing."""

        if reservation_id < 1:
            raise ValueError("Reservation ID must be positive.")

        try:
            reservation = (
                self.repository.confirm_stock_reservation(
                    reservation_id
                )
            )

            if reservation is None:
                self.db.rollback()
                return None

            self.db.commit()
            return reservation

        except Exception:
            self.db.rollback()
            raise

    def release_reservation(
        self,
        reservation_id: int,
        expired: bool = False,
    ):
        """Release reserved stock after cancellation or expiry."""

        if reservation_id < 1:
            raise ValueError("Reservation ID must be positive.")

        try:
            reservation = (
                self.repository.release_stock_reservation(
                    reservation_id,
                    expired=expired,
                )
            )

            if reservation is None:
                self.db.rollback()
                return None

            self.db.commit()
            return reservation

        except Exception:
            self.db.rollback()
            raise

    def expire_due_reservations(
        self,
        limit: int = 100,
    ) -> int:
        """Expire reservations whose expiry time has passed."""

        try:
            expired_count = (
                self.repository.expire_due_reservations(
                    limit=limit,
                )
            )

            self.db.commit()
            return expired_count

        except Exception:
            self.db.rollback()
            raise
