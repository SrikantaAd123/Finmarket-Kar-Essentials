# Finmarket Kart Essentials

**Finmarket Kart Essentials** is a full-stack grocery and everyday-essentials commerce application using the FINMARKET.IN brand identity. The UI uses the navy/teal logo palette, Bootstrap 5, custom CSS and browser JavaScript. The API is bootstrapped through the existing **FinMkt FastAPI** application factory (`finmkt.fastapi.create_app`). MySQL stores customers, categories, catalogue products, carts, addresses, coupons, orders, reviews and newsletter subscribers. ZITADEL provides user sign-in and API access-token validation.

> This is a substantial production-oriented project foundation, not a claim that Amazon's private catalogue has been copied. The included starter catalogue has 80 sample products in 10 categories. It is intentionally structured to accept much larger catalogue imports. Use supplier-authorised product data, prices and images when expanding it.

## Included capabilities

- Responsive storefront with FINMARKET logo colours, navigation, search, categories, sorting, promotional areas and product cards.
- Dedicated, branded sign-in page that redirects to the ZITADEL-hosted login experience. The site never asks customers to enter their ZITADEL password into the store.
- Authorization Code + PKCE using the ZITADEL public/User-Agent application.
- FastAPI bearer-token authorization. Protected API routes validate access tokens against ZITADEL's `/oauth/v2/introspect` endpoint from the server, using credentials stored only in backend `.env`. This supports JWT and opaque access tokens and checks whether the token is active/revoked.
- Customer profile, persisted cart, guest cart, wishlist, delivery addresses, coupons, order placement and order history.
- Checkout with stock checks, transactional order creation, stock decrement and **Cash on Delivery**.
- Administrator API and console for product creation, inventory updates, order-status updates and store metrics.
- Newsletter subscription persistence.
- API health/readiness endpoints and Swagger/OpenAPI docs.

## Architecture

```text
Browser (HTML + Bootstrap + CSS + JavaScript)
       |
       | ZITADEL Authorization Code + PKCE
       v
ZITADEL hosted login
       |
       | Access token
       v
FinMkt FastAPI application factory
       |
       +-- /api/v1/catalog, categories, products
       +-- /api/v1/cart, wishlist
       +-- /api/v1/account, addresses
       +-- /api/v1/orders, checkout
       +-- /api/v1/admin, store operations
       +-- /api/v1/newsletter
       |
       +-- ZITADEL token introspection (server-to-server)
       |
       v
MySQL (customers, catalogue, inventory, carts, orders, etc.)
```

## 1. Requirements

- Windows 10/11 with PowerShell
- Python 3.11 or newer
- `uv`
- MySQL 8.x (local installation or a managed MySQL instance)
- Access to your existing FinMkt FastAPI source package
- A ZITADEL project where you can create a public SPA/User-Agent application and an API application using Basic authentication

## 2. Install the project

Extract this project folder somewhere convenient, for example:

`C:\Users\YOUR_USER\Downloads\Finmarket-Kart-Essentials`

Open PowerShell in that folder:

```powershell
cd "$env:USERPROFILE\Downloads\Finmarket-Kart-Essentials"
uv sync --extra dev
```

### Install your existing FinMkt FastAPI package into this project's uv environment

This project intentionally does not replace or reimplement your FinMkt package. It imports `create_app` from `finmkt.fastapi` and uses the package's `app_config_from_settings` bridge.

Use the actual local path where your existing FinMkt FastAPI package lives. Based on the path used in your earlier FinMkt work, the command may look like this:

```powershell
$FinMktFastAPIPath = "$env:USERPROFILE\Downloads\samlapa-20261109T063346Z-1-001\samlapa\io\finmkt\fastapi"
Test-Path $FinMktFastAPIPath
uv pip install --python .\.venv\Scripts\python.exe --editable $FinMktFastAPIPath
```

`Test-Path` should return `True`. If your FinMkt package is stored in a different folder, change only `$FinMktFastAPIPath` to that folder. Do not install an unrelated package with the same name from a public package index.

## 3. Create the MySQL database

Open MySQL command line or MySQL Workbench and run this SQL. Choose a strong password and use the same value in `.env`:

```sql
CREATE DATABASE finmarket_kart
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'finmarket_user'@'%' IDENTIFIED BY 'REPLACE_WITH_A_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON finmarket_kart.* TO 'finmarket_user'@'%';
FLUSH PRIVILEGES;
```

Copy the environment template:

```powershell
Copy-Item .env.example .env
notepad .env
```

At minimum, update `DATABASE_URL`, the ZITADEL values and `ADMIN_EMAILS`. Keep `.env` private. Never commit it to GitHub.

Example database URL:

```text
mysql+pymysql://finmarket_user:YOUR_PASSWORD@127.0.0.1:3306/finmarket_kart?charset=utf8mb4
```

If your MySQL password contains special URL characters, URL-encode the password portion or use a password with URL-safe characters for the local development account.

## 4. Configure ZITADEL

The ZITADEL setup has two separate applications. They serve different purposes and must not share a client secret with the browser.

