
"""
FINMARKET KART ESSENTIALS
=========================

Main application entry point.

Integrations:
    - SAMLAPA FinMkt FastAPI application factory
    - SAMLAPA Settings configuration
    - _core.ini and fastapi.ini
    - MySQL / SQLAlchemy
    - Existing FINMARKET API routers
    - ZITADEL OAuth2 / OpenID Connect
    - Swagger OAuth2 Authorization Code + PKCE
    - Storefront HTML, CSS, JavaScript and images
    - Session middleware
    - Health and readiness endpoints

Run from project root:

uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
"""

from __future__ import annotations

import logging
import os

from copy import deepcopy
from dataclasses import is_dataclass, replace
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Literal, Optional, cast

from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BACKEND_DIR = PROJECT_ROOT / "backend"

API_DIR = BACKEND_DIR / "api"
API_V1_DIR = API_DIR / "v1"

DATABASE_DIR = BACKEND_DIR / "database"
MODELS_DIR = BACKEND_DIR / "models"

FRONTEND_DIR = PROJECT_ROOT / "frontend"

PAGES_DIR = FRONTEND_DIR / "pages"
COMPONENTS_DIR = FRONTEND_DIR / "components"
TEMPLATES_DIR = FRONTEND_DIR / "templates"

STATIC_DIR = FRONTEND_DIR / "static"

CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"

STATIC_IMAGES_DIR = STATIC_DIR / "images"
FRONTEND_IMAGES_DIR = FRONTEND_DIR / "images"

UPLOADS_DIR = Path(
    os.getenv(
        "UPLOADS_DIR",
        str(PROJECT_ROOT / "uploads"),
    )
).resolve()


# ============================================================
# 2. ENVIRONMENT
# ============================================================

load_dotenv(
    PROJECT_ROOT / ".env",
    override=False,
)

APP_ENV = (
    os.getenv("FINMKT_ENV")
    or os.getenv("APP_ENV")
    or "dev"
).strip().lower()

APP_ENV = {
    "development": "dev",
    "production": "prod",
}.get(APP_ENV, APP_ENV)

# SAMLAPA's config loader selects config/application/<FINMKT_ENV>.
os.environ.setdefault("FINMKT_ENV", APP_ENV)


# ============================================================
# 3. LOGGING
# ============================================================

logging.basicConfig(
    level=os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).upper(),
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)

logger = logging.getLogger("finmarket")


# ============================================================
# 4. DIRECTORY VALIDATION
# ============================================================

REQUIRED_DIRECTORIES = (
    BACKEND_DIR,
    API_V1_DIR,
    DATABASE_DIR,
    MODELS_DIR,
    FRONTEND_DIR,
    PAGES_DIR,
    STATIC_DIR,
)

for directory in REQUIRED_DIRECTORIES:

    if not directory.is_dir():

        raise RuntimeError(
            f"Required FINMARKET directory is missing: {directory}"
        )


if not (PAGES_DIR / "index.html").is_file():

    raise RuntimeError(
        f"Storefront homepage not found: {PAGES_DIR / 'index.html'}"
    )


# ============================================================
# 5. SAMLAPA FINMKT IMPORTS
# ============================================================

"""
Use the actual SAMLAPA configuration system.

Do not pass configparser.ConfigParser() into the
configuration bridge.

The configuration bridge expects finmkt.config.Settings.
"""

try:

    from finmkt.config import get_settings

    from finmkt.fastapi import (
        AppConfig,
        create_app,
    )

    from finmkt.fastapi.support.config_bridge import (
        app_config_from_settings,
        server_config_from_settings,
        uvicorn_kwargs_from_settings,
    )

except ImportError as exc:

    logger.exception(
        "SAMLAPA FinMkt package import failed."
    )

    raise RuntimeError(
        "Unable to import SAMLAPA FinMkt packages. "
        "Verify the editable installation of "
        "samlapa/io/finmkt/fastapi/src."
    ) from exc


# ============================================================
# 6. LOAD SAMLAPA SETTINGS
# ============================================================

try:

    finmkt_settings = get_settings()

except Exception as exc:

    logger.exception(
        "Unable to load FinMkt settings."
    )

    raise RuntimeError(
        "Could not load SAMLAPA configuration. "
        "Check config/application/dev/_core.ini "
        "and config/application/dev/fastapi.ini."
    ) from exc


# ============================================================
# 7. CONVERT SETTINGS TO APP CONFIGURATION
# ============================================================

