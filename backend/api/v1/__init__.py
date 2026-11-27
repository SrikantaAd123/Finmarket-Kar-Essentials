
"""
Version 1 API package for Finmarket Kart Essentials.

Exports all API routers and the central versioned router.
"""

# =========================================================
# ACCOUNT
# =========================================================

from .account import router as account_router

# =========================================================
# ADMIN
# =========================================================

from .admin import router as admin_router
from .admin_customers import router as admin_customers_router

# =========================================================
# CART
# =========================================================

from .cart import router as cart_router

# =========================================================
# CATALOG
# =========================================================

from .catalog import router as catalog_router

# =========================================================
# DELIVERY
# =========================================================

from .delivery import router as delivery_router

# =========================================================
# ORDERS
# =========================================================

from .orders import router as orders_router

# =========================================================
# PAYMENTS
# =========================================================

from .payments import router as payments_router

# =========================================================
# CENTRAL ROUTER
# =========================================================

from .router import api_router, router


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "api_router",
    "router",
    "account_router",
    "admin_router",
    "admin_customers_router",
    "cart_router",
    "catalog_router",
    "delivery_router",
    "orders_router",
    "payments_router",
]
