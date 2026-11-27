# FINMARKET frontend and API deployment note

## The selected single-server application

The runnable storefront in this archive is the Python-served frontend under `frontend/`:

- `frontend/pages/` contains the HTML/Jinja pages.
- `frontend/static/css/` contains the styles.
- `frontend/static/js/` contains the browser API, ZITADEL PKCE, catalogue, cart, checkout, account, orders and admin modules.
- `backend/main.py` serves these pages and the FastAPI `/api/v1` endpoints from the same origin.
- `frontend/static/images/` contains the logo, category banners and sample product images.

For this deployment, run **one Python FastAPI server**:

```powershell
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/`. Do not run `ng serve` for this selected storefront.

## About `client/`

The `client/` directory is an optional Angular prototype. It currently contains a catalogue home page and product detail page, not the complete cart, checkout, account and order workflow. It is not the frontend served at `/` by `backend.main:app`.

The older Angular integration instructions referred to an ASP.NET Core API on port 5000. That is not the selected runtime architecture in this Python project. Do not point this Angular prototype at the old .NET API.

If Angular is selected for a future deployment, it must first be completed for all required customer flows, built with `npm run build`, and explicitly mounted/served by FastAPI. An Angular dev server is not required for the Python-served storefront described above.

## Catalogue and images

The live category tiles are populated by `GET /api/v1/catalog/categories`. Selecting a category calls `GET /api/v1/catalog/products?category_id=...`. Product search, sorting and pagination are server-side.

Category image URLs in the seed data use `/images/...`; product fallback images use `/static/images/...`. FastAPI serves both URL prefixes from the repository's `frontend/static/images/` directory.

The included sample catalogue contains grocery-oriented sample products and a limited collection of reusable product photographs. It does not contain a unique, supplier-accurate photograph for every possible SKU. Replace sample/fallback photos with authorised product images before public launch.

## Important data rule

Public products are returned only when active, published and not deleted. Review `database/publish_existing_products.sql` and execute it only if every affected active product is approved for sale. It updates existing products; it does not create product photography or populate inventory quantities.
