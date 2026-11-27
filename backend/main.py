"""FINMARKET Kart Essentials - FastAPI application entry point.

The Streamlit storefront is the customer-facing frontend (default port 8501).
FastAPI serves the commerce API and Swagger documentation (default port 8000).
The old HTML frontend is optional; its absence must never prevent API startup.

Run from the project root:
    uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

Or:
    uv run python -m backend.main
"""
from __future__ import annotations

import logging
import os
import secrets
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# -----------------------------------------------------------------------------
# 1. Paths and environment
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

APP_NAME = os.getenv("APP_NAME", "FINMARKET Kart Essentials").strip()
APP_VERSION = os.getenv("APP_VERSION", "1.0.0").strip()
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("finmarket.api")

API_PREFIX = os.getenv("API_PREFIX", "/api/v1").strip().rstrip("/")
if not API_PREFIX.startswith("/"):
    API_PREFIX = f"/{API_PREFIX}"
if API_PREFIX == "/":
    raise RuntimeError("API_PREFIX cannot be '/'. Use /api/v1.")

API_HOST = os.getenv("API_HOST", "127.0.0.1").strip() or "127.0.0.1"
try:
    API_PORT = int(os.getenv("API_PORT", "8000"))
except ValueError as exc:
    raise RuntimeError("API_PORT must be a valid integer.") from exc
if not 1 <= API_PORT <= 65535:
    raise RuntimeError("API_PORT must be between 1 and 65535.")

STREAMLIT_PUBLIC_URL = os.getenv(
    "STREAMLIT_PUBLIC_URL", "http://127.0.0.1:8501"
).strip().rstrip("/")

# Optional legacy HTML directories. Streamlit is the primary storefront.
FRONTEND_DIR = PROJECT_ROOT / "frontend"
PAGES_DIR = FRONTEND_DIR / "pages"
STATIC_DIR = FRONTEND_DIR / "static"
HAS_LEGACY_PAGES = PAGES_DIR.is_dir()
HAS_STATIC_FILES = STATIC_DIR.is_dir()

# -----------------------------------------------------------------------------
# 2. Database connection (existing FINMARKET SQLAlchemy engine)
# -----------------------------------------------------------------------------
try:
    from backend.database.connection import engine
except Exception as exc:
    logger.exception("Could not import the FINMARKET database engine.")
    raise RuntimeError(
        "Unable to initialize the database engine. Check .env DB_HOST, DB_PORT, "
        "DB_NAME, DB_USER and DB_PASSWORD, and backend/database/connection.py."
    ) from exc