try:

    APP_CONFIG: AppConfig = app_config_from_settings(
        finmkt_settings
    )

    SERVER_CONFIG = server_config_from_settings(
        finmkt_settings
    )

except Exception as exc:

    logger.exception(
        "SAMLAPA configuration bridge failed."
    )

    raise RuntimeError(
        "Unable to convert SAMLAPA Settings into "
        "AppConfig and ServerConfig."
    ) from exc


# ============================================================
# 8. APPLICATION CONFIGURATION
# ============================================================

APP_NAME = os.getenv(
    "APP_NAME",
    APP_CONFIG.title or "FINMARKET Kart Essentials",
)

APP_VERSION = os.getenv(
    "APP_VERSION",
    APP_CONFIG.version or "1.0.0",
)

APP_DESCRIPTION = (
    "FINMARKET Kart Essentials commerce platform. "
    "Product catalogue, inventory, customers, cart, "
    "checkout, orders, payments and delivery management. "
    "Authentication integrated with ZITADEL OpenID Connect."
)

API_PREFIX = (
    os.getenv(
        "API_PREFIX",
        APP_CONFIG.url_prefix or "/api/v1",
    )
    .strip()
    .rstrip("/")
)

if not API_PREFIX.startswith("/") or API_PREFIX == "/":

    raise RuntimeError(
        "API_PREFIX must be a valid path such as /api/v1."
    )


SERVER_HOST = os.getenv(
    "API_HOST",
    SERVER_CONFIG.host,
)

try:

    SERVER_PORT = int(
        os.getenv(
            "API_PORT",
            str(SERVER_CONFIG.port),
        )
    )

except ValueError as exc:

    raise RuntimeError(
        "API_PORT must be an integer."
    ) from exc


# ============================================================
# 9. UPDATE SAMLAPA APP CONFIG
# ============================================================

def update_app_config(
    config: AppConfig,
    updates: dict[str, Any],
) -> AppConfig:
    """
    Update AppConfig without changing its original type.

    Supports dataclass and Pydantic configuration models.
    """

    if is_dataclass(config):

        return replace(
            config,
            **updates,
        )

    if hasattr(config, "model_copy"):

        return config.model_copy(
            update=updates
        )

    if hasattr(config, "copy"):

        return config.copy(
            update=updates
        )

    raise TypeError(
        "Unsupported SAMLAPA AppConfig implementation."
    )


# The FastAPI application factory reads CORS from AppConfig.
# Include both local Angular origins and the same-origin Python storefront.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:4200,http://localhost:4200,"
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if origin.strip()
]

APP_CONFIG = update_app_config(
    APP_CONFIG,
    {
        "title": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "url_prefix": API_PREFIX,
        "cors_origins": CORS_ALLOWED_ORIGINS,
        "cors_allow_credentials": True,
        "cors_allow_methods": [
            "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"
        ],
        "cors_allow_headers": ["*"],

        # We register OAuth-aware Swagger ourselves below.
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": "/openapi.json",
    },
)


# ============================================================
# 10. DATABASE CONNECTION
# ============================================================

try:

    from backend.database.connection import engine

except ImportError as exc:

    logger.exception(
        "Unable to import FINMARKET database engine."
    )

    raise RuntimeError(
        "Check backend/database/connection.py "
        "and database environment variables."
    ) from exc


def check_database_connection() -> tuple[bool, Optional[str]]:
    """
    Verify the existing MySQL connection.

    Does not create or modify tables.
    """

    try:

        with engine.connect() as connection:

            connection.execute(
                text("SELECT 1")
            )

        return True, None

    except SQLAlchemyError as exc:

        logger.exception(
            "MySQL database connection failed."
        )

        return False, str(exc)

    except Exception as exc:

        logger.exception(
            "Unexpected database error."
        )

        return False, str(exc)


# ============================================================
# 11. SQLALCHEMY MODEL REGISTRATION
# ============================================================

def register_models() -> None:
    """
    Register SQLAlchemy models.

    Database migrations remain responsible for schema creation.
    """

    try:

        import backend.models  # noqa: F401

    except Exception:

        logger.exception(
            "FINMARKET model registration failed."
        )

        raise


register_models()


# ============================================================
# 12. ZITADEL CONFIGURATION
# ============================================================

ZITADEL_ISSUER = os.getenv(
    "ZITADEL_ISSUER",
    "",
).strip().rstrip("/")


# Accept the variable names used by the existing project templates.
# This is a public SPA client ID; never expose a client secret.
ZITADEL_CLIENT_ID = (
    os.getenv("ZITADEL_PUBLIC_CLIENT_ID")
    or os.getenv("ZITADEL_CLIENT_ID")
    or os.getenv("ZITADEL_SWAGGER_CLIENT_ID")
    or ""
).strip()


