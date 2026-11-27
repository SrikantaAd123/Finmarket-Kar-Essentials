
"""Central application configuration for FINMARKET Kart Essentials."""

from __future__ import annotations

import os

from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# 1. PROJECT DIRECTORY
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STREAMLIT_DIR = PROJECT_ROOT / "streamlit_app"

BACKEND_DIR = PROJECT_ROOT / "backend"

ASSETS_DIR = PROJECT_ROOT / "assets"

ASSETS_IMAGES_DIR = ASSETS_DIR / "images"


# ============================================================
# 2. ENVIRONMENT CONFIGURATION
# ============================================================

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


def get_env(
    name: str,
    default: str = "",
) -> str:
    """Read and normalize an environment variable."""

    return os.getenv(name, default).strip()


def get_bool_env(
    name: str,
    default: bool = False,
) -> bool:
    """Read a boolean environment variable."""

    value = get_env(
        name,
        str(default),
    ).lower()

    return value in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_int_env(
    name: str,
    default: int,
) -> int:
    """Read an integer environment variable."""

    value = get_env(
        name,
        str(default),
    )

    try:
        return int(value)

    except ValueError:
        return default


def get_float_env(
    name: str,
    default: float,
) -> float:
    """Read a floating-point environment variable."""

    value = get_env(
        name,
        str(default),
    )

    try:
        return float(value)

    except ValueError:
        return default


# ============================================================
# 3. APPLICATION INFORMATION
# ============================================================

APP_NAME = get_env(
    "APP_NAME",
    "FINMARKET Kart Essentials",
)

APP_VERSION = get_env(
    "APP_VERSION",
    "1.0.0",
)

APP_ENV = get_env(
    "FINMKT_ENV",
    get_env("APP_ENV", "dev"),
).lower()

DEBUG = get_bool_env(
    "DEBUG",
    APP_ENV in {"dev", "development", "local"},
)


# ============================================================
# 4. FASTAPI CONFIGURATION
# ============================================================

API_BASE_URL = get_env(
    "FINMARKET_API_BASE_URL",
    get_env(
        "API_BASE_URL",
        "http://127.0.0.1:8000",
    ),
).rstrip("/")

API_PREFIX = get_env(
    "API_PREFIX",
    "/api/v1",
).rstrip("/")

if not API_PREFIX.startswith("/"):
    API_PREFIX = f"/{API_PREFIX}"

REQUEST_TIMEOUT = get_float_env(
    "STREAMLIT_API_TIMEOUT",
    30.0,
)

if REQUEST_TIMEOUT <= 0:
    REQUEST_TIMEOUT = 30.0


# ============================================================
# 5. API ENDPOINTS
# ============================================================

API_ENDPOINTS = {
    "health": "/api/v1/system/health",
    "ready": "/api/v1/system/ready",
    "info": "/api/v1/system/info",

    "categories": f"{API_PREFIX}/catalog/categories",
    "products": f"{API_PREFIX}/catalog/products",
    "featured_products": f"{API_PREFIX}/catalog/products/featured",
    "brands": f"{API_PREFIX}/catalog/brands",
}


def api_url(endpoint: str) -> str:
    """Build a complete backend API URL."""

    return (
        f"{API_BASE_URL}/"
        f"{endpoint.lstrip('/')}"
    )


# ============================================================
# 6. ASSET DIRECTORIES
# ============================================================

IMAGES_DIR = ASSETS_IMAGES_DIR

BANNERS_DIR = IMAGES_DIR / "banners"

CATEGORIES_DIR = IMAGES_DIR / "categories"

PRODUCTS_DIR = IMAGES_DIR / "products"

LOGO_DIR = IMAGES_DIR / "logo"

ICONS_DIR = IMAGES_DIR / "icons"


# ============================================================
# 7. IMAGE CONFIGURATION
# ============================================================

DEFAULT_PRODUCT_IMAGE = get_env(
    "DEFAULT_PRODUCT_IMAGE",
    "https://placehold.co/600x400?text=FINMARKET",
)

DEFAULT_CATEGORY_IMAGE = get_env(
    "DEFAULT_CATEGORY_IMAGE",
    "https://placehold.co/500x350?text=Category",
)

DEFAULT_BANNER_IMAGE = get_env(
    "DEFAULT_BANNER_IMAGE",
    "https://placehold.co/1600x500?text=FINMARKET",
)

DEFAULT_LOGO_FILENAME = get_env(
    "DEFAULT_LOGO_FILENAME",
    "finmarket-logo.png",
)


# ============================================================
# 8. STOREFRONT CONFIGURATION
# ============================================================

CURRENCY_SYMBOL = get_env(
    "CURRENCY_SYMBOL",
    "₹",
)

CURRENCY_CODE = get_env(
    "CURRENCY_CODE",
    "INR",
)

PRODUCTS_PER_PAGE = get_int_env(
    "PRODUCTS_PER_PAGE",
    12,
)

FEATURED_PRODUCTS_LIMIT = get_int_env(
    "FEATURED_PRODUCTS_LIMIT",
    8,
)

MAX_CART_QUANTITY = get_int_env(
    "MAX_CART_QUANTITY",
    99,
)

if PRODUCTS_PER_PAGE < 1:
    PRODUCTS_PER_PAGE = 12

