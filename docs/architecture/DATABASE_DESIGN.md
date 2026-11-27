
# Finmarket Kart Essentials – Database Design

## 1. Introduction

The Finmarket Kart Essentials backend uses MySQL as its relational database and SQLAlchemy ORM for database operations.

The database stores and manages information related to:

- Customers and authentication.
- Product catalog and categories.
- Shopping carts and cart items.
- Customer addresses.
- Orders and order items.
- Payments and refunds.
- Inventory and warehouse management.
- Delivery partners and shipments.
- Shipment tracking.
- Administrative operations.

The database design uses relational tables, primary keys, foreign keys, constraints, indexes, and ORM relationships to maintain data consistency.

## 2. Database Technology

| Component | Technology |
| --- | --- |
| Database | MySQL |
| ORM | SQLAlchemy |
| Database Driver | PyMySQL |
| Migration Tool | Alembic |
| Data Validation | Pydantic |
| Backend Framework | FastAPI |

## 3. Database Architecture

The application uses SQLAlchemy declarative models.

There are two declarative bases in the current project:

### 3.1 Commerce Database Base

Commerce models inherit from:

```python
from backend.database.commerce_base import CommerceBase
```

This base is used by the commerce-related models, including:

- Inventory models.
- Delivery models.
- Payment models.
- Other commerce entities that inherit from `CommerceBase`.

### 3.2 Legacy Database Base

The existing WorkSphere-related models use the `Base` defined in:

```python
from backend.database.connection import Base
```

These are separate declarative metadata registries.

They must not be treated as the same SQLAlchemy base unless the database architecture is deliberately refactored.

### 3.3 Database Connection

The database connection configuration is maintained in:

```text
backend/database/connection.py
```

The application uses a SQLAlchemy engine and database sessions to communicate with MySQL.

Database access is provided through the application's database dependency.

## 4. Main Database Entities

The following table describes the principal entities identified in the project.

| Entity | Purpose |
| --- | --- |
| Customer | Stores customer information |
| Category | Organizes products into categories |
| Product | Stores grocery product information |
| Cart | Represents a customer's shopping cart |
| Cart Item | Stores products and quantities in a cart |
| Address | Stores customer delivery and billing addresses |
| Order | Stores customer order information |
| Order Item | Stores purchased product snapshots |
| Payment Transaction | Stores payment attempts and provider details |
| Payment Refund | Stores refund information |
| Warehouse | Represents a physical inventory location |
| Inventory Stock | Stores product stock by warehouse |
| Stock Reservation | Tracks reserved inventory |
| Stock Movement | Records inventory changes |
| Delivery Partner | Stores delivery partner information |
| Serviceable Pincode | Stores supported delivery postal areas |
| Delivery Slot | Stores delivery time windows |
| Shipment | Represents the physical delivery of an order |
| Shipment Tracking | Stores shipment tracking events |

The final table inventory should be verified against the complete SQLAlchemy model registry and actual database migrations.

## 5. Entity Relationships

### 5.1 Customer and Orders

A customer can place multiple orders.

The order records contain a customer reference and preserve order-related information.

Conceptually:

```text
Customer
   |
   | One-to-Many
   |
   v
Orders
   |
   | One-to-Many
   |
   v
Order Items
```

### 5.2 Product Catalog

Products belong to product categories.

The catalog supports product identification through fields such as product name, SKU, slug, price, and category reference.

Conceptually:

```text
Category
   |
   | One-to-Many
   |
   v
Products
```

### 5.3 Shopping Cart

A shopping cart groups products selected by a customer.

Cart items store the selected products and quantities.

Conceptually:

```text
Customer
   |
   v
Cart
   |
   v
Cart Items
   |
   v
Products
```

### 5.4 Order and Payment

Payment transactions reference orders.

The payment model stores payment method, provider information, transaction identifiers, amount, currency, and payment status.

The project supports:

- Razorpay payments.
- Cash on delivery.
- Payment attempts.
- Full refunds.
- Partial refunds.

Conceptually:

```text
Order
   |
   v
Payment Transactions
   |
   v
Payment Refunds
```

### 5.5 Inventory Management

Inventory is maintained by product and warehouse.

The `InventoryStock` model references both `Product` and `Warehouse`.

A unique constraint prevents duplicate stock records for the same product and warehouse combination.

Conceptually:

```text
Product
   |
   v
Inventory Stock
   ^
   |
Warehouse
```

Inventory management also includes:

- Stock reservations.
- Stock movements.
- Reorder levels.
- Available quantity calculations.

### 5.6 Delivery Management

Delivery management contains partners, serviceable pincodes, delivery slots, shipments, and tracking events.

The `Shipment` model references:

- An order.
- An optional delivery partner.
- An optional delivery slot.

The shipment model also stores tracking information and delivery status.

Conceptually:

```text
Order
   |
   v
Shipment
   |
   +------------------+
   |                  |
   v                  v
Delivery Partner   Delivery Slot
   |
   v
Shipment Tracking Events
```

## 6. Important Database Tables

### 6.1 Payment Transactions

The payment transaction model uses the table:

```text
payment_transactions
```

Important fields include:

| Field | Purpose |
| --- | --- |
| `order_id` | Related order |
| `payment_method` | Payment method |
| `provider` | Payment provider |
| `provider_order_id` | Provider order reference |
| `provider_payment_id` | Provider payment reference |
| `idempotency_key` | Prevents duplicate payment operations |
| `amount` | Transaction amount |
| `currency` | Transaction currency |
| `status` | Payment status |

The model includes constraints for positive payment amounts and supported payment methods and statuses.

### 6.2 Inventory Stock

The inventory stock model uses:

```text
inventory_stock
```

Important fields include:

| Field | Purpose |
| --- | --- |
| `product_id` | Related product |
| `warehouse_id` | Related warehouse |
| `quantity_on_hand` | Physical stock quantity |
| `quantity_reserved` | Reserved stock quantity |
| `reorder_level` | Stock replenishment threshold |

The available quantity is calculated as:

```text
Available Quantity = Quantity on Hand - Quantity Reserved
```

The model enforces non-negative quantities and prevents reserved stock from exceeding stock on hand.

### 6.3 Delivery Shipments

The shipment model uses:

```text
shipments
```

Important fields include:

| Field | Purpose |
| --- | --- |
| `shipment_number` | Unique shipment reference |
| `order_id` | Related order |
| `delivery_partner_id` | Assigned delivery partner |
| `delivery_slot_id` | Assigned delivery slot |
| `status` | Shipment status |
| `tracking_number` | Shipment tracking reference |
| `estimated_delivery_at` | Expected delivery time |
| `picked_up_at` | Pickup timestamp |
| `delivered_at` | Delivery timestamp |
| `failure_reason` | Delivery failure details |

The model enforces unique shipment numbers and one shipment per order.

## 7. Primary Keys and Foreign Keys

Primary keys uniquely identify records.

Foreign keys maintain relationships between related tables.

Examples identified in the project include:

| Table | Foreign Key | References |
| --- | --- | --- |
| `payment_transactions` | `order_id` | `orders.id` |
| `inventory_stock` | `product_id` | `products.id` |
| `inventory_stock` | `warehouse_id` | `warehouses.id` |
| `shipments` | `order_id` | `orders.id` |
| `shipments` | `delivery_partner_id` | `delivery_partners.id` |
| `shipments` | `delivery_slot_id` | `delivery_slots.id` |

Foreign key deletion behavior is defined in the corresponding SQLAlchemy models.

For example:

- `RESTRICT` prevents deletion while dependent records exist.
- `SET NULL` clears optional references when the referenced record is deleted.

## 8. Database Constraints

The application uses database constraints to protect data integrity.

### 8.1 Primary Key Constraints

Each database record has a unique primary key.

### 8.2 Unique Constraints

Examples include:

- Unique delivery partner codes.
- Unique serviceable pincodes.
- Unique warehouse codes.
- Unique shipment numbers.
- Unique shipment order references.
- Unique inventory product and warehouse combinations.
- Unique payment idempotency keys.

### 8.3 Check Constraints

Examples include:

- Payment amounts must be positive.
- Inventory quantities cannot be negative.
- Reserved inventory cannot exceed physical stock.
- Delivery slot end time must be later than start time.
- Delivery slot capacity must be positive.
- Shipment status must belong to the supported status values.

## 9. Database Indexes

Indexes improve query performance for frequently searched or filtered fields.

The project defines indexes for selected fields, including:

- Payment order ID.
- Payment status.
- Payment provider order ID.
- Inventory warehouse ID.
- Warehouse city.
- Delivery partner phone.
- Delivery partner vehicle number.
- Shipment delivery partner ID.
- Shipment status.
- Serviceable pincode city.

Indexes should be selected based on actual query patterns and database performance measurements.

## 10. Transaction Management

Database transactions help maintain consistency when multiple operations must succeed together.

The application uses SQLAlchemy sessions for database operations.

The repository and service layers have different responsibilities.

### 10.1 Repository Layer

Repositories handle database operations such as:

- Creating records.
- Retrieving records.
- Updating records.
- Deleting records where supported.
- Executing database queries.
- Flushing pending database changes.

### 10.2 Service Layer

Services handle business logic and transaction management.

Depending on the service implementation, transaction operations include:

```python
db.commit()
db.rollback()
```

The inventory and delivery repositories use `flush()` rather than taking ownership of transaction commits.

### 10.3 Rollback

If a transaction fails, rollback prevents incomplete changes from being committed.

## 11. Database Migrations

Alembic is used for database schema migration management.

Migrations help maintain database schema changes as the application evolves.

Typical commands:

### Create a Migration

```powershell
uv run alembic revision --autogenerate -m "describe database change"
```

### Apply Migrations

```powershell
uv run alembic upgrade head
```

### Check Current Migration

```powershell
uv run alembic current
```

### View Migration History

```powershell
uv run alembic history
```

Autogenerated migrations must be reviewed before applying them.

## 12. Database Configuration and Security

Database configuration should be supplied through environment variables.

Example configuration keys:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE_NAME
```

The actual connection configuration must match the database setup in the application.

Security guidelines:

1. Never hardcode database passwords.
2. Keep `.env` files out of Git.
3. Use separate database credentials for development and production.
4. Restrict database access to trusted application services.
5. Use secure connections where supported.
6. Back up production databases regularly.
7. Avoid exposing sensitive customer and payment information in logs.

## 13. Database Backup and Recovery

Database backups protect application data against accidental deletion, corruption, and infrastructure failure.

Recommended operational practices:

- Schedule regular database backups.
- Store backups in a secure location.
- Restrict access to backup files.
- Test database restoration procedures.
- Maintain appropriate backup retention periods.
- Monitor database storage and availability.

## 14. Database Design Summary

The Finmarket Kart Essentials database uses a relational design with SQLAlchemy ORM and MySQL.

Its main responsibilities include:

- Customer and order data management.
- Product catalog management.
- Payment transaction and refund records.
- Warehouse and inventory management.
- Delivery partner and shipment management.
- Referential integrity through primary and foreign keys.
- Data integrity through unique and check constraints.
- Schema evolution through Alembic migrations.

The two declarative SQLAlchemy bases must remain distinct unless a deliberate architecture change is made.

---

**Project:** Finmarket Kart Essentials

**Document:** Database Design

**Version:** 1.0.0