ZITADEL_SWAGGER_CLIENT_ID = os.getenv(
    "ZITADEL_SWAGGER_CLIENT_ID",
    ZITADEL_CLIENT_ID,
).strip()


ZITADEL_AUTHORIZATION_URL = (
    f"{ZITADEL_ISSUER}/oauth/v2/authorize"
    if ZITADEL_ISSUER
    else ""
)


ZITADEL_TOKEN_URL = (
    f"{ZITADEL_ISSUER}/oauth/v2/token"
    if ZITADEL_ISSUER
    else ""
)


ZITADEL_AUDIENCE_SCOPE = os.getenv(
    "ZITADEL_AUDIENCE_SCOPE",
    os.getenv(
        "ZITADEL_API_AUDIENCE_SCOPE",
        "",
    ),
).strip()

# backend.auth.zitadel reads ZITADEL_API_AUDIENCE_SCOPE; keep both aliases aligned.
if ZITADEL_AUDIENCE_SCOPE:
    os.environ.setdefault(
        "ZITADEL_API_AUDIENCE_SCOPE",
        ZITADEL_AUDIENCE_SCOPE,
    )


ZITADEL_SWAGGER_SCOPES = (
    os.getenv(
        "ZITADEL_SWAGGER_SCOPES",
        "openid profile email",
    ).split()
)


if ZITADEL_AUDIENCE_SCOPE:

    ZITADEL_SWAGGER_SCOPES.append(
        ZITADEL_AUDIENCE_SCOPE
    )


ZITADEL_SWAGGER_SCOPES = list(
    dict.fromkeys(
        ZITADEL_SWAGGER_SCOPES
    )
)


# ============================================================
# 13. PUBLIC APPLICATION URLS
# ============================================================

PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    f"http://127.0.0.1:{SERVER_PORT}",
).strip().rstrip("/")


ZITADEL_FRONTEND_REDIRECT_URI = os.getenv(
    "ZITADEL_FRONTEND_REDIRECT_URI",
    f"{PUBLIC_BASE_URL}/auth/callback",
).strip()


SWAGGER_OAUTH_REDIRECT_URI = os.getenv(
    "ZITADEL_SWAGGER_REDIRECT_URI",
    f"{PUBLIC_BASE_URL}/docs/oauth2-redirect",
).strip()


# ============================================================
# 14. SESSION CONFIGURATION
# ============================================================

SESSION_SECRET = (
    os.getenv("SESSION_SECRET")
    or os.getenv("COOKIE_SECRET")
    or ""
).strip()


if not SESSION_SECRET:

    if APP_ENV in {
        "prod",
        "production",
        "qa",
        "staging",
    }:

        raise RuntimeError(
            "SESSION_SECRET is required in production."
        )

    SESSION_SECRET = (
        "LOCAL-ONLY-CHANGE-THIS-SESSION-SECRET"
    )

    logger.warning(
        "Using development-only SESSION_SECRET."
    )


SESSION_SAME_SITE_VALUE = (
    os.getenv(
        "SESSION_SAME_SITE",
        "lax",
    )
    .strip()
    .lower()
)


if SESSION_SAME_SITE_VALUE not in {
    "lax",
    "strict",
    "none",
}:

    raise RuntimeError(
        "SESSION_SAME_SITE must be lax, strict or none."
    )


# FIX: Explicit Literal typing for Starlette/Pylance.
SESSION_SAME_SITE = cast(
    Literal["lax", "strict", "none"],
    SESSION_SAME_SITE_VALUE,
)


SESSION_HTTPS_ONLY = (
    os.getenv(
        "SESSION_HTTPS_ONLY",
        "false",
    ).strip().lower()
    in {"1", "true", "yes", "on"}
)


if SESSION_SAME_SITE == "none" and not SESSION_HTTPS_ONLY:

    raise RuntimeError(
        "SESSION_HTTPS_ONLY must be true when "
        "SESSION_SAME_SITE is none."
    )


# ============================================================
# 15. APPLICATION STARTUP
# ============================================================

