"""Security tokens responsibilities."""

import logging

import jwt
from jwt import PyJWKClient, ExpiredSignatureError, InvalidTokenError, PyJWKError
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.config import settings
from app.core.errors import AppError


_jwks_client: PyJWKClient | None = None


logger = logging.getLogger(__name__)


_JWT_LEEWAY_SECONDS: int = 10


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            settings.supabase_jwks_url,
            cache_keys=True,
            timeout=settings.jwt_jwks_timeout_seconds,
        )
    return _jwks_client


def verify_jwt(token: str) -> dict:
    """Verify a Supabase-issued JWT and return its claims."""
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            options={"require": ["sub", "exp", "aud", "iss", "iat"]},
            audience="authenticated",
            issuer=settings.effective_supabase_jwt_issuer,
            leeway=_JWT_LEEWAY_SECONDS,
        )
        return claims
    except ExpiredSignatureError:
        raise AppError("Token has expired", status_code=401, code="TOKEN_EXPIRED")
    except PyJWKClientConnectionError as exc:
        logger.warning("event=jwks_unavailable")
        raise AppError(
            "Authentication verification is temporarily unavailable",
            status_code=503,
            code="AUTH_VERIFICATION_UNAVAILABLE",
        ) from exc
    except (InvalidTokenError, PyJWKError, PyJWKClientError):
        # Phase 6.15.7 — never echo library internals (exception text can name
        # algorithms, claims, key material sources). Fixed user-safe message.
        raise AppError("Invalid token", status_code=401, code="INVALID_TOKEN")
