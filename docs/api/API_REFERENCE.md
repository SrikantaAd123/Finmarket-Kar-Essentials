
# Finmarket Kart Essentials – API Reference

## 1. Overview

Finmarket Kart Essentials provides REST APIs for customer order management and administrative order operations.

| Property | Value |
| --- | --- |
| Application | Finmarket Kart Essentials |
| API Version | v1 |
| Framework | FastAPI |
| API Prefix | `/api/v1` |
| Database | MySQL |
| Authentication | ZITADEL JWT |
| API Documentation | `/docs` |

## 2. Base URL Configuration

### 2.1 Local Development URL

```text
http://localhost:8000
```

### 2.2 API Base Path

```text
http://localhost:8000/api/v1
```

The production base URL should be configured according to the deployment environment.

## 3. Interactive API Documentation

FastAPI provides interactive API documentation.

| Documentation | Endpoint |
| --- | --- |
| Swagger UI | `/docs` |
| ReDoc | `/redoc` |
| OpenAPI JSON | `/openapi.json` |

Example:

```text
http://localhost:8000/docs
```

## 4. Application Endpoints

### 4.1 Root Information

Returns basic application information.

**HTTP Method:** `GET`

**Endpoint:** `/`

#### Successful Root Response

```json
{
  "application": "Finmarket Kart Essentials",
  "message": "API is running successfully.",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

### 4.2 Application Health Check

Checks whether the API process is responding.

**HTTP Method:** `GET`

**Endpoint:** `/health`

#### Successful Health Response

```json
{
  "status": "healthy",
  "application": "Finmarket Kart Essentials"
}
```

This endpoint checks application responsiveness. It does not independently verify database connectivity.

## 5. Customer Order APIs

**Router Prefix:** `/api/v1/orders`

**Tag:** Customer Orders

These endpoints use the authenticated customer dependency.

### 5.1 Customer Checkout

Creates an order using the authenticated customer's cart.

**HTTP Method:** `POST`

**Endpoint:** `/api/v1/orders/checkout`

**Authentication:** Required

#### Checkout Request Example

```json
{
  "shipping_address_id": 1,
  "billing_address_id": null,
  "payment_method": "cod",
  "customer_notes": "Please call before delivery."
}
```

**Successful Response:** `201 Created`

The response contains the created order information.

### 5.2 Customer Order History

Retrieves paginated orders belonging to the authenticated customer.

**HTTP Method:** `GET`

**Endpoint:** `/api/v1/orders`

**Authentication:** Required

#### Supported Query Parameters

| Parameter | Description |
| --- | --- |
| `page` | Page number; minimum 1 |
| `page_size` | Number of records; 1–100 |
| `status` | Optional order status filter |

#### Order History Request Example

```http
GET /api/v1/orders?page=1&page_size=10&status=pending
```

### 5.3 Retrieve Order by Order Number

Retrieves an order using its unique order number.

**HTTP Method:** `GET`

**Endpoint:** `/api/v1/orders/number/{order_number}`

**Authentication:** Required

**Path Parameter:** `order_number` – Unique order reference.

### 5.4 Retrieve Order by Database ID

Retrieves a specific order belonging to the authenticated customer.

**HTTP Method:** `GET`

**Endpoint:** `/api/v1/orders/{order_id}`

**Authentication:** Required

**Path Parameter:** `order_id` – Order database ID.

### 5.5 Retrieve Order Tracking History

Retrieves tracking history for a customer's order.

**HTTP Method:** `GET`

**Endpoint:** `/api/v1/orders/{order_id}/tracking`

**Authentication:** Required

**Path Parameter:** `order_id` – Order database ID.

### 5.6 Retrieve Order Total

Retrieves the stored total for a customer's order.

**HTTP Method:** `GET`

**Endpoint:** `/api/v1/orders/{order_id}/total`

**Authentication:** Required

**Path Parameter:** `order_id` – Order database ID.

## 6. Administrative Order APIs

**Router Prefix:** `/api/v1/admin`

**Tag:** Admin Operations

### 6.1 Update Administrative Order Status

Updates an order's status through the administrative order service.

**HTTP Method:** `PATCH`

**Endpoint:** `/api/v1/admin/orders/{order_id}/status`

**Authentication:** Admin authorization required.

#### Order Status Update Request

```json
{
  "status": "processing",
  "description": "Order status updated.",
  "location": "Hyderabad"
}
```

#### Supported Order Status Values

- `pending`
- `confirmed`
- `processing`
- `packed`
- `shipped`
- `out_for_delivery`
- `delivered`
- `cancelled`
- `returned`

**Path Parameter:** `order_id` – Order database ID.

## 7. Authentication and Authorization

The application uses ZITADEL JWT authentication.

Protected endpoints require an access token using the Bearer authentication scheme.

### 7.1 Authorization Header

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### 7.2 Authenticated Request Example

```http
GET /api/v1/orders
Authorization: Bearer eyJ...
```

The backend validates the token using the configured ZITADEL issuer and signing keys.

Administrative endpoints additionally require the appropriate administrative authorization.

Never commit access tokens, client secrets, or private keys to source control.

## 8. HTTP Response Status Codes

| Status Code | Meaning |
| --- | --- |
| 200 | Request completed successfully |
| 201 | Resource created successfully |
| 400 | Invalid request or business validation failure |
| 401 | Authentication required or invalid |
| 403 | Insufficient permissions |
| 404 | Requested resource not found |
| 422 | Request validation failed |
| 500 | Internal server error |

The exact status code depends on the endpoint and its error-handling implementation.

## 9. Example API Requests

### 9.1 Check API Health

Run the following command in PowerShell:

```powershell
Invoke-RestMethod `
    -Uri "http://localhost:8000/health" `
    -Method GET
```

### 9.2 Retrieve Customer Orders

```powershell
$token = "YOUR_ZITADEL_ACCESS_TOKEN"

$headers = @{
    Authorization = "Bearer $token"
}

Invoke-RestMethod `
    -Uri "http://localhost:8000/api/v1/orders" `
    -Headers $headers `
    -Method GET
```

### 9.3 Retrieve Order Details

```powershell
Invoke-RestMethod `
    -Uri "http://localhost:8000/api/v1/orders/1" `
    -Headers $headers `
    -Method GET
```

## 10. API Security Guidelines

1. Use HTTPS in production.
2. Require valid JWT authentication for protected endpoints.
3. Apply role-based authorization to administrative endpoints.
4. Validate all incoming request data.
5. Never expose database credentials or secret keys.
6. Avoid logging access tokens or sensitive customer information.
7. Validate webhook signatures for payment provider callbacks.
8. Apply appropriate rate limiting and request-size restrictions.

## 11. Important Implementation Notes

- All API paths documented here use the `/api/v1` prefix where applicable.
- Customer order endpoints operate on the authenticated customer's data.
- Administrative operations require admin authorization.
- Request and response schemas are defined in backend schema modules.
- Swagger UI provides the live API schema generated by the running application.
- This document records the currently identified application, customer-order, and admin-order endpoints.
- It is not yet a complete inventory of every backend router.

---

**Project:** Finmarket Kart Essentials

**Document:** API Reference

**Version:** 1.0.0
