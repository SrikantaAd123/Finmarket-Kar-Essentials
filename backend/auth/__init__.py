
"""Authentication package for Finmarket Kart Essentials."""

# =========================================================
# FASTAPI AUTHENTICATION DEPENDENCIES
# =========================================================

from backend.auth.dependencies import (
    bearer_scheme,
    get_current_admin,
    get_current_customer,
    get_current_token_claims,
    get_current_zitadel_user,
)

# =========================================================
# PERMISSIONS AND AUTHORIZATION
# =========================================================

from backend.auth.permissions import (
    get_claims,
    get_user_roles,
    has_role,
    require_role,
    require_any_role,
    require_all_roles,
    has_scope,
    require_scope,
    require_admin,
)

# =========================================================
# TOKEN VALIDATION
# =========================================================

from backend.auth.token_validation import (
    validate_token,
    validate_token_claims,
    get_validated_subject,
)

# =========================================================
# ZITADEL CONFIGURATION AND IDENTITY
# =========================================================

from backend.auth.zitadel import (
    ZitadelConfigurationError,
    ZitadelTokenError,
    get_env,
    get_zitadel_issuer,
    get_zitadel_project_id,
    get_zitadel_scopes,
    get_jwks_client,
    clear_jwks_cache,
    validate_access_token,
    get_user_subject,
    get_user_email,
    get_user_name,
)


__all__ = [
    # Authentication dependencies
    "bearer_scheme",
    "get_current_admin",
    "get_current_customer",
    "get_current_token_claims",
    "get_current_zitadel_user",

    # Permissions
    "get_claims",
    "get_user_roles",
    "has_role",
    "require_role",
    "require_any_role",
    "require_all_roles",
    "has_scope",
    "require_scope",
    "require_admin",

    # Token validation
    "validate_token",
    "validate_token_claims",
    "get_validated_subject",

    # ZITADEL configuration
    "ZitadelConfigurationError",
    "ZitadelTokenError",
    "get_env",
    "get_zitadel_issuer",
    "get_zitadel_project_id",
    "get_zitadel_scopes",
    "get_jwks_client",
    "clear_jwks_cache",
    "validate_access_token",

    # User identity
    "get_user_subject",
    "get_user_email",
    "get_user_name",
]