def database_status() -> tuple[bool, str | None]:
    """Check MySQL availability without preventing API startup."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except SQLAlchemyError as exc:
        logger.warning("MySQL is not currently reachable: %s", exc)
        return False, str(exc)
    except Exception as exc:  # defensive: keep readiness endpoint informative
        logger.exception("Unexpected database connectivity error.")
        return False, str(exc)

# -----------------------------------------------------------------------------
# 3. ZITADEL OAuth settings (Swagger OAuth and public frontend configuration)
# -----------------------------------------------------------------------------
ZITADEL_ISSUER = os.getenv("ZITADEL_ISSUER", "").strip().rstrip("/")
ZITADEL_CLIENT_ID = (
    os.getenv("ZITADEL_SWAGGER_CLIENT_ID", "").strip()
    or os.getenv("ZITADEL_PUBLIC_CLIENT_ID", "").strip()
    or os.getenv("ZITADEL_CLIENT_ID", "").strip()
)
ZITADEL_AUTHORIZATION_URL = (
    f"{ZITADEL_ISSUER}/oauth/v2/authorize" if ZITADEL_ISSUER else ""
)
ZITADEL_TOKEN_URL = (
    f"{ZITADEL_ISSUER}/oauth/v2/token" if ZITADEL_ISSUER else ""
)
ZITADEL_AUDIENCE_SCOPE = (
    os.getenv("ZITADEL_API_AUDIENCE_SCOPE", "").strip()
    or os.getenv("ZITADEL_AUDIENCE_SCOPE", "").strip()
)
ZITADEL_SWAGGER_REDIRECT_URI = os.getenv(
    "ZITADEL_SWAGGER_REDIRECT_URI",
    f"http://127.0.0.1:{API_PORT}/docs/oauth2-redirect",
).strip()
ZITADEL_FRONTEND_REDIRECT_URI = os.getenv(
    "ZITADEL_REDIRECT_URI", "http://127.0.0.1:8501"
).strip()

ZITADEL_SCOPES = os.getenv(
    "ZITADEL_SCOPES", "openid profile email"
).split()
if ZITADEL_AUDIENCE_SCOPE:
    ZITADEL_SCOPES.append(ZITADEL_AUDIENCE_SCOPE)
ZITADEL_SCOPES = list(dict.fromkeys(scope for scope in ZITADEL_SCOPES if scope))

# -----------------------------------------------------------------------------
# 4. Session and CORS settings
# -----------------------------------------------------------------------------
SESSION_SECRET = os.getenv("SESSION_SECRET", "").strip()
if not SESSION_SECRET or SESSION_SECRET.startswith("CHANGE_ME"):
    if APP_ENV in {"production", "prod", "staging"}:
        raise RuntimeError(
            "Set a strong SESSION_SECRET in .env before running outside development."
        )
    SESSION_SECRET = secrets.token_urlsafe(48)
    logger.warning(
        "Using temporary development SESSION_SECRET. Set SESSION_SECRET in .env "
        "to keep sessions stable across restarts."
    )

# Starlette's SessionMiddleware requires a Literal type, not a general str.
SameSiteType = Literal["lax", "strict", "none"]

SESSION_SAME_SITE_RAW = os.getenv(
    "SESSION_SAME_SITE",
    "lax",
).strip().lower()

if SESSION_SAME_SITE_RAW not in ("lax", "strict", "none"):
    raise RuntimeError(
        "SESSION_SAME_SITE must be lax, strict or none."
    )

# Safe after the runtime validation above; this also satisfies Pylance.
SESSION_SAME_SITE = cast(
    SameSiteType,
    SESSION_SAME_SITE_RAW,
)
SESSION_HTTPS_ONLY = os.getenv("SESSION_HTTPS_ONLY", "false").lower() in {
    "1", "true", "yes", "on"
}

DEFAULT_CORS = (
    "http://127.0.0.1:8501,http://localhost:8501,"
    "http://127.0.0.1:4200,http://localhost:4200"
)
ALLOWED_ORIGINS = [
    value.strip()
    for value in os.getenv("CORS_ALLOWED_ORIGINS", DEFAULT_CORS).split(",")
    if value.strip()
]

# -----------------------------------------------------------------------------
# 5. FastAPI app and middleware
# -----------------------------------------------------------------------------
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "FINMARKET Kart Essentials commerce API. MySQL-backed catalogue, "
        "cart, customer, delivery, order and payment services. "
        "Authentication is integrated with ZITADEL."
    ),
    docs_url=None,  # custom Swagger below enables ZITADEL OAuth + PKCE
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site=SESSION_SAME_SITE,
    https_only=SESSION_HTTPS_ONLY,
)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Optional project middleware. A missing optional middleware must not mask
# the real API import error, but these files exist in the supplied project.
try:
    from backend.middleware.request_id import RequestIDMiddleware
    from backend.middleware.security_headers import SecurityHeadersMiddleware
    from backend.middleware.timing import RequestTimingMiddleware

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
except ImportError:
    logger.exception("Optional FINMARKET middleware could not be loaded.")

# Static files are mounted only when the legacy assets folder exists.
if HAS_STATIC_FILES:
    from fastapi.staticfiles import StaticFiles

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.info("No legacy frontend/static folder found; skipping static mount.")

# -----------------------------------------------------------------------------
# 6. Register existing commerce API router
# -----------------------------------------------------------------------------
try:
    from backend.api.v1.router import router as commerce_router
except Exception as exc:
    logger.exception("Unable to import backend.api.v1.router.")
    raise RuntimeError(
        "Could not load FINMARKET API routes. Check backend/api/v1/router.py "
        "and the imports used by its account, admin, cart, catalog, delivery, "
        "orders and payments routers."
    ) from exc

app.include_router(commerce_router, prefix=API_PREFIX)
logger.info("FINMARKET commerce routes registered under %s", API_PREFIX)

# -----------------------------------------------------------------------------
# 7. Storefront navigation: FastAPI stays on 8000; Streamlit runs on 8501
# -----------------------------------------------------------------------------
def storefront_redirect() -> RedirectResponse:
    return RedirectResponse(url=STREAMLIT_PUBLIC_URL or "/docs", status_code=307)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return storefront_redirect()


@app.get("/store", include_in_schema=False)
async def store() -> RedirectResponse:
    return storefront_redirect()


@app.get("/login", include_in_schema=False)
@app.get("/account", include_in_schema=False)
@app.get("/cart", include_in_schema=False)
@app.get("/checkout", include_in_schema=False)
@app.get("/orders", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
async def storefront_pages() -> RedirectResponse:
    # Streamlit owns these pages in this deployment. These aliases are kept
    # for old bookmarks and must not depend on optional HTML template folders.
    return storefront_redirect()

# -----------------------------------------------------------------------------
# 8. Public ZITADEL configuration endpoint used by clients
# -----------------------------------------------------------------------------
@app.get(f"{API_PREFIX}/auth/config", tags=["Authentication"])
async def public_auth_config() -> dict[str, Any]:
    if not ZITADEL_ISSUER or not ZITADEL_CLIENT_ID:
        return {
            "success": False,
            "configured": False,
            "detail": "Set ZITADEL_ISSUER and ZITADEL_CLIENT_ID in .env.",
        }
    return {
        "success": True,
        "configured": True,
        "issuer": ZITADEL_ISSUER,
        "client_id": ZITADEL_CLIENT_ID,
        "authorization_url": ZITADEL_AUTHORIZATION_URL,
        "token_url": ZITADEL_TOKEN_URL,
        "redirect_uri": ZITADEL_FRONTEND_REDIRECT_URI,
        "swagger_redirect_uri": ZITADEL_SWAGGER_REDIRECT_URI,
        "scopes": ZITADEL_SCOPES,
        "flow": "authorization_code",
        "pkce": "S256",
    }

@app.get("/auth/login", include_in_schema=False)
async def auth_login() -> RedirectResponse:
    return storefront_redirect()

# -----------------------------------------------------------------------------
# 9. Health, readiness and route diagnostics
# -----------------------------------------------------------------------------
@app.get("/health", tags=["System"])
@app.get(f"{API_PREFIX}/system/health", tags=["System"])
async def health() -> dict[str, Any]:
    return {
        "success": True,
        "status": "healthy",
        "application": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/ready", tags=["System"])
@app.get(f"{API_PREFIX}/system/ready", tags=["System"])
async def readiness() -> JSONResponse:
    connected, error = database_status()
    return JSONResponse(
        status_code=200 if connected else 503,
        content={
            "success": connected,
            "status": "ready" if connected else "degraded",
            "database": {
                "connected": connected,
                "message": "MySQL connected." if connected else "MySQL is unavailable.",
            },
        },
    )

@app.get(f"{API_PREFIX}/system/routes", include_in_schema=False)
async def route_diagnostics() -> dict[str, Any]:
    route_list: list[dict[str, Any]] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        methods = getattr(route, "methods", None)
        route_list.append({
            "path": path,
            "methods": sorted(methods) if methods else [],
            "name": getattr(route, "name", None),
        })
    return {"success": True, "count": len(route_list), "routes": route_list}

# -----------------------------------------------------------------------------
# 10. Swagger OpenAPI: replace HTTP Bearer schemes with ZITADEL OAuth2
# -----------------------------------------------------------------------------
def oauth_scope_descriptions() -> dict[str, str]:
    return {scope: f"FINMARKET API access: {scope}" for scope in ZITADEL_SCOPES}


def is_bearer_scheme(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and str(value.get("type", "")).lower() == "http"
        and str(value.get("scheme", "")).lower() == "bearer"
    )


def build_oauth_openapi() -> dict[str, Any]:
    """Return OpenAPI with ZITADEL Authorization Code + PKCE for Swagger."""
    if not ZITADEL_ISSUER or not ZITADEL_CLIENT_ID:
        raise RuntimeError("Configure ZITADEL_ISSUER and ZITADEL_CLIENT_ID in .env.")

    schema = deepcopy(app.openapi())
    components = schema.setdefault("components", {})
    schemes = components.setdefault("securitySchemes", {})
    bearer_names = {name for name, value in schemes.items() if is_bearer_scheme(value)}
    bearer_names.update(name for name in ("HTTPBearer", "BearerAuth", "Bearer") if name in schemes)
    for name in bearer_names:
        schemes.pop(name, None)

    scopes = oauth_scope_descriptions()
    schemes["ZitadelOAuth"] = {
        "type": "oauth2",
        "flows": {
            "authorizationCode": {
                "authorizationUrl": ZITADEL_AUTHORIZATION_URL,
                "tokenUrl": ZITADEL_TOKEN_URL,
                "scopes": scopes,
            }
        },
    }
    oauth_requirement = {"ZitadelOAuth": list(scopes)}

    # Update per-operation security entries which previously used HTTPBearer.
    paths = schema.get("paths", {})
    if isinstance(paths, dict):
        for path_item in paths.values():
            if not isinstance(path_item, dict):
                continue
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                security = operation.get("security")
                if not isinstance(security, list):
                    continue
                new_security: list[dict[str, Any]] = []
                replaced = False
                for requirement in security:
                    if not isinstance(requirement, dict):
                        continue
                    if bearer_names.intersection(requirement):
                        if not replaced:
                            new_security.append(oauth_requirement)
                            replaced = True
                    else:
                        new_security.append(requirement)
                operation["security"] = new_security

    global_security = schema.get("security")
    if isinstance(global_security, list):
        new_global: list[dict[str, Any]] = []
        replaced = False
        for requirement in global_security:
            if not isinstance(requirement, dict):
                continue
            if bearer_names.intersection(requirement):
                if not replaced:
                    new_global.append(oauth_requirement)
                    replaced = True
            else:
                new_global.append(requirement)
        schema["security"] = new_global

    schema.setdefault("info", {})["title"] = f"{APP_NAME} - ZITADEL OAuth API"
    return schema

@app.get("/oauth-openapi.json", include_in_schema=False)
async def oauth_openapi() -> JSONResponse:
    try:
        return JSONResponse(content=build_oauth_openapi())
    except Exception as exc:
        logger.exception("Could not build OAuth OpenAPI schema.")
        return JSONResponse(status_code=503, content={"detail": str(exc)})

@app.get("/docs", include_in_schema=False)
async def swagger_docs() -> Response:
    if not ZITADEL_ISSUER or not ZITADEL_CLIENT_ID:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Configure ZITADEL_ISSUER and ZITADEL_CLIENT_ID in .env to enable OAuth Swagger."
            },
        )
    return get_swagger_ui_html(
        openapi_url="/oauth-openapi.json",
        title=f"{APP_NAME} - API Documentation",
        oauth2_redirect_url="/docs/oauth2-redirect",
        init_oauth={
            "clientId": ZITADEL_CLIENT_ID,
            "appName": APP_NAME,
            "scopes": " ".join(ZITADEL_SCOPES),
            "usePkceWithAuthorizationCodeGrant": True,
        },
        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
        },
    )

@app.get("/docs/oauth2-redirect", include_in_schema=False)
async def swagger_oauth_redirect() -> HTMLResponse:
    return get_swagger_ui_oauth2_redirect_html()

# -----------------------------------------------------------------------------
# 11. Favicon and exception handlers
# -----------------------------------------------------------------------------
@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> JSONResponse:
    return JSONResponse(status_code=204, content=None)

@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "detail": exc.detail},
        headers=exc.headers,
    )

@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "An unexpected server error occurred."},
    )

# -----------------------------------------------------------------------------
# 12. Startup diagnostics and direct execution
# -----------------------------------------------------------------------------
logger.info("%s configured", APP_NAME)
logger.info("Project root: %s", PROJECT_ROOT)
logger.info("API: http://%s:%s%s", API_HOST, API_PORT, API_PREFIX)
logger.info("Swagger: http://%s:%s/docs", API_HOST, API_PORT)
logger.info("Streamlit storefront: %s", STREAMLIT_PUBLIC_URL)
logger.info("Legacy HTML frontend present: %s", HAS_LEGACY_PAGES)
logger.info("ZITADEL configured: %s", bool(ZITADEL_ISSUER and ZITADEL_CLIENT_ID))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=APP_ENV not in {"production", "prod"},
        log_level=LOG_LEVEL.lower(),
    )
