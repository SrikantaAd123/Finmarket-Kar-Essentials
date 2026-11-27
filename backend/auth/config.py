
"""ZITADEL configuration for Finmarket Kart Essentials."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


class AuthConfigurationError(RuntimeError):
    """Raised when authentication configuration is invalid."""


def _get_required_env(name: str) -> str:
    """Read a required environment variable."""

    value = os.getenv(name, "").strip()

    if not value:
        raise AuthConfigurationError(
            f"Missing required environment variable: {name}"
        )

    return value


def _get_bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""

    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    raise AuthConfigurationError(
        f"{name} must be a valid boolean value."
    )


def _get_int_env(name: str, default: int) -> int:
    """Read an integer environment variable."""

    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return int(value.strip())
    except ValueError as error:
        raise AuthConfigurationError(
            f"{name} must be a valid integer."
        ) from error


# =========================================================
# CONFIGURATION MODELS
# =========================================================

@dataclass(frozen=True)
class ZitadelSettings:
    """General ZITADEL issuer configuration."""

    issuer: str


@dataclass(frozen=True)
class SwaggerOAuthSettings:
    """Confidential OAuth settings for Swagger authentication."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str]

    encryption_key: str

    state_cookie_name: str
    session_cookie_name: str

    secure_cookie: bool
    session_ttl_seconds: int


# =========================================================
# URL VALIDATION
# =========================================================

def _validate_issuer(issuer: str) -> str:
    """Validate the ZITADEL issuer URL."""

    parsed = urlparse(issuer)

    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise AuthConfigurationError(
            "ZITADEL_ISSUER must be a valid HTTPS URL."
        )

    return issuer.rstrip("/")


def _validate_redirect_uri(redirect_uri: str) -> str:
    """Validate the OAuth callback URL."""

    parsed = urlparse(redirect_uri)

    is_localhost = parsed.hostname in {
        "localhost",
        "127.0.0.1",
    }

    if (
        not parsed.scheme
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or (
            parsed.scheme != "https"
            and not (
                parsed.scheme == "http"
                and is_localhost
            )
        )
    ):
        raise AuthConfigurationError(
            "ZITADEL_SWAGGER_REDIRECT_URI must use HTTPS "
            "or HTTP on localhost during development."
        )

    return redirect_uri


# =========================================================
# GENERAL ZITADEL SETTINGS
# =========================================================

def get_zitadel_settings() -> ZitadelSettings:
    """Return validated general ZITADEL settings."""

    issuer = _validate_issuer(
        _get_required_env("ZITADEL_ISSUER")
    )

    return ZitadelSettings(
        issuer=issuer,
    )


# =========================================================
# SWAGGER OAUTH SETTINGS
# =========================================================

def get_swagger_oauth_settings() -> SwaggerOAuthSettings:
    """Return validated confidential OAuth settings."""

    issuer_settings = get_zitadel_settings()

    client_id = _get_required_env(
        "ZITADEL_SWAGGER_CLIENT_ID"
    )

    client_secret = _get_required_env(
        "ZITADEL_SWAGGER_CLIENT_SECRET"
    )

    redirect_uri = _validate_redirect_uri(
        _get_required_env(
            "ZITADEL_SWAGGER_REDIRECT_URI"
        )
    )

    encryption_key = _get_required_env(
        "ZITADEL_SESSION_ENCRYPTION_KEY"
    )

    # Validate that the encryption key is a valid Fernet key.
    try:
        Fernet(encryption_key.encode("utf-8"))
    except (ValueError, TypeError) as error:
        raise AuthConfigurationError(
            "ZITADEL_SESSION_ENCRYPTION_KEY must be "
            "a valid Fernet key."
        ) from error

    scopes = os.getenv(
        "ZITADEL_SWAGGER_SCOPES",
        "openid profile email",
    ).split()

    if "openid" not in scopes:
        scopes.insert(0, "openid")

    state_cookie_name = os.getenv(
        "ZITADEL_STATE_COOKIE_NAME",
        "zitadel_oauth_state",
    ).strip()

    session_cookie_name = os.getenv(
        "ZITADEL_SESSION_COOKIE_NAME",
        "zitadel_session",
    ).strip()

    if not state_cookie_name:
        raise AuthConfigurationError(
            "ZITADEL_STATE_COOKIE_NAME cannot be empty."
        )

    if not session_cookie_name:
        raise AuthConfigurationError(
            "ZITADEL_SESSION_COOKIE_NAME cannot be empty."
        )

    session_ttl_seconds = _get_int_env(
        "ZITADEL_SESSION_TTL_SECONDS",
        3600,
    )

    if session_ttl_seconds <= 0:
        raise AuthConfigurationError(
            "ZITADEL_SESSION_TTL_SECONDS must be greater than zero."
        )

    secure_cookie = _get_bool_env(
        "ZITADEL_SECURE_COOKIE",
        default=True,
    )

    if not secure_cookie:
        parsed_redirect = urlparse(redirect_uri)

        if parsed_redirect.scheme != "http" or parsed_redirect.hostname not in {
            "localhost",
            "127.0.0.1",
        }:
            raise AuthConfigurationError(
                "Disabling secure cookies is only permitted "
                "for localhost development."
            )

    return SwaggerOAuthSettings(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=scopes,
        encryption_key=encryption_key,
        state_cookie_name=state_cookie_name,
        session_cookie_name=session_cookie_name,
        secure_cookie=secure_cookie,
        session_ttl_seconds=session_ttl_seconds,
    )


__all__ = [
    "AuthConfigurationError",
    "ZitadelSettings",
    "SwaggerOAuthSettings",
    "get_zitadel_settings",
    "get_swagger_oauth_settings",
]
