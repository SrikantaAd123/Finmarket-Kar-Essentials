
# Finmarket Kart Essentials – Payment Flow

## 1. Introduction

The payment module manages payment-related operations for the Finmarket Kart Essentials e-commerce application.

The application supports two payment methods:

- Razorpay.
- Cash on Delivery (COD).

The payment functionality includes:

- Payment transaction records.
- Payment provider references.
- Payment status tracking.
- Payment failure information.
- Idempotency support.
- Full refunds.
- Partial refunds.

Payment information is maintained separately from the order status.

## 2. Payment Architecture

The payment functionality uses the following technologies:

| Component | Technology |
| --- | --- |
| Backend Framework | FastAPI |
| Programming Language | Python |
| Database | MySQL |
| ORM | SQLAlchemy |
| Payment Provider | Razorpay |
| Data Validation | Pydantic |
| Database Migrations | Alembic |

The payment transaction model is defined using SQLAlchemy and inherits from `CommerceBase`.

## 3. Supported Payment Methods

### 3.1 Razorpay

Razorpay is the online payment provider supported by the application.

The payment transaction model stores provider-related information, including:

- Provider name.
- Provider order ID.
- Provider payment ID.
- Payment amount.
- Currency.
- Payment status.

The configured payment method value is:

```text
razorpay
```

### 3.2 Cash on Delivery

Cash on Delivery allows customers to select payment at the time of delivery.

The configured payment method value is:

```text
cod
```

Both payment methods are included in the order service's supported payment methods.

## 4. Payment Transaction Model

The SQLAlchemy payment transaction model is:

```python
PaymentTransaction
```

The database table is:

```text
payment_transactions
```

The model stores payment attempts and provider information.

### 4.1 Payment Transaction Fields

| Field | Description |
| --- | --- |
| `order_id` | Related order ID |
| `payment_method` | Selected payment method |
| `provider` | Payment provider |
| `provider_order_id` | Provider order reference |
| `provider_payment_id` | Provider payment reference |
| `idempotency_key` | Unique key for duplicate-operation protection |
| `amount` | Payment amount |
| `currency` | Transaction currency |
| `status` | Payment transaction status |
| `failure_code` | Payment failure code |
| `failure_message` | Payment failure details |
| `authorized_at` | Payment authorization timestamp |
| `captured_at` | Payment capture timestamp |

The transaction model also includes primary key and timestamp mixins.

## 5. Payment Status Lifecycle

The payment transaction model supports the following statuses:

| Status | Description |
| --- | --- |
| `created` | Payment transaction has been created |
| `pending` | Payment is awaiting completion |
| `authorized` | Payment has been authorized |
| `captured` | Payment has been captured |
| `failed` | Payment attempt has failed |
| `cancelled` | Payment transaction has been cancelled |
| `refunded` | Payment has been refunded |
| `partially_refunded` | Part of the payment has been refunded |

The order service separately defines these payment status values:

- `pending`
- `paid`
- `failed`
- `refunded`
- `partially_refunded`

The transaction status and order-level payment status are separate representations. They should not be treated as identical without checking the corresponding service logic.

## 6. Razorpay Payment Flow

The following describes the conceptual online payment process.

### 6.1 Customer Selects Razorpay

The customer selects Razorpay as the payment method during checkout.

The order service recognizes:

```text
razorpay
```

as a supported payment method.

### 6.2 Payment Transaction Creation

A payment transaction can store:

- Related order ID.
- Payment method.
- Provider.
- Amount.
- Currency.
- Transaction status.

The payment transaction has a relationship with the order.

### 6.3 Provider Order Reference

The transaction model provides a field for storing the Razorpay provider order reference:

```text
provider_order_id
```

This allows the application to associate its payment transaction with a provider-side order.

### 6.4 Payment Completion

After the customer completes the payment process, the payment result must be verified before the application treats the transaction as successful.

The payment transaction model provides fields for:

- Provider payment ID.
- Payment authorization timestamp.
- Payment capture timestamp.
- Payment status.

The exact verification and capture sequence depends on the implementation of the payment service and API routes.

### 6.5 Payment Failure

When a payment attempt fails, the transaction model can store:

```text
failure_code
failure_message
```

This information helps identify and investigate payment failures.

## 7. Cash on Delivery Flow

Cash on Delivery is an alternative to online payment.

The conceptual flow is:

1. Customer selects COD during checkout.
2. The order service validates the supported payment method.
3. The order is created according to checkout business rules.
4. Payment is collected during delivery.
5. The payment record can be updated to reflect the payment outcome.

