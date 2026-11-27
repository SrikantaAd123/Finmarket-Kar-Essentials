
"""Access-token validation helpers for ZITADEL authentication."""

from __future__ import annotations

from typing import Any

from backend.auth.zitadel import (
    ZitadelConfigurationError,
    ZitadelTokenError,
    get_user_subject,
    validate_access_token as zitadel_validate_access_token,
)


def validate_token_claims(
    claims: dict[str, Any],
) -> dict[str, Any]:
    """Validate the structure and essential identity claims."""

    if not isinstance(claims, dict):
        raise ZitadelTokenError(
            "Invalid token claims."
        )

    try:
        subject = get_user_subject(claims)
    except ZitadelTokenError:
        raise
    except Exception as error:
        raise ZitadelTokenError(
            "Invalid subject in token claims."
        ) from error

    if not isinstance(subject, str) or not subject.strip():
        raise ZitadelTokenError(
            "Token subject is missing."
        )

    return claims


def validate_token(
    access_token: str,
) -> dict[str, Any]:
    """Validate an access token through ZITADEL introspection."""

    if not isinstance(access_token, str) or not access_token.strip():
        raise ZitadelTokenError(
            "Access token is required."
        )

    claims = zitadel_validate_access_token(
        access_token.strip()
    )

    return validate_token_claims(claims)


def get_validated_subject(
    claims: dict[str, Any],
) -> str:
    """Return the subject from validated token claims."""

    validated_claims = validate_token_claims(claims)

    subject = get_user_subject(validated_claims)

    if not isinstance(subject, str) or not subject.strip():
        raise ZitadelTokenError(
            "Invalid user subject."
        )

    return subject


__all__ = [
    "ZitadelConfigurationError",
    "ZitadelTokenError",
    "validate_token_claims",
    "validate_token",
    "get_validated_subject",
]