def application_startup(
    application: FastAPI,
) -> None:
    """SAMLAPA application startup callback."""

    logger.info("=" * 65)

    logger.info(
        "Starting %s",
        APP_NAME,
    )

    logger.info(
        "Version: %s",
        APP_VERSION,
    )

    logger.info(
        "Environment: %s",
        APP_ENV,
    )

    logger.info(
        "API prefix: %s",
        API_PREFIX,
    )

    logger.info(
        "Server: %s:%s",
        SERVER_HOST,
        SERVER_PORT,
    )

    connected, error = check_database_connection()

    if connected:

        logger.info(
            "MySQL database connected successfully."
        )

    else:

        logger.error(
            "MySQL database unavailable: %s",
            error,
        )

    if ZITADEL_ISSUER and ZITADEL_CLIENT_ID:

        logger.info(
            "ZITADEL OAuth configuration detected."
        )

    else:

        logger.warning(
            "ZITADEL public OAuth configuration is incomplete."
        )

    logger.info(
        "FINMARKET application startup complete."
    )

    logger.info("=" * 65)


def application_shutdown(
    application: FastAPI,
) -> None:
    """SAMLAPA application shutdown callback."""

    logger.info(
        "Shutting down %s",
        APP_NAME,
    )


# ============================================================
# 16. CENTRAL API ROUTER
# ============================================================

try:

    from backend.api.v1.router import (
        router as core_api_router,
    )

except ImportError as exc:

    logger.exception(
        "Unable to import FINMARKET central API router."
    )

    raise RuntimeError(
        "Check backend/api/v1/router.py and its dependencies."
    ) from exc


# ============================================================
# 17. CREATE APPLICATION USING SAMLAPA FACTORY
# ============================================================

try:

    app = create_app(
        config=APP_CONFIG,

        routers=[
            core_api_router,
        ],

        on_startup=[
            application_startup,
        ],

        on_shutdown=[
            application_shutdown,
        ],
    )

except Exception as exc:

    logger.exception(
        "SAMLAPA FastAPI application factory failed."
    )

    raise RuntimeError(
        "Unable to create FINMARKET application using "
        "finmkt.fastapi.create_app()."
    ) from exc


# ============================================================
# 18. APPLICATION STATE
# ============================================================

app.title = APP_NAME
app.version = APP_VERSION
app.description = APP_DESCRIPTION

app.state.finmkt_settings = finmkt_settings
app.state.finmkt_config = APP_CONFIG
app.state.finmkt_server_config = SERVER_CONFIG
app.state.finmkt_environment = APP_ENV

app.state.finmkt_config_dir = (
    PROJECT_ROOT
    / "config"
    / "application"
    / APP_ENV
)


# ============================================================
# 19. SESSION MIDDLEWARE
# ============================================================

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site=SESSION_SAME_SITE,
    https_only=SESSION_HTTPS_ONLY,
    session_cookie="finmarket_session",
    max_age=60 * 60 * 24 * 7,
)


# ============================================================
# 20. FRONTEND TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory=str(FRONTEND_DIR)
)


# ============================================================
# 21. STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=str(STATIC_DIR),
        check_dir=True,
    ),
    name="static",
)


# The database seed stores category image URLs under /images/...
# Serve that public URL prefix from the same checked-in image directory
# used by /static/images. The previous frontend/images path did not exist
# in this archive, which caused seeded category images to return 404.
if STATIC_IMAGES_DIR.is_dir():

    app.mount(
        "/images",
        StaticFiles(
            directory=str(STATIC_IMAGES_DIR),
            check_dir=True,
        ),
        name="catalog-images",
    )


UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(
        directory=str(UPLOADS_DIR),
        check_dir=True,
    ),
    name="uploads",
)


# ============================================================
# 22. TEMPLATE RENDERING
# ============================================================

def render_page(
    request: Request,
    filename: str,
    extra: Optional[dict[str, Any]] = None,
) -> HTMLResponse:
    """
    Render frontend/pages HTML files.

    Prevents path traversal outside the pages directory.
    """

    page_root = PAGES_DIR.resolve()

    candidate = (
        page_root / filename
    ).resolve()

    if not candidate.is_relative_to(page_root):

        raise StarletteHTTPException(
            status_code=404,
            detail="Page not found.",
        )

    if not candidate.is_file():

        raise StarletteHTTPException(
            status_code=404,
            detail=f"Page not found: {filename}",
        )

    context: dict[str, Any] = {
        "request": request,
        "site_name": APP_NAME,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "current_year": datetime.now(
            timezone.utc
        ).year,
        "api_prefix": API_PREFIX,
    }

    if extra:

        context.update(extra)

    return templates.TemplateResponse(
        request=request,
        name=f"pages/{filename}",
        context=context,
    )


