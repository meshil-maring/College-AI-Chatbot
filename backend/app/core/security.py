import jwt
from jwt import PyJWKClient, ExpiredSignatureError, InvalidTokenError
from fastapi import Header, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.errors import AppError

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
    return _jwks_client


def verify_jwt(token: str) -> dict:
    """Verify a Supabase-issued JWT and return its claims."""
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"require": ["sub", "exp", "aud"]},
            audience="authenticated",
        )
        return claims
    except ExpiredSignatureError:
        raise AppError("Token has expired", status_code=401, code="TOKEN_EXPIRED")
    except InvalidTokenError as exc:
        raise AppError(f"Invalid token: {exc}", status_code=401, code="INVALID_TOKEN")


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict:
    """FastAPI dependency — returns the authenticated application user."""
    if not authorization:
        raise AppError("Authentication required", status_code=401, code="AUTH_REQUIRED")

    if not authorization.startswith("Bearer "):
        raise AppError(
            "Invalid authentication scheme",
            status_code=401,
            code="INVALID_SCHEME",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AppError("Token missing", status_code=401, code="TOKEN_MISSING")

    claims = verify_jwt(token)
    auth_user_id: str = claims["sub"]

    # Imported here to avoid circular imports
    from app.db.supabase import get_user_by_auth_id

    user = await get_user_by_auth_id(auth_user_id)
    if user is None:
        raise AppError(
            "No application user found for this account",
            status_code=404,
            code="USER_NOT_FOUND",
        )

    return {
        "user_id": user["id"],
        "auth_user_id": auth_user_id,
        "email": claims.get("email"),
    }