### A. Create the website application

In your ZITADEL project, create a **User Agent / Single Page Application** and select **Authorization Code with PKCE**.

Register these exact redirect URLs for local development (the Swagger URI is needed when using the Authorize button in `/docs`):

```text
Redirect URI:       http://127.0.0.1:8000/auth/callback
Post-logout URI:    http://127.0.0.1:8000/
Swagger OAuth URI:  http://127.0.0.1:8000/docs/oauth2-redirect
Allowed web origin: http://127.0.0.1:8000
```

Copy the public application's Client ID into:

```env
ZITADEL_PUBLIC_CLIENT_ID=YOUR_SPA_CLIENT_ID
```

The public client ID is not a secret. Do not create or put a client secret in the browser application. If you use `http://localhost:8000` instead of `http://127.0.0.1:8000`, register and use the localhost URLs consistently. ZITADEL requires the redirect URI to match exactly.

### B. Create the API application for introspection

Create an **API** application in the same ZITADEL project and select **Basic** as its authentication method. Copy its Client ID and Client Secret to the backend-only `.env` values:

```env
ZITADEL_API_CLIENT_ID=YOUR_API_CLIENT_ID
ZITADEL_API_CLIENT_SECRET=YOUR_API_CLIENT_SECRET
```

The secret is used only by the FastAPI server when it calls ZITADEL's introspection endpoint. Do not add it to `index.html`, JavaScript, HTML attributes, public GitHub repositories or screenshots.

### C. Configure the API audience scope

Use the ZITADEL **project ID that represents this API**. Add it to `.env` in both settings below:

```env
ZITADEL_AUDIENCE_SCOPE=urn:zitadel:iam:org:project:id:YOUR_API_PROJECT_ID:aud
ZITADEL_API_AUDIENCE=YOUR_API_PROJECT_ID
```

The website requests this audience scope during login. The API checks the audience returned by introspection. Use the project ID, not the application Client ID.

Set your issuer URL exactly as shown in your ZITADEL OIDC settings, without appending `/oauth/v2`:

```env
ZITADEL_ISSUER=https://YOUR-TENANT.zitadel.cloud
ZITADEL_SCOPES=openid profile email offline_access
```

If you are using a custom ZITADEL domain, use that exact issuer domain. The login code discovers the authorization, token and end-session endpoints from the issuer's OIDC discovery document.

### D. Configure the first store administrator

For local setup, set a verified ZITADEL email address that should receive administrator permissions:

```env
ADMIN_EMAILS=your-admin-email@example.com
```

Use a controlled internal account. The allow-list is evaluated only after successful ZITADEL token introspection. Other authenticated accounts receive the `customer` role. Administrator status is recalculated from this verified-email allow-list on each validated API request.

## 5. Start the application

For local development, set:

```env
AUTO_CREATE_TABLES=true
```

Optional: to run MySQL in Docker instead of installing MySQL locally, make sure the `MYSQL_*` values in `.env` are set and run:

```powershell
docker compose up -d mysql
```

Make sure the password and username in `DATABASE_URL` match the `MYSQL_USER` and `MYSQL_PASSWORD` values in `.env`.

Then run the database migration and load the sample catalogue:

```powershell
uv run alembic upgrade head
uv run python -m scripts.seed_catalog
```

Start the website and API:

```powershell
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- Storefront: `http://127.0.0.1:8000/`
- Secure sign-in: `http://127.0.0.1:8000/login`
- Store admin: `http://127.0.0.1:8000/admin` (administrator account only)
- Swagger API docs: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- API health: `http://127.0.0.1:8000/api/v1/system/health`
- Database readiness: `http://127.0.0.1:8000/api/v1/system/ready`

The API prefix is supplied to the FinMkt FastAPI configuration as `/api/v1`. If the installed FinMkt package applies a different prefix policy, adjust `Settings.api_prefix` in `backend/config.py` to match the factory version used by your other FinMkt services.

## 6. Grow the catalogue with a CSV import

The starter catalogue is intentionally only a small demonstration dataset. To load a larger supplier-authorised product list, copy `catalog_import_template.csv`, replace the sample rows with your supplier catalogue and keep the required columns. Category slugs must already exist (the importer creates the ten starter categories first). Product rows are inserted by SKU or updated when that SKU already exists.

```powershell
uv run python -m scripts.import_catalog .\catalog_import_template.csv
```

Use product data and images that your suppliers or licensors have authorised you to publish. This import tool is a scalable way to load your own catalogue; it does not copy Amazon or Flipkart's private product databases.

## 7. Main API routes