# ============================================================
# 23. STOREFRONT ROUTES
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse,
    name="home",
)
async def home_page(
    request: Request,
) -> HTMLResponse:

    return render_page(
        request,
        "index.html",
    )


@app.get(
    "/products",
    response_class=HTMLResponse,
    name="products",
)
async def products_page(
    request: Request,
) -> HTMLResponse:
    """Render the storefront catalogue as a directly addressable page."""

    return render_page(
        request,
        "index.html",
    )


@app.get(
    "/login",
    response_class=HTMLResponse,
    name="login",
)
async def login_page(
    request: Request,
) -> HTMLResponse:

    return render_page(
        request,
        "login.html",
    )


@app.get(
    "/auth/callback",
    response_class=HTMLResponse,
    name="zitadel_frontend_callback",
)
async def frontend_auth_callback(
    request: Request,
) -> HTMLResponse:
    """
    Serve the frontend callback handler.

    The frontend JavaScript must:
        1. Read code and state from the URL.
        2. Validate state against the original login request.
        3. Retrieve the stored PKCE code verifier.
        4. Exchange the code at the ZITADEL token endpoint.
        5. Validate and establish authentication state.

    This endpoint does not independently authenticate the user.
    """

    if "error" in request.query_params:

        error = request.query_params.get(
            "error",
            "authentication_failed",
        )

        description = request.query_params.get(
            "error_description",
            "ZITADEL authentication was unsuccessful.",
        )

        return render_page(
            request,
            "login.html",
            {
                "auth_error": error,
                "auth_error_description": description,
                "auth_callback": True,
            },
        )

    return render_page(
        request,
        "login.html",
        {
            "auth_callback": True,
        },
    )


@app.get(
    "/account",
    response_class=HTMLResponse,
    name="customer_account",
)
async def customer_account_page(
    request: Request,
) -> HTMLResponse:

    return render_page(
        request,
        "account.html",
    )


@app.get(
    "/cart",
    response_class=HTMLResponse,
    name="cart",
)
async def cart_page(
    request: Request,
) -> HTMLResponse:

    return render_page(
        request,
        "cart.html",
    )


@app.get(
    "/checkout",
    response_class=HTMLResponse,
    name="checkout",
)
async def checkout_page(
    request: Request,
) -> HTMLResponse:

    return render_page(
        request,
        "checkout.html",
    )


@app.get(
    "/orders",
    response_class=HTMLResponse,
    name="orders",
)
async def orders_page(
    request: Request,
) -> HTMLResponse:

    return render_page(
        request,
        "orders.html",
    )


@app.get(
    "/admin",
    response_class=HTMLResponse,
    name="admin",
)
async def admin_page(
    request: Request,
) -> HTMLResponse:

    return render_page(
        request,
        "admin.html",
    )


@app.get(
    "/product/{product_id}",
    response_class=HTMLResponse,
    name="product_detail",
)
async def product_detail_page(
    request: Request,
    product_id: int,
) -> HTMLResponse:

    return render_page(
        request,
        "product_detail.html",
        {
            "product_id": product_id,
        },
    )


# ============================================================
# 24. ZITADEL OAUTH HELPERS
# ============================================================

def get_oauth_scopes() -> dict[str, str]:

    return {
        scope: f"FINMARKET authorization scope: {scope}"
        for scope in ZITADEL_SWAGGER_SCOPES
    }


def is_http_bearer_scheme(
    value: Any,
) -> bool:

    return (
        isinstance(value, dict)
        and str(
            value.get("type", "")
        ).lower() == "http"
        and str(
            value.get("scheme", "")
        ).lower() == "bearer"
    )


# ============================================================
# 25. OAUTH OPENAPI GENERATION
# ============================================================

