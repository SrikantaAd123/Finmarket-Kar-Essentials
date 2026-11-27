
"""
Central registration of Finmarket Kart Essentials commerce models.

Importing this module registers all commerce models with
CommerceBase.metadata for SQLAlchemy and Alembic.
"""

# =========================================================
# CUSTOMER MODELS
# =========================================================

from backend.models.customer import (
    Customer,
    CustomerAddress,
)


# =========================================================
# CATALOG MODELS
# =========================================================

from backend.models.catalog import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductVariant,
)


# =========================================================
# CART MODELS
# =========================================================

from backend.models.cart import (
    Cart,
    CartItem,
)


# =========================================================
# ORDER MODELS
# =========================================================

from backend.models.order import (
    Order,
    OrderItem,
)

from backend.models.order_tracking import (
    OrderTracking,
)


# =========================================================
# PAYMENT MODELS
# =========================================================

from backend.models.payment import (
    PaymentTransaction,
    PaymentRefund,
)

from backend.models.payment_webhook import (
    PaymentWebhookEvent,
)


# =========================================================
# DELIVERY MODELS
# =========================================================

from backend.models.delivery import (
    DeliveryPartner,
    ServiceablePincode,
    DeliverySlot,
    Shipment,
    ShipmentTracking,
)


# =========================================================
# INVENTORY MODELS
# =========================================================

from backend.models.inventory import (
    Warehouse,
    InventoryStock,
    StockReservation,
    StockMovement,
)


# =========================================================
# NOTIFICATION MODELS
# =========================================================

from backend.models.notification import (
    Notification,
    NotificationPreference,
)


from backend.models.audit import AuditLog


from backend.models.order_return import (
    OrderReturn,
    OrderReturnItem,
)


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "Customer",
    "CustomerAddress",
    "Category",
    "Brand",
    "Product",
    "ProductImage",
    "ProductVariant",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderTracking",
    "PaymentTransaction",
    "PaymentRefund",
    "PaymentWebhookEvent",
    "DeliveryPartner",
    "ServiceablePincode",
    "DeliverySlot",
    "Shipment",
    "ShipmentTracking",
    "Warehouse",
    "InventoryStock",
    "StockReservation",
    "StockMovement",
    "Notification",
    "NotificationPreference",
    "AuditLog",

    "OrderReturn",
    "OrderReturnItem",
]