The exact timing and implementation of COD payment status updates must follow the payment service.

## 8. Idempotency

The payment transaction model contains an idempotency field:

```text
idempotency_key
```

This field is unique when a value is provided.

Idempotency helps protect payment operations against duplicate processing.

For example, if a client retries a payment request because of a network interruption, an idempotency mechanism can help prevent the same operation from being processed more than once.

The unique database constraint provides an additional safeguard for duplicate idempotency keys.

## 9. Payment Refunds

The payment model includes a separate refund entity:

```python
PaymentRefund
```

Payment transactions have a relationship with their associated refunds.

The application supports:

- Full refunds.
- Partial refunds.

### 9.1 Full Refund

A full refund represents the return of the complete refundable payment amount.

The transaction-level payment status includes:

```text
refunded
```

### 9.2 Partial Refund

A partial refund represents the return of only part of the payment amount.

The transaction-level payment status includes:

```text
partially_refunded
```

Refund records are associated with their parent payment transaction.

The exact refund validation, provider API calls, and status-update sequence are defined by the payment service implementation.

## 10. Database Relationships

The payment transaction model maintains a relationship with the order model.

Conceptually:

```text
Order
  |
  | One-to-Many
  |
  v
Payment Transactions
  |
  | One-to-Many
  |
  v
Payment Refunds
```

The payment transaction uses the following foreign key:

```text
payment_transactions.order_id
    -> orders.id
```

The foreign key uses `RESTRICT` deletion behavior.

Payment refunds are associated with payment transactions through the SQLAlchemy relationship.

## 11. Database Constraints and Indexes

The payment transaction model defines database constraints to protect transaction data.

### 11.1 Amount Constraint

The payment amount must be greater than zero.

### 11.2 Payment Method Constraint

Supported transaction payment methods are:

- `razorpay`
- `cod`

### 11.3 Payment Status Constraint

The transaction status must be one of the supported values:

- `created`
- `pending`
- `authorized`
- `captured`
- `failed`
- `cancelled`
- `refunded`
- `partially_refunded`

### 11.4 Unique Idempotency Key

The idempotency key is unique when provided.

### 11.5 Database Indexes

The model defines indexes for:

| Index Field | Purpose |
| --- | --- |
| `order_id` | Retrieve transactions for an order |
| `status` | Filter transactions by status |
| `provider_order_id` | Search provider order references |

## 12. Payment Security

Payment operations must follow secure implementation practices.

Recommended security requirements include:

1. Never expose Razorpay API secrets to frontend applications.
2. Store payment credentials in environment variables or a secure secret manager.
3. Verify payment signatures on the backend.
4. Validate payment amounts against trusted order data.
5. Verify webhook signatures before processing webhook events.
6. Use idempotency protection for retryable payment operations.
7. Avoid logging sensitive payment credentials.
8. Use HTTPS for production payment communication.
9. Restrict access to payment and refund operations.
10. Maintain transaction records for auditing.

These are security requirements; individual controls should be verified against the actual payment implementation.

## 13. Payment Error Handling

Payment operations should account for common failure scenarios.

| Scenario | Expected Handling |
| --- | --- |
| Invalid payment method | Reject the request |
| Invalid payment amount | Reject the transaction |
| Payment provider failure | Record the failure where applicable |
| Duplicate idempotency key | Prevent duplicate processing |
| Invalid payment verification | Reject the unverified payment |
| Refund failure | Preserve the failure information |
| Database failure | Roll back the affected database transaction |

The actual HTTP response and retry behavior depend on the relevant API and service implementation.

## 14. Payment Monitoring and Auditing

Payment transaction records support operational monitoring and auditing.

Useful monitoring information includes:

- Total payment attempts.
- Successful payment transactions.
- Failed payment transactions.
- Pending payment transactions.
- Full refunds.
- Partial refunds.
- Provider payment references.
- Payment failure codes.

Sensitive payment credentials must never be included in monitoring output or application logs.

## 15. Payment Flow Summary

The payment module provides the foundation for managing online and offline payment methods.

| Area | Responsibility |
| --- | --- |
| Order Service | Validates supported payment methods |
| Payment Transaction | Stores payment attempt information |
| Razorpay | Online payment provider |
| COD | Offline payment method |
| Payment Refund | Stores refund information |
| SQLAlchemy | Database object mapping |
| MySQL | Persistent transaction storage |

The payment module keeps transaction records associated with orders and supports payment status tracking, idempotency, and refunds.

---

**Project:** Finmarket Kart Essentials

**Document:** Payment Flow

**Version:** 1.0.0
