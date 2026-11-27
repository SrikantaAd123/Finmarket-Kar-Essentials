
"""Pydantic schema package for Finmarket Kart Essentials."""

# =========================================================
# COMMON SCHEMAS
# =========================================================

from backend.schemas.common import (
    BaseSchema,
    TimestampSchema,
    IDSchema,
    PaginationParams,
    PaginationMetadata,
    PaginatedResponse,
    MessageResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
)


# =========================================================
# CATALOG SCHEMAS
# =========================================================

from backend.schemas.catalog import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    ProductImageCreate,
    ProductImageResponse,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductFilter,
)


# =========================================================
# CUSTOMER SCHEMAS
# =========================================================

from backend.schemas.customer import (
    CustomerProfileUpdate,
    CustomerProfileResponse,
    CustomerAddressCreate,
    CustomerAddressUpdate,
    CustomerAddressResponse,
    CustomerAddressListResponse,
)


# =========================================================
# CART SCHEMAS
# =========================================================

from backend.schemas.cart import (
    AddToCartRequest,
    UpdateCartItemRequest,
    RemoveCartItemRequest,
    CartProductSummary,
    CartItemResponse,
    CartResponse,
    CartSummaryResponse,
    CartOperationResponse,
)


# =========================================================
# ORDER SCHEMAS
# =========================================================

from backend.schemas.order import (
    OrderStatus,
    PaymentStatus as OrderPaymentStatus,
    PaymentMethod as OrderPaymentMethod,
    OrderCheckoutRequest,
    OrderItemResponse,
    OrderAddressResponse,
    OrderTrackingResponse,
    OrderResponse,
    OrderListResponse,
    OrderCancellationRequest,
    OrderCancellationResponse,
)


# =========================================================
# PAYMENT SCHEMAS
# =========================================================

from backend.schemas.payment import (
    PaymentMethod as TransactionPaymentMethod,
    PaymentStatus as TransactionPaymentStatus,
    RefundStatus,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    RazorpayVerificationRequest,
    PaymentVerificationResponse,
    PaymentTransactionResponse,
    PaymentRefundRequest,
    PaymentRefundResponse,
    PaymentHistoryResponse,
    PaymentStatusResponse,
)


# =========================================================
# DELIVERY SCHEMAS
# =========================================================

from backend.schemas.delivery import (
    ShipmentStatus,
    DeliveryPartnerCreate,
    DeliveryPartnerUpdate,
    DeliveryPartnerResponse,
    ServiceablePincodeCreate,
    ServiceablePincodeUpdate,
    ServiceablePincodeResponse,
    PincodeCheckRequest,
    PincodeCheckResponse,
    DeliverySlotCreate,
    DeliverySlotUpdate,
    DeliverySlotResponse,
    ShipmentCreate,
    ShipmentAssignmentRequest,
    ShipmentStatusUpdate,
    ShipmentResponse,
    ShipmentTrackingCreate,
    ShipmentTrackingResponse,
    ShipmentTrackingListResponse,
)


# =========================================================
# INVENTORY SCHEMAS
# =========================================================

from backend.schemas.inventory import (
    StockReservationStatus,
    StockMovementType,
    StockDirection,
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
    InventoryStockCreate,
    InventoryStockResponse,
    StockAdjustmentRequest,
    StockReservationCreate,
    StockReservationUpdate,
    StockReservationResponse,
    StockMovementCreate,
    StockMovementResponse,
    LowStockItemResponse,
    InventorySummaryResponse,
)


# =========================================================
# NOTIFICATION SCHEMAS
# =========================================================

from backend.schemas.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    NotificationCreate,
    NotificationUpdate,
    NotificationResponse,
    NotificationListResponse,
    NotificationPreferenceUpdate,
    NotificationPreferenceResponse,
    NotificationOperationResponse,
    NotificationRetryRequest,
    NotificationRetryResponse,
)


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    # Common
    "BaseSchema",
    "TimestampSchema",
    "IDSchema",
    "PaginationParams",
    "PaginationMetadata",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",

    # Catalog
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "BrandCreate",
    "BrandUpdate",
    "BrandResponse",
    "ProductImageCreate",
    "ProductImageResponse",
    "ProductVariantCreate",
    "ProductVariantResponse",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductFilter",

    # Customer
    "CustomerProfileUpdate",
    "CustomerProfileResponse",
    "CustomerAddressCreate",
    "CustomerAddressUpdate",
    "CustomerAddressResponse",
    "CustomerAddressListResponse",

    # Cart
    "AddToCartRequest",
    "UpdateCartItemRequest",
    "RemoveCartItemRequest",
    "CartProductSummary",
    "CartItemResponse",
    "CartResponse",
    "CartSummaryResponse",
    "CartOperationResponse",

    # Order
    "OrderStatus",
    "OrderPaymentStatus",
    "OrderPaymentMethod",
    "OrderCheckoutRequest",
    "OrderItemResponse",
    "OrderAddressResponse",
    "OrderTrackingResponse",
    "OrderResponse",
    "OrderListResponse",
    "OrderCancellationRequest",
    "OrderCancellationResponse",

    # Payment
    "TransactionPaymentMethod",
    "TransactionPaymentStatus",
    "RefundStatus",
    "PaymentInitiateRequest",
    "PaymentInitiateResponse",
    "RazorpayVerificationRequest",
    "PaymentVerificationResponse",
    "PaymentTransactionResponse",
    "PaymentRefundRequest",
    "PaymentRefundResponse",
    "PaymentHistoryResponse",
    "PaymentStatusResponse",

    # Delivery
    "ShipmentStatus",
    "DeliveryPartnerCreate",
    "DeliveryPartnerUpdate",
    "DeliveryPartnerResponse",
    "ServiceablePincodeCreate",
    "ServiceablePincodeUpdate",
    "ServiceablePincodeResponse",
    "PincodeCheckRequest",
    "PincodeCheckResponse",
    "DeliverySlotCreate",
    "DeliverySlotUpdate",
    "DeliverySlotResponse",
    "ShipmentCreate",
    "ShipmentAssignmentRequest",
    "ShipmentStatusUpdate",
    "ShipmentResponse",
    "ShipmentTrackingCreate",
    "ShipmentTrackingResponse",
    "ShipmentTrackingListResponse",

    # Inventory
    "StockReservationStatus",
    "StockMovementType",
    "StockDirection",
    "WarehouseCreate",
    "WarehouseUpdate",
    "WarehouseResponse",
    "InventoryStockCreate",
    "InventoryStockResponse",
    "StockAdjustmentRequest",
    "StockReservationCreate",
    "StockReservationUpdate",
    "StockReservationResponse",
    "StockMovementCreate",
    "StockMovementResponse",
    "LowStockItemResponse",
    "InventorySummaryResponse",

    # Notifications
    "NotificationChannel",
    "NotificationStatus",
    "NotificationType",
    "NotificationCreate",
    "NotificationUpdate",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationPreferenceUpdate",
    "NotificationPreferenceResponse",
    "NotificationOperationResponse",
    "NotificationRetryRequest",
    "NotificationRetryResponse",
]
