
# Finmarket Kart Essentials – System Architecture

## 1. Introduction

Finmarket Kart Essentials is an e-commerce backend application built using Python and FastAPI.

The system follows a layered architecture that separates API handling, authentication, business logic, database operations, and data models.

The architecture is designed to support:

- Customer management.
- Product catalog management.
- Shopping cart operations.
- Order processing.
- Payment management.
- Inventory management.
- Delivery and shipment tracking.
- Administrative operations.

## 2. Technology Stack

| Component | Technology |
| --- | --- |
| Programming Language | Python |
| Backend Framework | FastAPI |
| Database | MySQL |
| ORM | SQLAlchemy |
| Database Driver | PyMySQL |
| Data Validation | Pydantic |
| Authentication | ZITADEL JWT |
| Payment Provider | Razorpay |
| Database Migration | Alembic |
| ASGI Server | Uvicorn |
| Testing | Pytest |
| Containerization | Docker |

## 3. High-Level Architecture

The application follows a layered backend architecture.

```text
                    CLIENT APPLICATION
                            |
                            v
                       FASTAPI API
                            |
                            v
                  AUTHENTICATION LAYER
                            |
                            v
                      API ROUTERS
                            |
                            v
                     SERVICE LAYER
                            |
                            v
                   REPOSITORY LAYER
                            |
                            v
                    SQLALCHEMY ORM
                            |
                            v
                       MYSQL DB
```

External integrations are handled by their respective application modules.

Examples include:

- ZITADEL for authentication.
- Razorpay for online payment processing.

## 4. Backend Project Structure

The backend is organized into separate modules.

```text
backend/
│
├── __init__.py
├── main.py
│
├── admin/
│
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── admin.py
│       └── orders.py
│
├── auth/
│   ├── dependencies.py
│   └── zitadel.py
│
├── database/
│   ├── connection.py
│   └── commerce_base.py
│
├── models/
│
├── repositories/
│
├── schemas/
│
├── services/
│
├── inventory/
│
├── delivery/
│
├── payments/
│
├── orders/
│
├── notifications/
│
└── utils/
```

The structure represents the major backend areas. Individual files and subpackages may vary as the project develops.

## 5. Application Entry Point

The main FastAPI application is created in:

```text
backend/main.py
```

The entry point is responsible for:

- Creating the FastAPI application.
- Configuring application metadata.
- Registering middleware.
- Registering API routers.
- Providing application-level endpoints.
- Managing application startup and shutdown.

The application is served through Uvicorn.

Example:

```powershell
uv run uvicorn backend.main:app --reload
```

## 6. API Layer

The API layer exposes application functionality through HTTP endpoints.

It uses FastAPI routers to organize related operations.

Current customer order and administrative order routers include:

```text
backend/api/v1/orders.py
backend/api/v1/admin.py
```

The customer order router handles operations such as:

- Checkout.
- Customer order history.
- Order retrieval.
- Order tracking.
- Order total retrieval.

The administrative router handles administrative order operations, including order status updates.

The API layer is responsible for:

- Receiving HTTP requests.
- Validating request data.
- Resolving dependencies.
- Calling service methods.
- Serializing responses.
- Returning HTTP status codes.

## 7. Authentication Layer

Authentication is implemented through ZITADEL JWT validation.

The authentication modules include:

```text
backend/auth/
```

Important files:

| File | Responsibility |
| --- | --- |
| `zitadel.py` | ZITADEL token validation and configuration |
| `dependencies.py` | FastAPI authentication dependencies |

The authentication flow is:

1. Client obtains an access token through the configured identity provider.
2. Client sends the token using the Bearer authorization scheme.
3. FastAPI authentication dependencies receive the token.
4. The backend validates the JWT signature and claims.
5. The authenticated user information is made available to protected endpoints.
6. Administrative endpoints apply additional authorization checks.

Example HTTP header:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## 8. Service Layer

The service layer contains business logic.

Services coordinate operations between repositories and other application components.

Examples include:

| Service | Responsibility |
| --- | --- |
| `OrderService` | Checkout, order creation, order history and cancellation |
| `DeliveryService` | Delivery partners, delivery slots, shipments and tracking |
| `InventoryService` | Warehouse stock, reservations and stock movements |
| `AdminDashboardService` | Administrative dashboard operations |

The service layer is responsible for:

- Business validation.
- Workflow coordination.
- Status transition validation.
- Calculations.
- Transaction coordination where applicable.
- Handling business-level errors.

## 9. Repository Layer

The repository layer handles database operations.

Repositories separate SQLAlchemy queries from business logic.

Examples include:

- `OrderRepository`
- `CartRepository`
- `CustomerRepository`
- `InventoryRepository`
- `DeliveryRepository`

Typical repository responsibilities include:

- Creating database records.
- Retrieving records.
- Updating records.
- Filtering and pagination.
- Loading related entities.
- Flushing pending changes.

The inventory and delivery repositories use `flush()` rather than committing transactions themselves.

Transaction ownership must remain consistent with the corresponding service implementation.

## 10. Database Layer

The application uses MySQL with SQLAlchemy ORM.

Database-related files are located in:

```text
backend/database/
```

The project currently contains two separate SQLAlchemy declarative bases.

### 10.1 Legacy Base

The legacy declarative base is defined in:

```text
backend/database/connection.py
```

It is used by the existing WorkSphere-related models.

### 10.2 Commerce Base

