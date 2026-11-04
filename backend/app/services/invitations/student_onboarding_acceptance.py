"""Public setup-link inspection and student account activation."""

import hashlib
from typing import Any
from uuid import UUID

from supabase_auth.errors import AuthApiError, AuthRetryableError

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.invitations import student_onboarding as repository
from app.schemas.invitations.student_onboarding import (
    StudentInvitationCompleteResponse,
    StudentInvitationPublicView,
)
from app.services.invitations.student_onboarding_common import (
    INVALID_LINK,
    database,
)


def _resolve(token: str) -> tuple[str, dict[str, Any]]:
    import logging as _l
    _log = _l.getLogger(__name__)
    if (
        not token or len(token) < 32 or len(token) > 256
        or not token.isascii()
        or not all(char.isalnum() or char in "_-" for char in token)
    ):
        raise INVALID_LINK
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    try:
        raw = repository.inspect(get_admin_client(), token_hash=token_hash)
        _log.warning("RAW row type=%s val=%s", type(raw).__name__, repr(raw)[:400])
        row = database(lambda: raw)
    except Exception as exc:
        _log.warning("EXC type=%s code=%s msg=%s", type(exc).__name__, getattr(exc, 'code', None), str(exc)[:300])
        raise
    if not row:
        raise INVALID_LINK
    return token_hash, row


def inspect(token: str) -> StudentInvitationPublicView:
    _, row = _resolve(token)
    return StudentInvitationPublicView.model_validate({
        key: row[key] for key in (
            "status", "student_name", "email", "institution_name", "batch_name",
            "batch_code", "section_name", "section_active", "expires_at",
        )
    })


def _create_or_update_auth_user(row: dict[str, Any], invitation_id: UUID, password: str) -> str:
    client = get_admin_client()
    existing = row.get("provisioned_auth_user_id")
    if existing:
        try:
            client.auth.admin.update_user_by_id(str(existing), {"password": password, "email_confirm": True})
        except AuthApiError as exc:
            raise AppError("Password setup is temporarily unavailable. Request a new setup link.", 503, "AUTH_ACCOUNT_UNAVAILABLE") from exc
        except AuthRetryableError as exc:
            raise AppError("Password setup is temporarily unavailable. Retry using this link.", 503, "AUTH_ACCOUNT_UNAVAILABLE") from exc
        return str(existing)
    try:
        response = client.auth.admin.create_user({
            "email": row["email"],
            "password": password,
            "email_confirm": True,
            "app_metadata": {"student_onboarding_invitation_id": str(invitation_id)},
        })
    except AuthApiError as exc:
        message = str(getattr(exc, "message", "") or "").lower()
        status = getattr(exc, "status", None)
        if status in (400, 409, 422) and any(word in message for word in ("already", "exists", "duplicate")):
            raise AppError("An account already exists for this email. Contact your administrator.", 409, "AUTH_ACCOUNT_EXISTS") from exc
        raise AppError("Password setup is temporarily unavailable. Retry using this link.", 503, "AUTH_ACCOUNT_UNAVAILABLE") from exc
    except AuthRetryableError as exc:
        raise AppError("Password setup is temporarily unavailable. Retry using this link.", 503, "AUTH_ACCOUNT_UNAVAILABLE") from exc
    if response.user is None or not response.user.id:
        raise AppError("Password setup could not be confirmed. Retry using this link.", 503, "AUTH_ACCOUNT_UNAVAILABLE")
    return str(response.user.id)


def complete(token: str, password: str) -> StudentInvitationCompleteResponse:
    token_hash, row = _resolve(token)
    if row["status"] == "accepted":
        return StudentInvitationCompleteResponse(
            message="Student account setup is already complete. Sign in to continue.",
            completed=True,
        )
    if not row.get("section_active"):
        raise AppError(
            "This section is no longer active. Ask your administrator to assign an active section.",
            409,
            "SECTION_INACTIVE",
        )
    invitation_id = UUID(str(row["invitation_id"]))
    client = get_admin_client()
    claimed = database(lambda: repository.claim_setup(
        client, invitation=invitation_id, token_hash=token_hash,
    ))
    if not claimed:
        raise INVALID_LINK
    try:
        auth_user_id = _create_or_update_auth_user(row, invitation_id, password)
    except AppError as exc:
        released = database(lambda: repository.release_setup(
            client, invitation=invitation_id, token_hash=token_hash,
        ))
        if not released:
            raise AppError(
                "Password setup failed and an account may already be associated with this invitation. Contact your administrator.",
                409,
                "INVITATION_SETUP_RECONCILIATION_REQUIRED",
            ) from exc
        raise
    recorded = database(lambda: repository.record_auth_user(
        client,
        invitation=invitation_id,
        token_hash=token_hash,
        auth_user=auth_user_id,
    ))
    if not recorded:
        raise INVALID_LINK
    result = database(lambda: repository.complete(
        client,
        invitation=invitation_id,
        token_hash=token_hash,
        auth_user=auth_user_id,
    ))
    if not isinstance(result, dict) or result.get("accepted") is not True:
        raise AppError("Student account activation could not be confirmed. Retry using this link.", 503, "STUDENT_SETUP_UNCONFIRMED")
    return StudentInvitationCompleteResponse(
        message="Student account setup is complete. You can now sign in.",
        completed=True,
    )
