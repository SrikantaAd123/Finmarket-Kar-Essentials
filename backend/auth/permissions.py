
"""Role-based and scope-based authorization helpers."""

from __future__ import annotations

import os
from typing import Any, Iterable

from fastapi import HTTPException, status


DEFAULT_ROLES_CLAIM = "urn:zitadel:iam:org:project:roles"
DEFAULT_ADMIN_ROLE = "admin"


def get_claims(
    user_or_claims: dict[str, Any],
) -> dict[str, Any]:
    """Accept either raw token claims or the current-user dictionary."""

    if not isinstance(user_or_claims, dict):
        return {}

    nested_claims = user_or_claims.get("claims")

    if isinstance(nested_claims, dict):
        return nested_claims

    return user_or_claims


def get_user_roles(
    user_or_claims: dict[str, Any],
) -> set[str]:
    """Extract role names from the configured ZITADEL roles claim."""

    claims = get_claims(user_or_claims)

    roles_claim = os.getenv(
        "ZITADEL_ROLES_CLAIM",
        DEFAULT_ROLES_CLAIM,
    ).strip()

    role_data = claims.get(roles_claim)

    if not isinstance(role_data, dict):
        return set()

    return {
        role.strip()
        for role in role_data
        if isinstance(role, str) and role.strip()
    }


def has_role(
    user_or_claims: dict[str, Any],
    role: str,
) -> bool:
    """Check whether the user has a particular role."""

    if not isinstance(role, str) or not role.strip():
        return False

    return role.strip() in get_user_roles(user_or_claims)


def require_role(
    user_or_claims: dict[str, Any],
    role: str,
) -> dict[str, Any]:
    """Require a specific role or raise HTTP 403."""

    if not has_role(user_or_claims, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The '{role}' role is required.",
        )

    return user_or_claims


def require_any_role(
    user_or_claims: dict[str, Any],
    roles: Iterable[str],
) -> dict[str, Any]:
    """Require at least one role from the supplied roles."""

    required_roles = {
        role.strip()
        for role in roles
        if isinstance(role, str) and role.strip()
    }

    if not required_roles:
        raise ValueError(
            "At least one valid role must be provided."
        )

    user_roles = get_user_roles(user_or_claims)

    if not user_roles.intersection(required_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the required permissions.",
        )

    return user_or_claims


def require_all_roles(
    user_or_claims: dict[str, Any],
    roles: Iterable[str],
) -> dict[str, Any]:
    """Require every role from the supplied roles."""

    required_roles = {
        role.strip()
        for role in roles
        if isinstance(role, str) and role.strip()
    }

    if not required_roles:
        raise ValueError(
            "At least one valid role must be provided."
        )

    user_roles = get_user_roles(user_or_claims)

    if not required_roles.issubset(user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have all the required permissions.",
        )

    return user_or_claims


def has_scope(
    user_or_claims: dict[str, Any],
    scope: str,
) -> bool:
    """Check whether the access token contains a particular scope."""

    if not isinstance(scope, str) or not scope.strip():
        return False

    claims = get_claims(user_or_claims)
    token_scopes = claims.get("scope", "")

    if isinstance(token_scopes, str):
        available_scopes = set(token_scopes.split())

    elif isinstance(token_scopes, list):
        available_scopes = {
            item
            for item in token_scopes
            if isinstance(item, str)
        }

    else:
        return False

    return scope.strip() in available_scopes


def require_scope(
    user_or_claims: dict[str, Any],
    scope: str,
) -> dict[str, Any]:
    """Require a particular OAuth scope or raise HTTP 403."""

    if not has_scope(user_or_claims, scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The '{scope}' scope is required.",
        )

    return user_or_claims


def require_admin(
    user_or_claims: dict[str, Any],
) -> dict[str, Any]:
    """Require the configured ZITADEL administrator role."""

    admin_role = os.getenv(
        "ZITADEL_ADMIN_ROLE",
        DEFAULT_ADMIN_ROLE,
    ).strip()

    return require_role(
        user_or_claims,
        admin_role,
    )


__all__ = [
    "get_claims",
    "get_user_roles",
    "has_role",
    "require_role",
    "require_any_role",
    "require_all_roles",
    "has_scope",
    "require_scope",
    "require_admin",
]