| Area | Route | Access |
| --- | --- | --- |
| Health | `GET /api/v1/system/health` | Public |
| Readiness | `GET /api/v1/system/ready` | Public |
| ZITADEL config | `GET /api/v1/auth/config` | Public |
| Current identity | `GET /api/v1/auth/me` | Signed in |
| Categories | `GET /api/v1/categories` | Public |
| Product catalogue | `GET /api/v1/products` | Public |
| Product detail | `GET /api/v1/products/{product_id}` | Public |
| Cart | `GET /api/v1/cart` | Signed in |
| Add cart item | `POST /api/v1/cart/items` | Signed in |
| Wishlist | `GET /api/v1/cart/wishlist` | Signed in |
| Addresses | `GET/POST /api/v1/account/addresses` | Signed in |
| Checkout | `POST /api/v1/orders/checkout` | Signed in |
| Order history | `GET /api/v1/orders` | Signed in |
| Reviews | `GET/POST /api/v1/products/{product_id}/reviews` | Read public / write signed in |
| Newsletter | `POST /api/v1/newsletter/subscribe` | Public |
| Admin metrics | `GET /api/v1/admin/overview` | Admin |
| Add product | `POST /api/v1/admin/products` | Admin |
| Update inventory | `PATCH /api/v1/admin/products/{product_id}/stock` | Admin |
| Update order status | `PATCH /api/v1/admin/orders/{order_number}/status` | Admin |

## 8. Checkout and payments

The included checkout supports **Cash on Delivery**. It verifies stock inside a database transaction, calculates totals on the backend, creates the order and order-item records, decrements inventory and clears the cart. Do not switch the browser to an “online paid” state without integrating and verifying a payment provider (for example, a payment gateway with server-side order creation, webhook signature validation, idempotency and refund handling).

Delivery charges are configured by `DELIVERY_FEE` and `FREE_DELIVERY_THRESHOLD`. Coupon examples seeded into the database are `WELCOME10` and `SAVE50`.

## 9. Production checklist before public launch

Run the starter regression checks after installing your local FinMkt FastAPI package:

```powershell
uv run pytest
```

This project is a sizeable working foundation, but these environment-specific launch tasks still need to be completed and verified in your own infrastructure:

1. Use HTTPS for the storefront, API and exact ZITADEL redirect URIs.
2. Use a managed MySQL database, backups and least-privilege database credentials; run `uv run alembic upgrade head` for schema changes and set `AUTO_CREATE_TABLES=false` in production.
3. Put secrets in your deployment secret manager, not in a committed `.env` file.
4. Add a payment gateway only after implementing server-side verification and webhook handling.
5. Connect actual delivery partners, shipping zones, serviceable PIN codes and inventory fulfilment rules.
6. Add rate limiting, security headers, a strict Content Security Policy, audit events, alerting and structured log shipping.
7. Add automated integration tests against a disposable MySQL database and a non-production ZITADEL project.
8. Add catalogue import tooling using supplier-authorised CSV/API data and appropriately licensed product images.

## 10. Troubleshooting notes

- **`ModuleNotFoundError: finmkt`**: install the existing local FinMkt FastAPI package into this project's `.venv` using the command in section 2.
- **`404` on `/api/v1/...`**: check the API prefix produced by the installed FinMkt app config. The app routers are passed to `create_app`; the factory owns prefixing and app middleware.
- **ZITADEL `invalid_redirect_uri`**: the browser origin, redirect URI, trailing slash and registered ZITADEL URL must match exactly. Use one hostname consistently (`127.0.0.1` or `localhost`).
- **ZITADEL `invalid_client` during API access**: check that `ZITADEL_API_CLIENT_ID` and `ZITADEL_API_CLIENT_SECRET` belong to the API app configured for Basic introspection, not the public SPA app.
- **API returns 403 audience error**: check that the API project's project ID is used in both `ZITADEL_AUDIENCE_SCOPE` and `ZITADEL_API_AUDIENCE`.
- **API returns 503 token validation not configured**: fill the three API introspection values in `.env` and restart Uvicorn.
- **No products are shown**: make sure MySQL is running, `AUTO_CREATE_TABLES=true` in development, and run `uv run python -m scripts.seed_catalog`.

## Security note

The access token is kept in browser `sessionStorage`, not `localStorage`, and sent only as an Authorization bearer token to the same-origin API. The API does not accept an ID token as an API access token. The API's ZITADEL client secret stays on the server. As with any browser-based application, use HTTPS, keep frontend dependencies controlled, apply a restrictive Content Security Policy and prevent cross-site scripting. For deployments that require tokens never to be accessible to browser JavaScript, evolve this SPA into a backend-for-frontend using secure HttpOnly cookies.


## Selected single-server storefront

The default website served by `backend.main:app` is the Python/Jinja storefront in `frontend/`. It uses the FastAPI backend on the same origin, so the intended local URL is `http://127.0.0.1:8000/`. The optional Angular prototype in `client/` is not the default website and is not required to start the FastAPI storefront. See `ANGULAR_CATALOG_INTEGRATION_README.md` for the distinction.

The catalogue uses the live category API and supports category selection, server-side product search, sorting and pagination. Category image URLs under `/images/` and product/static image URLs under `/static/images/` are both served from `frontend/static/images/`.

The sample product photographs are a limited fallback set. For a real production catalogue, upload or assign the correct authorised image to each SKU rather than treating a fallback photograph as the exact product.
