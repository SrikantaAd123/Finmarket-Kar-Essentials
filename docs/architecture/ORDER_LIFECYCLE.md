
# Finmarket Kart Essentials – Order Lifecycle

## 1. Introduction

The order lifecycle describes how customer orders are created, processed, tracked, cancelled, and completed in Finmarket Kart Essentials.

The backend uses FastAPI, SQLAlchemy, and MySQL to manage order-related operations.

The `OrderService` handles the business logic for:

- Customer checkout.
- Order creation.
- Shipping and billing address validation.
- Order item snapshots.
- Order total calculations.
- Customer order history.
- Order cancellation.
- Order status management.
- Order tracking.

Database operations are delegated to repositories.

## 2. Order Lifecycle Overview

The application supports the following order statuses:

```text
pending
   |
   v
confirmed
   |
   v
processing
   |
   v
packed
   |
   v
shipped
   |
   v
out_for_delivery
   |
   v
delivered
```

Additional supported outcomes include:

```text
pending / confirmed
       |
       v
   cancelled

Other applicable order states
       |
       v
    returned
```

The diagram illustrates the general business flow. It does not establish that every transition is automatically performed by the application.

## 3. Supported Order Statuses

The `OrderService.ORDER_STATUSES` collection defines these supported values:

| Status | Description |
| --- | --- |
| `pending` | Order has been created and is awaiting further processing |
| `confirmed` | Order has been confirmed |
| `processing` | Order is being prepared |
| `packed` | Order items have been packed |
| `shipped` | Order has been dispatched |
| `out_for_delivery` | Order is with the delivery process for final delivery |
| `delivered` | Order has been delivered |
| `cancelled` | Order has been cancelled |
| `returned` | Order has been returned |

The order status represents the business state of the order.

## 4. Step-by-Step Order Lifecycle

### 4.1 Customer Checkout

The customer initiates checkout through the customer orders API.

**HTTP Method:** `POST`

**Endpoint:** `/api/v1/orders/checkout`

The checkout request is handled by the order API and `OrderService`.

The service handles:

- Customer validation.
- Cart-related operations.
- Shipping address validation.
- Billing address validation.
- Order item snapshots.
- Order total calculations.
- Order creation.

The checkout request schema is `OrderCheckoutRequest`.

### 4.2 Order Creation

After checkout validation and order creation, the system stores the order information.

The order number is generated using the following format:

```text
FMK-{16 uppercase hexadecimal characters}
```

Example:

```text
FMK-A1B2C3D4E5F67890
```

The database unique constraint provides the final protection against duplicate order numbers.

### 4.3 Order Confirmation

After creation, an order can proceed through its supported business statuses.

The order service defines `pending` and `confirmed` as cancellable statuses.

The actual status update is performed through the order service.

### 4.4 Order Processing

After confirmation, the order can move through the preparation stages.

The supported processing statuses are:

- `processing`
- `packed`

These statuses represent preparation and packing activities.

### 4.5 Order Shipment

The order can move to the `shipped` status after dispatch.

Delivery management is handled separately through the delivery service and shipment records.

### 4.6 Out for Delivery

The `out_for_delivery` status represents the final delivery stage.

Shipment tracking information can be used to record delivery progress.

### 4.7 Order Delivery

The order reaches the `delivered` status when the delivery process is completed and the order status is updated accordingly.

## 5. Order Cancellation

The `OrderService.CANCELLABLE_STATUSES` collection contains:

```python
{
    "pending",
    "confirmed",
}
```

Therefore, the service permits cancellation only for orders in these statuses.

### 5.1 Cancellation Requirements

The cancellation operation includes:

1. Validate the order ID.
2. Retrieve the order.
3. Verify that the order exists.
4. Check whether its current status permits cancellation.
5. Require a cancellation reason.
6. Perform the cancellation through the order repository.
7. Add an order tracking event.

### 5.2 Cancellation Restrictions

Orders outside the cancellable statuses cannot be cancelled through the service's normal cancellation operation.

For example, an order in `processing`, `shipped`, or `delivered` status is not included in the configured cancellable statuses.

### 5.3 Cancellation Tracking

The cancellation reason is stored with the order, and the operation adds a tracking event to preserve the order history.

## 6. Payment Lifecycle

Payment status is maintained separately from order status.

The `OrderService.PAYMENT_STATUSES` collection defines:

| Payment Status | Description |
| --- | --- |
| `pending` | Payment is awaiting completion |
| `paid` | Payment has been completed |
| `failed` | Payment attempt failed |
| `refunded` | Payment has been fully refunded |
| `partially_refunded` | Part of the payment has been refunded |

### 6.1 Supported Payment Methods

The order service supports:

- `razorpay`
- `cod`

### 6.2 Razorpay Payment

Razorpay payment transactions are managed through the payment functionality.

The payment transaction model stores provider information, including:

- Provider order ID.
- Provider payment ID.
- Payment amount.
- Currency.
- Payment status.
- Idempotency key.

### 6.3 Cash on Delivery

Cash on delivery is supported as a payment method.

The payment method is represented by:

```text
cod
```

Payment status and order status should be treated as separate pieces of information.

### 6.4 Refunds

The payment module supports full and partial refunds.

The payment transaction statuses include:

