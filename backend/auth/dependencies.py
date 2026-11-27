
"""FastAPI authentication and database dependencies."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, HTTPException, status
import httpx

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from backend.auth.zitadel import (
    ZitadelConfigurationError,
    ZitadelTokenError,
    get_user_subject,
    get_zitadel_issuer,
    validate_access_token,
)
from backend.database.connection import get_db
from backend.repositories.customer_repository import CustomerRepository


# =========================================================
# HTTP BEARER AUTHENTICATION
# =========================================================

bearer_scheme = HTTPBearer(auto_error=False)


# =========================================================
# VALIDATE ACCESS TOKEN
# =========================================================

def get_current_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict[str, Any]:
    """Validate the incoming ZITADEL Bearer token."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = validate_access_token(credentials.credentials)

        # ZITADEL access tokens do not always contain profile/email claims.
        # Resolve them from the official UserInfo endpoint, using the same
        # access token, and bind the response to the verified JWT subject.
        issuer = get_zitadel_issuer()
        try:
            response = httpx.get(
                f"{issuer}/oidc/v1/userinfo",
                headers={
                    "Authorization": f"Bearer {credentials.credentials}",
                    "Accept": "application/json",
                },
                timeout=12.0,
            )
            response.raise_for_status()
            userinfo = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Could not retrieve the signed-in profile from ZITADEL UserInfo. "
                    "Confirm the email scope is requested and the access token is valid."
                ),
            ) from error

        if not isinstance(userinfo, dict) or userinfo.get("sub") != claims.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ZITADEL UserInfo identity does not match the verified access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Keep the cryptographically verified JWT claims authoritative for
        # issuer, audience, subject and ZITADEL project-role claims.
        claims = {**userinfo, **claims}
        claims["email"] = userinfo.get("email") or claims.get("email")
        claims["email_verified"] = userinfo.get("email_verified", claims.get("email_verified", False))
        claims["name"] = (
            userinfo.get("name")
            or " ".join(filter(None, [userinfo.get("given_name"), userinfo.get("family_name")]))
            or claims.get("name")
        )
        return claims

    except ZitadelConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication configuration error.",
        ) from error

    except ZitadelTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


# =========================================================
# CURRENT ZITADEL USER
# =========================================================

def get_current_zitadel_user(
    claims: dict[str, Any] = Depends(
        get_current_token_claims
    ),
) -> dict[str, Any]:
    """Return the authenticated ZITADEL user identity."""

    try:
        subject = get_user_subject(claims)

    except ZitadelTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity in access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return {
        "sub": subject,
        "email": claims.get("email"),
        "name": claims.get("name"),
        "username": claims.get("preferred_username"),
        "claims": claims,
    }


# =========================================================
# CURRENT CUSTOMER
# =========================================================

def get_current_customer(
    current_user: dict[str, Any] = Depends(
        get_current_zitadel_user
    ),
    db: Session = Depends(get_db),
) -> Any:
    """Find the local customer linked to the ZITADEL subject."""

    repository = CustomerRepository(db)

    customer = repository.get_customer_by_zitadel_sub(
        current_user["sub"]
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Customer profile not found. "
                "Please complete customer registration."
            ),
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your customer account is inactive.",
        )

    return customer


# =========================================================
# CURRENT ADMIN
# =========================================================

def get_current_admin(
    current_user: dict[str, Any] = Depends(
        get_current_zitadel_user
    ),
) -> dict[str, Any]:
    """Allow access only to users with the configured ZITADEL admin role."""

    admin_role = os.getenv(
        "ZITADEL_ADMIN_ROLE",
        "admin",
    ).strip()

    roles_claim = os.getenv(
        "ZITADEL_ROLES_CLAIM",
        "urn:zitadel:iam:org:project:roles",
    ).strip()

    claims = current_user.get("claims", {})
    roles = claims.get(roles_claim)

    if (
        not admin_role
        or not isinstance(roles, dict)
        or admin_role not in roles
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator permissions are required.",
        )

    return current_user


# =========================================================
# PUBLIC EXPORTS
# =========================================================

__all__ = [
    "bearer_scheme",
    "get_current_token_claims",
    "get_current_zitadel_user",
    "get_current_customer",
    "get_current_admin",
]
