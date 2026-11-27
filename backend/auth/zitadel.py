
"""ZITADEL JWT authentication for Finmarket Kart Essentials."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import jwt
from dotenv import load_dotenv
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    PyJWKClientError,
)


# =========================================================
# ENVIRONMENT CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


class ZitadelConfigurationError(RuntimeError):
    """Raised when ZITADEL configuration is missing or invalid."""


class ZitadelTokenError(ValueError):
    """Raised when a ZITADEL access token is invalid."""


def get_env(name: str) -> str:
    """Read a required environment variable."""

    value = os.getenv(name, "").strip()

    if not value:
        raise ZitadelConfigurationError(
            f"Missing environment variable: {name}"
        )

    return value


def get_zitadel_issuer() -> str:
    """Return and validate the ZITADEL issuer URL."""

    issuer = get_env("ZITADEL_ISSUER").rstrip("/")

    parsed = urlparse(issuer)

    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ZitadelConfigurationError(
            "ZITADEL_ISSUER must be a valid HTTPS issuer URL."
        )

    return issuer


def get_zitadel_project_id() -> str:
    """Return the expected API audience."""

    return get_env("ZITADEL_PROJECT_ID")


def get_zitadel_scopes() -> list[str]:
    """Return configured OIDC scopes."""

    configured_scopes = os.getenv(
        "ZITADEL_SCOPES",
        "openid profile email",
    ).split()

    audience_scope = os.getenv(
        "ZITADEL_API_AUDIENCE_SCOPE",
        "",
    ).strip()

    scopes = list(dict.fromkeys(configured_scopes))

    if audience_scope and audience_scope not in scopes:
        scopes.append(audience_scope)

    if "openid" not in scopes:
        scopes.insert(0, "openid")

    return scopes


# =========================================================
# ZITADEL JWKS CLIENT
# =========================================================

@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient:
    """Create and cache the ZITADEL public-key client."""

    issuer = get_zitadel_issuer()

    jwks_url = f"{issuer}/oauth/v2/keys"

    return PyJWKClient(
        jwks_url,
        cache_keys=True,
        timeout=10,
    )


def clear_jwks_cache() -> None:
    """Clear the cached JWKS client."""

    get_jwks_client.cache_clear()


# =========================================================
# ACCESS TOKEN VALIDATION
# =========================================================

def validate_access_token(
    token: str,
) -> dict[str, Any]:
    """
    Validate a ZITADEL JWT access token.

    Checks:
    - RS256 signature
    - ZITADEL issuer
    - Configured project audience
    - Expiration
    - Issued-at timestamp
    - Required subject claim
    """

    if not isinstance(token, str) or not token.strip():
        raise ZitadelTokenError(
            "Access token is empty."
        )

    issuer = get_zitadel_issuer()
    audience = get_zitadel_project_id()

    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(
            token
        )

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={
                "require": [
                    "exp",
                    "iat",
                    "iss",
                    "sub",
                    "aud",
                ],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
            leeway=30,
        )

        if not isinstance(claims, dict):
            raise ZitadelTokenError(
                "Invalid token claims."
            )

        get_user_subject(claims)

        return claims

    except ZitadelConfigurationError:
        raise

    except ZitadelTokenError:
        raise

    except InvalidTokenError as error:
        raise ZitadelTokenError(
            "The ZITADEL access token is invalid or expired."
        ) from error

    except PyJWKClientError as error:
        raise ZitadelTokenError(
            "Unable to retrieve the ZITADEL signing key."
        ) from error

    except Exception as error:
        raise ZitadelTokenError(
            "Unable to validate the ZITADEL access token."
        ) from error


# =========================================================
# USER IDENTITY
# =========================================================

def get_user_subject(
    claims: dict[str, Any],
) -> str:
    """Extract the authenticated user's ZITADEL subject ID."""

    if not isinstance(claims, dict):
        raise ZitadelTokenError(
            "Invalid token claims."
        )

    subject = claims.get("sub")

    if not isinstance(subject, str) or not subject.strip():
        raise ZitadelTokenError(
            "The token does not contain a valid user subject."
        )

    return subject.strip()


def get_user_email(
    claims: dict[str, Any],
) -> str | None:
    """Extract the user's email address from token claims."""

    email = claims.get("email")

    if not isinstance(email, str) or not email.strip():
        return None

    return email.strip()


def get_user_name(
    claims: dict[str, Any],
) -> str | None:
    """Extract the user's display name from token claims."""

    name = claims.get("name")

    if not isinstance(name, str) or not name.strip():
        return None

    return name.strip()


__all__ = [
    "ZitadelConfigurationError",
    "ZitadelTokenError",
    "get_env",
    "get_zitadel_issuer",
    "get_zitadel_project_id",
    "get_zitadel_scopes",
    "get_jwks_client",
    "clear_jwks_cache",
    "validate_access_token",
    "get_user_subject",
    "get_user_email",
    "get_user_name",
]