The commerce declarative base is defined in:

```text
backend/database/commerce_base.py
```

Commerce models inherit from `CommerceBase`.

The two metadata registries must remain distinct unless the database architecture is deliberately refactored.

### 10.3 Database Session

SQLAlchemy sessions are used to interact with the database.

The application database dependency provides sessions to API operations and other components.

## 11. Models and Schemas

Models and schemas have different responsibilities.

### 11.1 SQLAlchemy Models

Models represent database entities.

Examples include:

- Customer.
- Product.
- Order.
- PaymentTransaction.
- PaymentRefund.
- Warehouse.
- InventoryStock.
- DeliveryPartner.
- Shipment.

Models define database columns, relationships, constraints, and indexes.

### 11.2 Pydantic Schemas

Schemas validate incoming requests and define response structures.

Examples include:

- Order checkout request.
- Order response.
- Order tracking response.
- Payment request and response schemas.
- Inventory request and response schemas.

The API layer uses schemas to validate data and serialize responses.

## 12. Payment Integration

Payment functionality is maintained separately from the order business logic.

Supported payment methods include:

- Razorpay.
- Cash on Delivery.

The payment transaction model stores:

- Related order ID.
- Payment method.
- Provider.
- Provider order ID.
- Provider payment ID.
- Payment amount.
- Currency.
- Transaction status.
- Failure information.
- Idempotency key.

The payment module also supports refund records.

Payment verification and provider communication must be handled by the payment implementation.

## 13. Inventory Management

The inventory module manages stock across warehouses.

Its main entities include:

- Warehouse.
- InventoryStock.
- StockReservation.
- StockMovement.

The inventory repository manages database operations for these entities.

Inventory validation includes:

- Positive quantity validation.
- Non-negative stock validation.
- Reservation status validation.
- Movement type validation.
- Movement direction validation.

The available quantity is calculated as:

```text
Available Quantity = Quantity on Hand - Quantity Reserved
```

## 14. Delivery Management

The delivery module manages the physical delivery process.

Its main entities include:

- DeliveryPartner.
- ServiceablePincode.
- DeliverySlot.
- Shipment.
- ShipmentTracking.

The delivery service validates shipment status transitions and coordinates repository operations.

Shipment tracking records preserve delivery progress, including status, description, location, and timestamp.

## 15. Middleware and Cross-Origin Configuration

The application configures middleware at the FastAPI application level.

CORS middleware controls which browser origins are permitted to access the API.

The allowed origins should be configured according to the frontend environments.

Production configuration should use explicitly trusted origins rather than unrestricted access.

## 16. Error Handling

The application uses multiple validation and error-handling layers.

### API Layer

Handles HTTP-related errors and translates application exceptions into appropriate HTTP responses.

### Service Layer

Validates business rules and raises meaningful exceptions when operations are invalid.

### Repository Layer

Performs database operations and allows database failures to propagate to the transaction owner.

### Database Transactions

Failed transactions must be rolled back by the component responsible for transaction management.

## 17. Testing Architecture

The application uses Pytest for automated testing.

The test suite is organized into different testing categories.

```text
tests/
│
├── conftest.py
│
├── auth/
│
├── unit/
│
├── integration/
│
├── orders/
│
└── payments/
```

Testing responsibilities include:

| Test Category | Purpose |
| --- | --- |
| Unit Tests | Validate individual functions and services |
| Integration Tests | Validate interactions between application components |
| Authentication Tests | Validate JWT authentication behavior |
| Order Tests | Validate order lifecycle and cancellation |
| Payment Tests | Validate payment and webhook behavior |

Run the complete test suite:

```powershell
uv run pytest tests -v
```

Generate a coverage report:

```powershell
uv run pytest tests --cov=backend --cov-report=term-missing
```

## 18. Deployment Architecture

The project includes a Docker-based deployment structure.

```text
deployment/
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── monitoring/
│   └── prometheus.yml
│
└── nginx/
    └── nginx.conf
```

The deployment configuration is intended to support:

- FastAPI backend.
- MySQL database.
- Nginx reverse proxy.
- Prometheus monitoring.

Prometheus scraping requires a metrics endpoint to be implemented by the backend.

Production deployment also requires secure secrets, HTTPS, database backups, and appropriate access controls.

## 19. Application Request Flow

A typical protected customer API request follows this sequence:

1. Client sends an HTTP request.
2. FastAPI receives the request.
3. Authentication dependencies validate the access token.
4. The API router validates request parameters and schemas.
5. The service layer executes business logic.
6. The repository layer performs database operations.
7. SQLAlchemy communicates with MySQL.
8. The service returns the result.
9. The API layer serializes the response.
10. FastAPI returns the HTTP response to the client.

## 20. Architecture Summary

Finmarket Kart Essentials uses a modular, layered backend architecture.

| Layer | Main Responsibility |
| --- | --- |
| API | HTTP endpoints and request handling |
| Authentication | ZITADEL JWT validation and authorization |
| Services | Business rules and workflow coordination |
| Repositories | Database queries and persistence |
| Models | SQLAlchemy database entities |
| Schemas | Request and response validation |
| Database | MySQL persistence |
| Integrations | Razorpay and other external services |
| Testing | Automated quality validation |
| Deployment | Containerized application execution |

This separation improves maintainability, testability, and clarity as the application grows.

---

**Project:** Finmarket Kart Essentials

**Document:** System Architecture

**Version:** 1.0.0
