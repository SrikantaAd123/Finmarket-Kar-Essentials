
"""Service package for Finmarket Kart Essentials.

Services are loaded lazily to prevent circular imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.services.admin_customer_service import AdminCustomerService
    from backend.services.cart_service import CartService
    from backend.services.catalog_service import CatalogService
    from backend.services.customer_service import CustomerService
    from backend.services.delivery_service import DeliveryService
    from backend.services.inventory_service import InventoryService
    from backend.services.notification_service import NotificationService
    from backend.services.order_service import OrderService
    from backend.services.payment_service import PaymentService
    from backend.services.refund_service import RefundService


_EXPORTS = {
    "AdminCustomerService": "backend.services.admin_customer_service",
    "CartService": "backend.services.cart_service",
    "CatalogService": "backend.services.catalog_service",
    "CustomerService": "backend.services.customer_service",
    "DeliveryService": "backend.services.delivery_service",
    "InventoryService": "backend.services.inventory_service",
    "NotificationService": "backend.services.notification_service",
    "OrderService": "backend.services.order_service",
    "PaymentService": "backend.services.payment_service",
    "RefundService": "backend.services.refund_service",
}


def __getattr__(name: str) -> Any:
    """Load service classes only when requested."""

    if name not in _EXPORTS:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )

    from importlib import import_module

    module = import_module(_EXPORTS[name])
    service_class = getattr(module, name)

    globals()[name] = service_class

    return service_class


__all__ = [
    "AdminCustomerService",
    "CartService",
    "CatalogService",
    "CustomerService",
    "DeliveryService",
    "InventoryService",
    "NotificationService",
    "OrderService",
    "PaymentService",
    "RefundService",
]