if FEATURED_PRODUCTS_LIMIT < 1:
    FEATURED_PRODUCTS_LIMIT = 8

if MAX_CART_QUANTITY < 1:
    MAX_CART_QUANTITY = 99


# ============================================================
# 9. STREAMLIT SERVER CONFIGURATION
# ============================================================

STREAMLIT_HOST = get_env(
    "STREAMLIT_HOST",
    "127.0.0.1",
)

STREAMLIT_PORT = get_int_env(
    "STREAMLIT_PORT",
    8501,
)

STREAMLIT_APP_URL = get_env(
    "STREAMLIT_APP_URL",
    f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}",
).rstrip("/")


# ============================================================
# 10. ZITADEL OAUTH CONFIGURATION
# ============================================================

ZITADEL_ISSUER = get_env(
    "ZITADEL_ISSUER",
).rstrip("/")

ZITADEL_CLIENT_ID = (
    get_env("ZITADEL_PUBLIC_CLIENT_ID")
    or get_env("ZITADEL_CLIENT_ID")
)

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

ZITADEL_USERINFO_URL = (
    f"{ZITADEL_ISSUER}/oidc/v1/userinfo"
    if ZITADEL_ISSUER
    else ""
)

ZITADEL_LOGOUT_URL = (
    f"{ZITADEL_ISSUER}/oidc/v1/end_session"
    if ZITADEL_ISSUER
    else ""
)

ZITADEL_REDIRECT_URI = get_env(
    "ZITADEL_FRONTEND_REDIRECT_URI",
    f"{API_BASE_URL}/auth/callback",
)

ZITADEL_SCOPES = get_env(
    "ZITADEL_FRONTEND_SCOPES",
    "openid profile email",
).split()

ZITADEL_AUDIENCE_SCOPE = get_env(
    "ZITADEL_AUDIENCE_SCOPE",
    get_env("ZITADEL_API_AUDIENCE_SCOPE"),
)

if ZITADEL_AUDIENCE_SCOPE:
    ZITADEL_SCOPES.append(
        ZITADEL_AUDIENCE_SCOPE
    )

ZITADEL_SCOPES = list(
    dict.fromkeys(ZITADEL_SCOPES)
)


# ============================================================
# 11. SESSION CONFIGURATION
# ============================================================

SESSION_COOKIE_NAME = get_env(
    "SESSION_COOKIE_NAME",
    "finmarket_session",
)

SESSION_MAX_AGE = get_int_env(
    "SESSION_MAX_AGE",
    604800,
)

COOKIE_SECRET = (
    get_env("SESSION_SECRET")
    or get_env("COOKIE_SECRET")
)


# ============================================================
# 12. UPLOAD CONFIGURATION
# ============================================================

UPLOADS_DIR = Path(
    get_env(
        "UPLOADS_DIR",
        str(PROJECT_ROOT / "uploads"),
    )
).expanduser()

if not UPLOADS_DIR.is_absolute():
    UPLOADS_DIR = PROJECT_ROOT / UPLOADS_DIR

UPLOADS_DIR = UPLOADS_DIR.resolve()


# ============================================================
# 13. OPTIONAL FEATURE FLAGS
# ============================================================

ENABLE_FEATURED_PRODUCTS = get_bool_env(
    "ENABLE_FEATURED_PRODUCTS",
    True,
)

ENABLE_PRODUCT_SEARCH = get_bool_env(
    "ENABLE_PRODUCT_SEARCH",
    True,
)

ENABLE_CATEGORY_FILTER = get_bool_env(
    "ENABLE_CATEGORY_FILTER",
    True,
)

ENABLE_BRAND_FILTER = get_bool_env(
    "ENABLE_BRAND_FILTER",
    True,
)

ENABLE_CART = get_bool_env(
    "ENABLE_CART",
    True,
)


# ============================================================
# 14. IMAGE PATH HELPER
# ============================================================

def image_path(
    directory: Path,
    filename: str | Path | None,
) -> Path | None:
    """
    Resolve a local image safely.

    Supports:
        image.png
        categories/image.png
        nested/category/image.png

    Prevents paths outside the requested asset directory.
    """

    if not filename:
        return None

    try:

        image_root = directory.resolve()

        supplied_path = Path(
            str(filename)
        )

        if supplied_path.is_absolute():
            return None

        resolved_path = (
            image_root / supplied_path
        ).resolve()

        if not resolved_path.is_relative_to(
            image_root
        ):
            return None

        if resolved_path.is_file():
            return resolved_path

    except (
        OSError,
        ValueError,
        TypeError,
    ):
        return None

    return None


# ============================================================
# 15. PROJECT DIRECTORY VALIDATION
# ============================================================

def validate_project_directories() -> dict[str, bool]:
    """Return the availability of important project directories."""

    return {
        "project_root": PROJECT_ROOT.is_dir(),
        "streamlit": STREAMLIT_DIR.is_dir(),
        "backend": BACKEND_DIR.is_dir(),
        "assets": ASSETS_DIR.is_dir(),
        "images": IMAGES_DIR.is_dir(),
        "categories": CATEGORIES_DIR.is_dir(),
        "products": PRODUCTS_DIR.is_dir(),
        "logo": LOGO_DIR.is_dir(),
        "uploads": UPLOADS_DIR.is_dir(),
    }
