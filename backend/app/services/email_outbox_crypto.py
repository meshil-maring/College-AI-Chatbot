"""At-rest protection for Phase 7.17 invitation delivery secrets.

The invitation URL needs the original high-entropy token, while the invitation
table intentionally retains only its SHA-256 digest.  The durable outbox stores
an authenticated Fernet ciphertext so a worker can reconstruct the URL after a
restart without persisting the raw bearer token.  The key is backend-only and
is required by startup validation in every deployed environment.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import DEV_TEST_ENVIRONMENTS, settings
from app.core.errors import AppError

# Deliberately public/non-secret local material. It is accepted only in the
# allowlisted local/test environments and must never protect deployed data.
_LOCAL_KEY_MATERIAL = b"college-ai-chatbot-phase-7.17-local-only"


def _local_key() -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(_LOCAL_KEY_MATERIAL).digest())


def _cipher() -> Fernet:
    configured = (settings.email_outbox_token_encryption_key or "").strip()
    environment = (settings.environment or "").strip().lower()
    key = configured.encode("ascii") if configured else None
    if key is None and environment in DEV_TEST_ENVIRONMENTS:
        key = _local_key()
    if key is None:
        raise AppError(
            "Email delivery is not configured.",
            status_code=500,
            code="EMAIL_OUTBOX_ENCRYPTION_NOT_CONFIGURED",
        )
    try:
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise AppError(
            "Email delivery is not configured.",
            status_code=500,
            code="EMAIL_OUTBOX_ENCRYPTION_INVALID",
        ) from exc


def protect_invitation_token(raw_token: str) -> str:
    """Return authenticated ciphertext; the plaintext is never persisted."""
    if not raw_token:
        raise ValueError("invitation token must not be empty")
    return _cipher().encrypt(raw_token.encode("utf-8")).decode("ascii")


def recover_invitation_token(protected_token: str) -> str:
    """Recover a token for immediate rendering or fail with a safe category."""
    try:
        value = _cipher().decrypt(protected_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, ValueError) as exc:
        raise AppError(
            "Email delivery payload could not be recovered.",
            status_code=500,
            code="EMAIL_OUTBOX_PAYLOAD_INVALID",
        ) from exc
    if not value:
        raise AppError(
            "Email delivery payload could not be recovered.",
            status_code=500,
            code="EMAIL_OUTBOX_PAYLOAD_INVALID",
        )
    return value
