"""Invitation-only Super Admin registration (Phase 9).

Creation/listing/cancellation are Super Admin only (``require_super_admin`` at
the route). Registration is authorized by possession of a single-use, expiring
token; the account email comes from the invitation row, never the request, and
the role is the server constant ``super_admin`` at platform scope, assigned via
the existing ``phase712_assign_super_admin`` function. Only the SHA-256 digest
of the token is stored. Passwords go straight to Supabase Auth.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import platform_admin_invitations as token_repo
from app.schemas.super_admin_registration import (
    SuperAdminInvitationListResponse,
    SuperAdminInvitationView,
    SuperAdminInviteCreatedResponse,
    SuperAdminInvitePublicView,
    SuperAdminRegisteredResponse,
    SuperAdminRegisterRequest,
)
from app.services import invitation_abuse_controls as abuse
from app.services import student_registration as student_svc

logger = logging.getLogger(__name__)

TABLE = "platform_super_admin_invitations"
INVITATION_TTL_HOURS = 24
REGISTER_ROUTE = "/super-admin-invite/{token}"
VIEW_COLUMNS = "invitation_id, email, status, expires_at, created_at, acceptance_id"

_INVALID = ("This invitation link is not valid", 400, "INVITATION_INVALID")


def _invalid() -> AppError:
    return AppError(_INVALID[0], status_code=_INVALID[1], code=_INVALID[2])


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return [row for row in data if row]
    return [data] if data else []


def _parse(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _expired(row: dict[str, Any]) -> bool:
    expires = _parse(row.get("expires_at"))
    return expires is None or expires <= datetime.now(timezone.utc)


def _actor_id(actor: dict[str, Any]) -> str:
    user_id = actor.get("user_id")
    if not user_id:
        raise AppError(
            "You do not have permission to perform this action",
            status_code=403,
            code="FORBIDDEN",
        )
    return str(user_id)


def _resolve_live(client, raw_token: str) -> dict[str, Any]:
    if not raw_token or not (32 <= len(raw_token) <= 256):
        raise _invalid()
    rows = _rows(
        client.table(TABLE)
        .select("*")
        .eq("token_hash", token_repo.hash_invitation_token(raw_token))
        .limit(1)
        .execute()
    )
    if not rows:
        raise _invalid()
    row = rows[0]
    status = row.get("status")
    if status == "cancelled":
        raise AppError("This invitation has been cancelled", status_code=410, code="INVITATION_CANCELLED")
    if status == "accepted":
        return row
    if status == "expired" or (_expired(row) and not row.get("acceptance_id")):
        raise AppError("This invitation has expired", status_code=410, code="INVITATION_EXPIRED")
    return row


def create_invitation(actor: dict[str, Any], email: str) -> SuperAdminInviteCreatedResponse:
    actor_id = _actor_id(actor)
    client = get_admin_client()

    existing_user = _rows(
        client.table("users").select("id").eq("email", email).limit(1).execute()
    )
    if existing_user:
        raise AppError(
            "An account already exists for this email address",
            status_code=409,
            code="ACCOUNT_ALREADY_EXISTS",
        )

    pending = _rows(
        client.table(TABLE)
        .select(VIEW_COLUMNS)
        .eq("email", email)
        .eq("status", "invited")
        .execute()
    )
    for row in pending:
        if row.get("acceptance_id"):
            raise AppError("The previous acceptance requires reconciliation", 409,
                           "INVITATION_RECONCILIATION_REQUIRED")
        if not _expired(row):
            raise AppError(
                "An active invitation already exists for this email address",
                status_code=409,
                code="INVITATION_ALREADY_PENDING",
            )
        if token_repo.transition_invitation(client, row["invitation_id"], kind="platform", status="expired") is None:
            raise AppError("Expiry conflicts with recorded acceptance", 409, "INVITATION_RECONCILIATION_REQUIRED")

    raw_token = token_repo.generate_invitation_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITATION_TTL_HOURS)
    inserted = _rows(
        client.table(TABLE)
        .insert(
            {
                "email": email,
                "token_hash": token_repo.hash_invitation_token(raw_token),
                "expires_at": expires_at.isoformat(),
                "created_by": actor_id,
            }
        )
        .execute()
    )
    if not inserted:
        raise AppError("Unable to create the invitation", status_code=500, code="INVITATION_CREATE_FAILED")
    logger.info("event=super_admin_invited actor=%s", actor_id)
    return SuperAdminInviteCreatedResponse(
        invitation=SuperAdminInvitationView(**{k: inserted[0].get(k) for k in SuperAdminInvitationView.model_fields}),
        invitation_token=raw_token,
        invitation_url=REGISTER_ROUTE.format(token=raw_token),
        expires_in_hours=INVITATION_TTL_HOURS,
    )


def list_invitations() -> SuperAdminInvitationListResponse:
    client = get_admin_client()
    rows = _rows(
        client.table(TABLE)
        .select(VIEW_COLUMNS)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    views = []
    for row in rows:
        if row.get("status") == "invited" and _expired(row):
            row = {**row, "status": "expired"}
        views.append(SuperAdminInvitationView(**row))
    return SuperAdminInvitationListResponse(invitations=views)


def cancel_invitation(actor: dict[str, Any], invitation_id: str) -> SuperAdminInvitationView:
    actor_id = _actor_id(actor)
    client = get_admin_client()
    try:
        result = token_repo.transition_invitation(
            client, invitation_id, kind="platform", status="cancelled", actor_user_id=actor_id,
        )
    except Exception as exc:
        raise AppError("Cancellation outcome requires reconciliation", 409,
                       "INVITATION_CANCELLATION_UNCERTAIN") from exc
    if not result:
        latest = _rows(client.table(TABLE).select("*").eq("invitation_id", str(invitation_id)).limit(1).execute())
        raise AppError(
            "Invitation could not be cancelled; acceptance may require reconciliation",
            status_code=409 if latest else 404,
            code="INVITATION_CANCELLATION_CONFLICT" if latest else "INVITATION_NOT_FOUND",
        )
    logger.info("event=super_admin_invitation_cancelled actor=%s", actor_id)
    return SuperAdminInvitationView(**{k: result["invitation"].get(k) for k in SuperAdminInvitationView.model_fields})


def inspect_invitation(raw_token: str, *, peer: str | None = None) -> SuperAdminInvitePublicView:
    abuse.enforce_inspect_rate_limit(peer)
    client = get_admin_client()
    row = _resolve_live(client, raw_token)
    recovery = (token_repo.recover_accepted_operation(
        client, row["invitation_id"], token_repo.hash_invitation_token(raw_token), kind="platform",
    ) if row.get("status") == "accepted" and row.get("acceptance_id") else None)
    return SuperAdminInvitePublicView(
        email=str(row["email"]), status=str(row["status"]), expires_at=row.get("expires_at"),
        account_recovery_available=bool(recovery),
    )


def recover_account(raw_token: str, *, peer: str | None = None) -> SuperAdminRegisteredResponse:
    digest = token_repo.hash_invitation_token(raw_token or "")
    abuse.enforce_accept_rate_limit(digest, peer)
    client = get_admin_client()
    invitation = _resolve_live(client, raw_token)
    from app.services.invitation_operations import recover_accepted_account
    recover_accepted_account(client, invitation, digest, kind="platform")
    return SuperAdminRegisteredResponse(
        email=invitation["email"], message="Your Super Admin account is ready. Sign in with the password you created.",
    )


def register_super_admin(
    raw_token: str, payload: SuperAdminRegisterRequest, *, peer: str | None = None
) -> SuperAdminRegisteredResponse:
    abuse.enforce_accept_rate_limit(token_repo.hash_invitation_token(raw_token or ""), peer)
    if payload.password != payload.confirm_password:
        raise AppError("Passwords do not match", status_code=422, code="PASSWORD_MISMATCH")

    client = get_admin_client()
    invitation = _resolve_live(client, raw_token)
    email = str(invitation["email"]).strip().lower()

    if not invitation.get("acceptance_id") and _rows(client.table("users").select("id").eq("email", email).limit(1).execute()):
        raise AppError(
            "An account already exists for this email address",
            status_code=409,
            code="ACCOUNT_ALREADY_EXISTS",
        )

    acceptance_id = invitation.get("acceptance_id") or uuid4()
    token_hash = token_repo.hash_invitation_token(raw_token)
    try:
        reserved = token_repo.reserve_invitation(
            client, invitation["invitation_id"], kind="platform",
            token_hash=token_hash, acceptance_id=acceptance_id,
        )
        if reserved is None:
            raise _invalid()
        from app.services.invitation_operations import complete_acceptance
        complete_acceptance(client, invitation, reserved, acceptance_id=acceptance_id,
                            token_hash=token_hash, payload=payload, kind="platform")
    except Exception as exc:
        if isinstance(exc, AppError):
            raise
        raise AppError("Registration needs reconciliation. Retry to recover recorded progress.",
                       409, "INVITATION_RECONCILIATION_REQUIRED") from exc

    logger.info("event=super_admin_registered")
    return SuperAdminRegisteredResponse(
        email=email,
        message="Your Super Admin account is ready. Sign in with the password you just created.",
    )