- `refunded`
- `partially_refunded`

Refund records are managed through the payment refund functionality.

## 7. Delivery and Shipment Lifecycle

Delivery management uses a separate shipment lifecycle.

The `DeliveryService.SHIPMENT_TRANSITIONS` collection defines the supported shipment transitions.

### 7.1 Shipment Statuses

| Status | Description |
| --- | --- |
| `created` | Shipment has been created |
| `assigned` | Shipment has been assigned |
| `picked_up` | Shipment has been picked up |
| `in_transit` | Shipment is moving through the delivery network |
| `out_for_delivery` | Shipment is out for final delivery |
| `delivered` | Shipment has been delivered |
| `failed` | Delivery attempt has failed |
| `returned` | Shipment has been returned |
| `cancelled` | Shipment has been cancelled |

### 7.2 Supported Shipment Transitions

The following transitions are defined by the delivery service:

| Current Status | Allowed Next Statuses |
| --- | --- |
| `created` | `assigned`, `cancelled` |
| `assigned` | `picked_up`, `cancelled`, `failed` |
| `picked_up` | `in_transit`, `failed` |
| `in_transit` | `out_for_delivery`, `failed`, `returned` |
| `out_for_delivery` | `delivered`, `failed`, `returned` |
| `failed` | `assigned`, `returned`, `cancelled` |
| `delivered` | None |
| `returned` | None |
| `cancelled` | None |

The delivery service validates shipment status transitions before updating shipment information.

### 7.3 Shipment Tracking

Shipment tracking events record delivery progress.

Tracking information can include:

- Shipment status.
- Event description.
- Location.
- Updated by.
- Event timestamp.

The delivery repository retrieves shipment records with their related order, delivery partner, delivery slot, and tracking events.

## 8. Order Tracking

The customer order API provides an endpoint to retrieve order tracking information.

**HTTP Method:** `GET`

**Endpoint:**

```http
/api/v1/orders/{order_id}/tracking
```

The response includes tracking event information such as:

| Field | Description |
| --- | --- |
| `id` | Tracking event ID |
| `status` | Recorded order status |
| `title` | Tracking event title |
| `description` | Event description |
| `location` | Event location |
| `updated_by` | User or system that recorded the event |
| `created_at` | Event creation timestamp |

Tracking events provide a history of order progress.

## 9. Order Management APIs

The following endpoints support customer and administrative order operations.

| Operation | HTTP Method | Endpoint |
| --- | --- | --- |
| Checkout | POST | `/api/v1/orders/checkout` |
| Customer order history | GET | `/api/v1/orders` |
| Retrieve order by number | GET | `/api/v1/orders/number/{order_number}` |
| Retrieve order by ID | GET | `/api/v1/orders/{order_id}` |
| Retrieve order tracking | GET | `/api/v1/orders/{order_id}/tracking` |
| Retrieve order total | GET | `/api/v1/orders/{order_id}/total` |
| Admin order status update | PATCH | `/api/v1/admin/orders/{order_id}/status` |

Customer endpoints require customer authentication.

Administrative status updates require admin authorization.

## 10. Order Data and Snapshots

The order service supports order item snapshots.

These snapshots preserve relevant product information at the time of purchase.

Order item response information includes:

- Product ID.
- Product name.
- Product SKU.
- Quantity.
- Unit price.
- Line total.

Order totals include:

| Field | Description |
| --- | --- |
| `subtotal` | Order item subtotal |
| `tax_amount` | Applied tax |
| `delivery_fee` | Delivery charge |
| `discount_amount` | Applied discount |
| `total_amount` | Final order total |

Monetary values are handled using Python `Decimal` and rounded to two decimal places using `ROUND_HALF_UP`.

## 11. Transaction Management

Database transaction handling is important during order operations.

The application uses SQLAlchemy sessions and repositories.

The order service delegates database operations to:

- `OrderRepository`
- `CartRepository`
- `CustomerRepository`

The order service documentation specifies that transaction commits are managed by the caller.

The transaction owner must ensure that failed operations are rolled back appropriately.

## 12. Error Handling and Validation

The order service validates important business conditions.

Examples include:

- Customer ID must be a positive integer.
- Order ID must be valid.
- Customer must exist.
- Payment method must be supported.
- Monetary amounts cannot be negative.
- Cancellation reason is required.
- Order must be in a cancellable status before cancellation.
- Invalid order status values must be rejected.

The API layer translates service and validation errors into appropriate HTTP responses.

## 13. Lifecycle Summary

The Finmarket Kart Essentials order lifecycle is organized into separate but related processes.

| Process | Responsible Component |
| --- | --- |
| Customer checkout | Customer Orders API |
| Order business logic | `OrderService` |
| Order database operations | `OrderRepository` |
| Cart operations | `CartRepository` |
| Customer validation | `CustomerRepository` |
| Payment processing | Payment module |
| Shipment management | `DeliveryService` |
| Shipment database operations | `DeliveryRepository` |
| Customer tracking | Order and delivery tracking functionality |

The order lifecycle and shipment lifecycle are separate state-management processes.

Payment status is also maintained independently from order status.

---

**Project:** Finmarket Kart Essentials

**Document:** Order Lifecycle

**Version:** 1.0.0
