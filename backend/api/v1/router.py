
"""
Central router for API version 1.
"""

from fastapi import APIRouter

from .account import router as account_router
from .admin import router as admin_router
from .admin_customers import router as admin_customers_router
from .cart import router as cart_router
from .catalog import router as catalog_router
from .delivery import router as delivery_router
from .orders import router as orders_router
from .payments import router as payments_router


api_router = APIRouter()


# Register all version 1 API modules.

api_router.include_router(account_router)
api_router.include_router(admin_router)
api_router.include_router(admin_customers_router)
api_router.include_router(cart_router)
api_router.include_router(catalog_router)
api_router.include_router(delivery_router)
api_router.include_router(orders_router)
api_router.include_router(payments_router)


# Router alias
router = api_router