def generate_oauth_openapi() -> dict[str, Any]:
    """
    Generate OpenAPI with ZITADEL OAuth2 Authorization Code.

    Swagger uses PKCE.

    No client secret is exposed to the browser.
    """

    if not ZITADEL_ISSUER:

        raise RuntimeError(
            "ZITADEL_ISSUER is missing."
        )

    if not ZITADEL_SWAGGER_CLIENT_ID:

        raise RuntimeError(
            "ZITADEL_SWAGGER_CLIENT_ID is missing."
        )

    schema = deepcopy(
        app.openapi()
    )

    components = schema.setdefault(
        "components",
        {},
    )

    security_schemes = components.setdefault(
        "securitySchemes",
        {},
    )

    bearer_names = {
        name
        for name, definition in security_schemes.items()
        if is_http_bearer_scheme(definition)
    }

    bearer_names.update(
        name
        for name in (
            "HTTPBearer",
            "BearerAuth",
            "Bearer",
        )
        if name in security_schemes
    )

    for name in bearer_names:

        security_schemes.pop(
            name,
            None,
        )

    scopes = get_oauth_scopes()

    security_schemes["ZitadelOAuth"] = {
        "type": "oauth2",
        "flows": {
            "authorizationCode": {
                "authorizationUrl": ZITADEL_AUTHORIZATION_URL,
                "tokenUrl": ZITADEL_TOKEN_URL,
                "scopes": scopes,
            }
        },
    }

    oauth_requirement = {
        "ZitadelOAuth": list(scopes),
    }

    # Replace existing HTTP Bearer security requirements
    # with the ZITADEL OAuth2 requirement.

    for path_item in schema.get(
        "paths",
        {},
    ).values():

        if not isinstance(path_item, dict):
            continue

        for operation in path_item.values():

            if not isinstance(operation, dict):
                continue

            operation_security = operation.get(
                "security"
            )

            if not isinstance(
                operation_security,
                list,
            ):
                continue

            updated: list[dict[str, Any]] = []

            replaced = False

            for requirement in operation_security:

                if not isinstance(
                    requirement,
                    dict,
                ):
                    continue

                if bearer_names.intersection(
                    requirement
                ):

                    if not replaced:

                        updated.append(
                            oauth_requirement
                        )

                        replaced = True

                else:

                    updated.append(
                        requirement
                    )

            operation["security"] = updated

    # Replace global security if present.

    global_security = schema.get(
        "security"
    )

    if isinstance(
        global_security,
        list,
    ):

        updated_global: list[dict[str, Any]] = []

        replaced = False

        for requirement in global_security:

            if not isinstance(
                requirement,
                dict,
            ):
                continue

            if bearer_names.intersection(
                requirement
            ):

                if not replaced:

                    updated_global.append(
                        oauth_requirement
                    )

                    replaced = True

            else:

                updated_global.append(
                    requirement
                )

        schema["security"] = updated_global

    schema.setdefault(
        "info",
        {},
    )["title"] = (
        f"{APP_NAME} - ZITADEL OAuth API"
    )

    return schema


# ============================================================
# 26. OAUTH OPENAPI ENDPOINT
# ============================================================

@app.get(
    "/oauth-openapi.json",
    include_in_schema=False,
)
async def oauth_openapi():

    try:

        return JSONResponse(
            content=generate_oauth_openapi()
        )

    except Exception:

        logger.exception(
            "Unable to generate OAuth OpenAPI."
        )

        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "detail": (
                    "OAuth configuration is incomplete. "
                    "Check ZITADEL settings."
                ),
            },
        )


# ============================================================
# 27. SWAGGER OAUTH DOCUMENTATION
# ============================================================

def swagger_redirect_uri_for(request: Request) -> str:
    """Use the browser's exact origin for local Swagger OAuth redirects."""
    if APP_ENV in {"dev", "development", "local"}:
        return f"{str(request.base_url).rstrip('/')}/docs/oauth2-redirect"
    return SWAGGER_OAUTH_REDIRECT_URI


@app.get(
    "/docs",
    include_in_schema=False,
)
async def oauth_swagger_docs(request: Request):

    if (
        not ZITADEL_ISSUER
        or not ZITADEL_SWAGGER_CLIENT_ID
    ):

        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "detail": (
                    "Configure ZITADEL_ISSUER and "
                    "ZITADEL_SWAGGER_CLIENT_ID."
                ),
            },
        )

    return get_swagger_ui_html(
        openapi_url="/oauth-openapi.json",
        title=f"{APP_NAME} - OAuth Swagger",

        oauth2_redirect_url=swagger_redirect_uri_for(request),

        init_oauth={
            "clientId": ZITADEL_SWAGGER_CLIENT_ID,
            "appName": APP_NAME,
            "scopes": list(
                get_oauth_scopes()
            ),
            "usePkceWithAuthorizationCodeGrant": True,
        },

        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
        },
    )


@app.get(
    "/docs/oauth2-redirect",
    include_in_schema=False,
)
async def swagger_oauth_redirect():

    return get_swagger_ui_oauth2_redirect_html()


# ============================================================
# 28. PUBLIC ZITADEL CONFIGURATION
# ============================================================

