
"""Unit tests for ZITADEL JWT authentication."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from backend.auth import zitadel


# =========================================================
# FIXTURES
# =========================================================

@pytest.fixture(autouse=True)
def clear_jwks_cache():
    """Prevent cached JWKS clients from leaking between tests."""
    zitadel.clear_jwks_cache()
    yield
    zitadel.clear_jwks_cache()


@pytest.fixture
def zitadel_env(monkeypatch):
    """Provide valid ZITADEL environment configuration."""
    monkeypatch.setenv(
        "ZITADEL_ISSUER",
        "https://example.zitadel.cloud",
    )
    monkeypatch.setenv("ZITADEL_PROJECT_ID", "test-project")
    monkeypatch.setenv(
        "ZITADEL_SCOPES",
        "openid profile email",
    )
    monkeypatch.delenv(
        "ZITADEL_API_AUDIENCE_SCOPE",
        raising=False,
    )


@pytest.fixture
def valid_claims():
    """Return representative valid JWT claims."""
    return {
        "sub": "user-123",
        "iss": "https://example.zitadel.cloud",
        "aud": "test-project",
        "exp": 2_000_000_000,
        "iat": 1_900_000_000,
        "email": "user@example.com",
        "name": "Test User",
    }


# =========================================================
# ENVIRONMENT CONFIGURATION TESTS
# =========================================================

def test_get_env_returns_value(monkeypatch):
    monkeypatch.setenv("TEST_SETTING", "  example-value  ")

    assert zitadel.get_env("TEST_SETTING") == "example-value"


def test_get_env_missing_variable(monkeypatch):
    monkeypatch.delenv("TEST_SETTING", raising=False)

    with pytest.raises(zitadel.ZitadelConfigurationError):
        zitadel.get_env("TEST_SETTING")


def test_get_zitadel_issuer_valid(zitadel_env):
    assert (
        zitadel.get_zitadel_issuer()
        == "https://example.zitadel.cloud"
    )


@pytest.mark.parametrize(
    "issuer",
    [
        "",
        "http://example.zitadel.cloud",
        "example.zitadel.cloud",
        "https://",
        "https://example.zitadel.cloud?query=value",
        "https://example.zitadel.cloud#fragment",
    ],
)
def test_get_zitadel_issuer_invalid(monkeypatch, issuer):
    monkeypatch.setenv("ZITADEL_ISSUER", issuer)

    with pytest.raises(zitadel.ZitadelConfigurationError):
        zitadel.get_zitadel_issuer()


def test_get_zitadel_issuer_removes_trailing_slash(monkeypatch):
    monkeypatch.setenv(
        "ZITADEL_ISSUER",
        "https://example.zitadel.cloud/",
    )

    assert (
        zitadel.get_zitadel_issuer()
        == "https://example.zitadel.cloud"
    )


def test_get_zitadel_project_id(zitadel_env):
    assert zitadel.get_zitadel_project_id() == "test-project"


def test_get_zitadel_project_id_missing(monkeypatch):
    monkeypatch.delenv("ZITADEL_PROJECT_ID", raising=False)

    with pytest.raises(zitadel.ZitadelConfigurationError):
        zitadel.get_zitadel_project_id()


# =========================================================
# SCOPE CONFIGURATION TESTS
# =========================================================

def test_get_zitadel_scopes_default(monkeypatch):
    monkeypatch.delenv("ZITADEL_SCOPES", raising=False)
    monkeypatch.delenv(
        "ZITADEL_API_AUDIENCE_SCOPE",
        raising=False,
    )

    assert zitadel.get_zitadel_scopes() == [
        "openid",
        "profile",
        "email",
    ]


def test_get_zitadel_scopes_custom(monkeypatch):
    monkeypatch.setenv(
        "ZITADEL_SCOPES",
        "openid profile email",
    )
    monkeypatch.setenv(
        "ZITADEL_API_AUDIENCE_SCOPE",
        "api",
    )

    assert zitadel.get_zitadel_scopes() == [
        "openid",
        "profile",
        "email",
        "api",
    ]


def test_get_zitadel_scopes_adds_openid(monkeypatch):
    monkeypatch.setenv(
        "ZITADEL_SCOPES",
        "profile email",
    )
    monkeypatch.delenv(
        "ZITADEL_API_AUDIENCE_SCOPE",
        raising=False,
    )

    assert zitadel.get_zitadel_scopes() == [
        "openid",
        "profile",
        "email",
    ]


def test_get_zitadel_scopes_removes_duplicates(monkeypatch):
    monkeypatch.setenv(
        "ZITADEL_SCOPES",
        "openid profile email profile",
    )
    monkeypatch.setenv(
        "ZITADEL_API_AUDIENCE_SCOPE",
        "email",
    )

    assert zitadel.get_zitadel_scopes() == [
        "openid",
        "profile",
        "email",
    ]


# =========================================================
# JWKS CLIENT TESTS
# =========================================================

def test_get_jwks_client_creates_correct_client(
    zitadel_env,
    monkeypatch,
):
    mock_client = MagicMock()
    client_constructor = MagicMock(return_value=mock_client)

    monkeypatch.setattr(
        zitadel,
        "PyJWKClient",
        client_constructor,
    )

    client = zitadel.get_jwks_client()

    assert client is mock_client

    client_constructor.assert_called_once_with(
        "https://example.zitadel.cloud/oauth/v2/keys",
        cache_keys=True,
        timeout=10,
    )


def test_get_jwks_client_is_cached(zitadel_env, monkeypatch):
    mock_client = MagicMock()
    client_constructor = MagicMock(return_value=mock_client)

    monkeypatch.setattr(
        zitadel,
        "PyJWKClient",
        client_constructor,
    )

    first = zitadel.get_jwks_client()
    second = zitadel.get_jwks_client()

    assert first is second
    client_constructor.assert_called_once()


def test_clear_jwks_cache(zitadel_env, monkeypatch):
    client_constructor = MagicMock(return_value=MagicMock())

    monkeypatch.setattr(
        zitadel,
        "PyJWKClient",
        client_constructor,
    )

    zitadel.get_jwks_client()
    zitadel.clear_jwks_cache()
    zitadel.get_jwks_client()

    assert client_constructor.call_count == 2


def test_get_jwks_client_requires_issuer(monkeypatch):
    monkeypatch.delenv("ZITADEL_ISSUER", raising=False)

    with pytest.raises(zitadel.ZitadelConfigurationError):
        zitadel.get_jwks_client()


# =========================================================
# TOKEN VALIDATION MOCK HELPER
# =========================================================

def configure_token_validation(
    monkeypatch,
    claims=None,
    decode_error=None,
    jwks_error=None,
):
    """Mock the JWKS client and JWT decoder."""

    signing_key = SimpleNamespace(key="mock-public-key")

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = signing_key

    monkeypatch.setattr(
        zitadel,
        "get_jwks_client",
        lambda: mock_client,
    )

    if jwks_error is not None:
        mock_client.get_signing_key_from_jwt.side_effect = jwks_error

    mock_decode = MagicMock(
        return_value=claims if claims is not None else {}
    )

    if decode_error is not None:
        mock_decode.side_effect = decode_error

    monkeypatch.setattr(
        zitadel.jwt,
        "decode",
        mock_decode,
    )

    return mock_client, mock_decode


# =========================================================
# ACCESS TOKEN VALIDATION TESTS
# =========================================================

def test_validate_access_token_success(
    zitadel_env,
    valid_claims,
    monkeypatch,
):
    mock_client, mock_decode = configure_token_validation(
        monkeypatch,
        claims=valid_claims,
    )

    result = zitadel.validate_access_token("valid.jwt.token")

    assert result == valid_claims

    mock_client.get_signing_key_from_jwt.assert_called_once_with(
        "valid.jwt.token"
    )

    mock_decode.assert_called_once()

    kwargs = mock_decode.call_args.kwargs

    assert kwargs["algorithms"] == ["RS256"]
    assert kwargs["issuer"] == "https://example.zitadel.cloud"
    assert kwargs["audience"] == "test-project"
    assert kwargs["leeway"] == 30


@pytest.mark.parametrize(
    "token",
    [
        "",
        " ",
        None,
        123,
        [],
    ],
)
def test_validate_access_token_empty_or_invalid_input(token):
    with pytest.raises(zitadel.ZitadelTokenError):
        zitadel.validate_access_token(token)


def test_validate_access_token_invalid_signature(
    zitadel_env,
    monkeypatch,
):
    configure_token_validation(
        monkeypatch,
        decode_error=InvalidTokenError("Invalid signature"),
    )

    with pytest.raises(
        zitadel.ZitadelTokenError,
        match="invalid or expired",
    ):
        zitadel.validate_access_token("invalid.jwt.token")


def test_validate_access_token_expired(
    zitadel_env,
    monkeypatch,
):
    configure_token_validation(
        monkeypatch,
        decode_error=jwt.ExpiredSignatureError("Token expired"),
    )

    with pytest.raises(zitadel.ZitadelTokenError):
        zitadel.validate_access_token("expired.jwt.token")


def test_validate_access_token_wrong_issuer(
    zitadel_env,
    monkeypatch,
):
    configure_token_validation(
        monkeypatch,
        decode_error=jwt.InvalidIssuerError("Wrong issuer"),
    )

    with pytest.raises(zitadel.ZitadelTokenError):
        zitadel.validate_access_token("wrong.issuer.token")


def test_validate_access_token_wrong_audience(
    zitadel_env,
    monkeypatch,
):
    configure_token_validation(
        monkeypatch,
        decode_error=jwt.InvalidAudienceError("Wrong audience"),
    )

    with pytest.raises(zitadel.ZitadelTokenError):
        zitadel.validate_access_token("wrong.audience.token")


def test_validate_access_token_missing_required_claim(
    zitadel_env,
    monkeypatch,
):
    configure_token_validation(
        monkeypatch,
        decode_error=jwt.MissingRequiredClaimError("exp"),
    )

    with pytest.raises(zitadel.ZitadelTokenError):
        zitadel.validate_access_token("missing.claim.token")


def test_validate_access_token_jwks_failure(
    zitadel_env,
    monkeypatch,
):
    configure_token_validation(
        monkeypatch,
        jwks_error=PyJWKClientError("JWKS unavailable"),
    )

    with pytest.raises(
        zitadel.ZitadelTokenError,
        match="Unable to retrieve",
    ):
        zitadel.validate_access_token("valid.jwt.token")


def test_validate_access_token_configuration_error(monkeypatch):
    monkeypatch.delenv("ZITADEL_ISSUER", raising=False)

    with pytest.raises(zitadel.ZitadelConfigurationError):
        zitadel.validate_access_token("valid.jwt.token")


def test_validate_access_token_invalid_subject(
    zitadel_env,
    monkeypatch,
):
    claims = {
        "sub": "",
        "iss": "https://example.zitadel.cloud",
        "aud": "test-project",
    }

    configure_token_validation(
        monkeypatch,
        claims=claims,
    )

    with pytest.raises(
        zitadel.ZitadelTokenError,
        match="valid user subject",
    ):
        zitadel.validate_access_token("invalid.subject.token")


def test_validate_access_token_unexpected_error(
    zitadel_env,
    monkeypatch,
):
    configure_token_validation(
        monkeypatch,
        jwks_error=RuntimeError("Unexpected failure"),
    )

    with pytest.raises(
        zitadel.ZitadelTokenError,
        match="Unable to validate",
    ):
        zitadel.validate_access_token("valid.jwt.token")


# =========================================================
# USER SUBJECT TESTS
# =========================================================

def test_get_user_subject_success():
    assert zitadel.get_user_subject(
        {"sub": "user-123"}
    ) == "user-123"


def test_get_user_subject_strips_whitespace():
    assert zitadel.get_user_subject(
        {"sub": "  user-123  "}
    ) == "user-123"


@pytest.mark.parametrize(
    "claims",
    [
        None,
        [],
        {},
        {"sub": ""},
        {"sub": "   "},
        {"sub": None},
        {"sub": 123},
    ],
)
def test_get_user_subject_invalid(claims):
    with pytest.raises(zitadel.ZitadelTokenError):
        zitadel.get_user_subject(claims)


# =========================================================
# USER EMAIL TESTS
# =========================================================

def test_get_user_email_success():
    assert zitadel.get_user_email(
        {"email": "user@example.com"}
    ) == "user@example.com"


def test_get_user_email_strips_whitespace():
    assert zitadel.get_user_email(
        {"email": "  user@example.com  "}
    ) == "user@example.com"


@pytest.mark.parametrize(
    "claims",
    [
        {},
        {"email": ""},
        {"email": "   "},
        {"email": None},
        {"email": 123},
    ],
)
def test_get_user_email_missing_or_invalid(claims):
    assert zitadel.get_user_email(claims) is None


# =========================================================
# USER NAME TESTS
# =========================================================

def test_get_user_name_success():
    assert zitadel.get_user_name(
        {"name": "Test User"}
    ) == "Test User"


def test_get_user_name_strips_whitespace():
    assert zitadel.get_user_name(
        {"name": "  Test User  "}
    ) == "Test User"


@pytest.mark.parametrize(
    "claims",
    [
        {},
        {"name": ""},
        {"name": "   "},
        {"name": None},
        {"name": 123},
    ],
)
def test_get_user_name_missing_or_invalid(claims):
    assert zitadel.get_user_name(claims) is None


# =========================================================
# PUBLIC EXPORTS
# =========================================================

def test_public_exports():
    expected_exports = {
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
    }

    assert set(zitadel.__all__) == expected_exports
