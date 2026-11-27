"""
SQLAlchemy model registration for FINMARKET and WorkSphere.

All commerce model modules are imported here so string-based SQLAlchemy
relationship targets (OrderReturn, Shipment, PaymentTransaction, etc.)
are registered before mapper configuration.

WorkSphere and FINMARKET commerce models use separate declarative
metadata registries; importing them together does not merge their tables.
"""

# =========================================================
# WORKSPHERE MODELS
# =========================================================

from backend.models.user import User
from backend.models.auth_session import AuthSession
from backend.models.project import Project
from backend.models.task import Task
from backend.models.activity import Activity

# =========================================================
# FINMARKET SUPPORTING MODELS
# =========================================================

from backend.models.audit import AuditLog

from backend.models.catalog import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductVariant,
)

from backend.models.customer import (
    Customer,
    CustomerAddress,
)

from backend.models.cart import (
    Cart,
    CartItem,
)

from backend.models.order import (
    Order,
    OrderItem,
)

from backend.models.order_return import (
    OrderReturn,
    OrderReturnItem,
)

from backend.models.order_tracking import (
    OrderTracking,
)

from backend.models.delivery import (
    DeliveryPartner,
    ServiceablePincode,
    DeliverySlot,
    Shipment,
    ShipmentTracking,
)

from backend.models.inventory import (
    Warehouse,
    InventoryStock,
    StockReservation,
    StockMovement,
)

from backend.models.payment import (
    PaymentTransaction,
    PaymentRefund,
)

from backend.models.payment_webhook import PaymentWebhookEvent

from backend.models.notification import (
    Notification,
    NotificationPreference,
)


__all__ = [
    # WorkSphere
    "User",
    "AuthSession",
    "Project",
    "Task",
    "Activity",

    # FINMARKET audit
    "AuditLog",

    # Catalogue
    "Category",
    "Brand",
    "Product",
    "ProductImage",
    "ProductVariant",

    # Customer and cart
    "Customer",
    "CustomerAddress",
    "Cart",
    "CartItem",

    # Orders and returns
    "Order",
    "OrderItem",
    "OrderReturn",
    "OrderReturnItem",
    "OrderTracking",

    # Delivery and shipment
    "DeliveryPartner",
    "ServiceablePincode",
    "DeliverySlot",
    "Shipment",
    "ShipmentTracking",

    # Inventory
    "Warehouse",
    "InventoryStock",
    "StockReservation",
    "StockMovement",

    # Payments
    "PaymentTransaction",
    "PaymentRefund",
    "PaymentWebhookEvent",

    # Notifications
    "Notification",
    "NotificationPreference",
]