def frontend_redirect_uri_for(request: Request) -> str:
    """
    Resolve the callback to the same origin as the storefront.

    During local development, localhost and 127.0.0.1 are different
    browser origins. The callback must match the origin where the
    login was started so sessionStorage retains the PKCE verifier.
    Register the exact callback URI in ZITADEL.
    """
    if APP_ENV in {"dev", "development", "local"}:
        origin = str(request.base_url).rstrip("/")
        return f"{origin}/auth/callback"

    return ZITADEL_FRONTEND_REDIRECT_URI


def frontend_oauth_scopes() -> list[str]:
    """
    Include the ZITADEL project audience needed by the API's JWT validator.
    """
    configured = os.getenv(
        "ZITADEL_FRONTEND_SCOPES",
        "openid profile email",
    ).split()

    audience_scope = (
        ZITADEL_AUDIENCE_SCOPE
        or os.getenv("ZITADEL_API_AUDIENCE_SCOPE", "").strip()
    )

    if "openid" not in configured:
        configured.insert(0, "openid")

    if audience_scope and audience_scope not in configured:
        configured.append(audience_scope)

    return list(dict.fromkeys(scope for scope in configured if scope))


def frontend_post_logout_redirect_uri_for(request: Request) -> str:
    """Return the exact local origin to which ZITADEL should send the user after logout."""
    if APP_ENV in {"dev", "development", "local"}:
        return f"{str(request.base_url).rstrip('/')}/"
    return os.getenv(
        "ZITADEL_POST_LOGOUT_REDIRECT_URI",
        f"{PUBLIC_BASE_URL}/",
    ).strip()


def auth_config_payload(request: Request) -> dict[str, Any]:
    """
    Public OAuth configuration for the storefront.
    Never expose client secrets.
    """
    return {
        "success": True,
        "provider": "zitadel",
        "issuer": ZITADEL_ISSUER,
        "client_id": ZITADEL_CLIENT_ID,
        "authorization_url": ZITADEL_AUTHORIZATION_URL,
        "token_url": ZITADEL_TOKEN_URL,
        "redirect_uri": frontend_redirect_uri_for(request),
        "post_logout_redirect_uri": frontend_post_logout_redirect_uri_for(request),
        "swagger_redirect_uri": swagger_redirect_uri_for(request),
        "scopes": frontend_oauth_scopes(),
        "flow": "authorization_code",
        "pkce": True,
        "pkce_method": "S256",
    }


# ============================================================
# 29. FRONTEND AUTH CONFIGURATION ROUTES
# ============================================================

AUTH_CONFIG_PATH = f"{API_PREFIX}/auth/config"

existing_paths = {
    getattr(route, "path", None)
    for route in app.routes
}


if AUTH_CONFIG_PATH not in existing_paths:

    @app.get(
        AUTH_CONFIG_PATH,
        tags=["Authentication"],
        name="public_zitadel_config",
    )
    async def public_auth_config(request: Request):

        if not ZITADEL_ISSUER or not ZITADEL_CLIENT_ID:

            raise StarletteHTTPException(
                status_code=503,
                detail="ZITADEL public client is not configured.",
            )

        return auth_config_payload(request)


existing_paths = {
    getattr(route, "path", None)
    for route in app.routes
}


if "/auth/config" not in existing_paths:

    @app.get(
        "/auth/config",
        include_in_schema=False,
        name="frontend_zitadel_config",
    )
    async def frontend_auth_config(request: Request):

        if not ZITADEL_ISSUER or not ZITADEL_CLIENT_ID:

            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "detail": "ZITADEL is not configured.",
                },
            )

        return auth_config_payload(request)


# ============================================================
# 30. AUTHENTICATION ENTRY POINT
# ============================================================

@app.get(
    "/auth/login",
    include_in_schema=False,
)
async def auth_login():

    return RedirectResponse(
        url="/login",
        status_code=302,
    )


# ============================================================
# 31. SYSTEM HEALTH
# ============================================================

@app.get(
    f"{API_PREFIX}/system/health",
    tags=["System"],
)
async def system_health():

    return {
        "success": True,
        "status": "healthy",
        "application": APP_NAME,
        "version": APP_VERSION,
        "environment": APP_ENV,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# ============================================================
# 32. DATABASE READINESS
# ============================================================

@app.get(
    f"{API_PREFIX}/system/ready",
    tags=["System"],
)
async def system_ready():

    connected, error = check_database_connection()

    return JSONResponse(
        status_code=(
            200 if connected else 503
        ),

        content={
            "success": connected,

            "status": (
                "ready" if connected else "degraded"
            ),

            "database": {
                "connected": connected,

                "message": (
                    "MySQL connected"
                    if connected
                    else "Database connection unavailable"
                ),
            },
        },
    )


# ============================================================
# 33. APPLICATION DIAGNOSTICS
# ============================================================

@app.get(
    f"{API_PREFIX}/system/info",
    tags=["System"],
)
async def system_info():

    return {
        "success": True,
        "application": APP_NAME,
        "version": APP_VERSION,
        "environment": APP_ENV,
        "api_prefix": API_PREFIX,
        "database": "MySQL",
        "authentication": "ZITADEL",
        "frontend": "enabled",
        "static_files": STATIC_DIR.is_dir(),
        "images": STATIC_IMAGES_DIR.is_dir(),
    }


@app.get(
    f"{API_PREFIX}/system/routes",
    tags=["System"],
    include_in_schema=False,
)
async def registered_routes():

    route_list = []

    for route in app.routes:

        path = getattr(
            route,
            "path",
            None,
        )

        if not path:
            continue

        methods = getattr(
            route,
            "methods",
            None,
        )

        route_list.append(
            {
                "path": path,

                "methods": (
                    sorted(methods)
                    if methods
                    else []
                ),

                "name": getattr(
                    route,
                    "name",
                    None,
                ),
            }
        )

    return {
        "success": True,
        "count": len(route_list),
        "routes": route_list,
    }


# ============================================================
# 34. FAVICON
# ============================================================

@app.get(
    "/favicon.ico",
    include_in_schema=False,
)
async def favicon():

    return HTMLResponse(
        content="",
        status_code=204,
    )


# ============================================================
# 35. HTTP EXCEPTION HANDLER
# ============================================================

@app.exception_handler(
    StarletteHTTPException
)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):

    path = request.url.path

    if (
        path == API_PREFIX
        or path.startswith(API_PREFIX + "/")
    ):

        return JSONResponse(
            status_code=exc.status_code,

            content={
                "success": False,
                "detail": exc.detail,
            },

            headers=exc.headers,
        )

    message = escape(
        str(exc.detail)
    )

    return HTMLResponse(
        status_code=exc.status_code,

        content=(
            "<!doctype html>"
            "<html lang='en'>"
            "<head>"
            "<meta charset='utf-8'>"
            f"<title>{exc.status_code} | FINMARKET</title>"
            "</head>"
            "<body>"
            "<main>"
            f"<h1>{exc.status_code} - Unable to complete your request</h1>"
            f"<p>{message}</p>"
            "<a href='/'>Return to FINMARKET</a>"
            "</main>"
            "</body>"
            "</html>"
        ),

        headers=exc.headers,
    )


# ============================================================
# 36. UNEXPECTED EXCEPTION HANDLER
# ============================================================

@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):

    logger.exception(
        "Unhandled exception at %s %s",
        request.method,
        request.url.path,
    )

    path = request.url.path

    if (
        path == API_PREFIX
        or path.startswith(API_PREFIX + "/")
    ):

        return JSONResponse(
            status_code=500,

            content={
                "success": False,
                "detail": (
                    "An unexpected server error occurred."
                ),
            },
        )

    return HTMLResponse(
        status_code=500,

        content=(
            "<!doctype html>"
            "<html lang='en'>"
            "<head>"
            "<meta charset='utf-8'>"
            "<title>500 | FINMARKET</title>"
            "</head>"
            "<body>"
            "<h1>Something went wrong</h1>"
            "<p>Please try again later.</p>"
            "<a href='/'>Return to FINMARKET</a>"
            "</body>"
            "</html>"
        ),
    )


# ============================================================
# 37. UVICORN CONFIGURATION FROM SAMLAPA
# ============================================================

try:

    UVICORN_CONFIG = uvicorn_kwargs_from_settings(
        finmkt_settings
    )

except Exception:

    logger.exception(
        "Unable to convert SAMLAPA Uvicorn configuration."
    )

    UVICORN_CONFIG = {
        "host": SERVER_HOST,
        "port": SERVER_PORT,
        "reload": APP_ENV == "dev",
        "workers": 1,
        "log_level": "info",
    }


# Preserve environment overrides.

UVICORN_CONFIG["host"] = SERVER_HOST
UVICORN_CONFIG["port"] = SERVER_PORT

if UVICORN_CONFIG.get("reload"):

    UVICORN_CONFIG["workers"] = 1


# ============================================================
# 38. PUBLIC EXPORTS
# ============================================================

__all__ = [
    "app",
    "APP_CONFIG",
    "SERVER_CONFIG",
    "finmkt_settings",
    "UVICORN_CONFIG",
    "check_database_connection",
    "register_models",
]
