"""Institution administrators and the protected Owner (User Management U2).

An administrator has the admin permission set, limited to the access areas the
Owner chose (none chosen means full access); the account loader applies the
limit. The Owner always has full access, and alone invites, limits and removes
administrators and transfers ownership. The database enforces this on every command, and an
Owner's invitation stops working if its sender is no longer the Owner.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import institution_admins as repo
from app.repositories.invitations import platform_admin_invitations as invite_repo
from app.schemas.admin.institution_admins import (
    AdminAccessUpdate,
    AdminInvitationCreate,
    InstitutionAdminList,
    InstitutionAdminResult,
)
from app.services.email import email_outbox_crypto
from app.services.invitations import platform_admin_invitations as invitations

DATABASE_ERRORS = {
    "P1401": (403, "OWNER_REQUIRED", "Only the institution Owner can manage administrators."),
    "P1402": (422, "NOT_AN_ADMINISTRATOR", "Choose an active administrator of your institution."),
    "P1403": (409, "OWNER_CANNOT_BE_REMOVED", "Transfer ownership to another administrator before leaving."),
    "P1404": (409, "OWNER_ALWAYS_FULL_ACCESS", "The Owner always has full access."),
    "P1202": (409, "MEMBER_ALREADY_EXISTS", "This email already belongs to someone in your institution."),
    "P1203": (409, "INVITATION_ALREADY_PENDING", "An invitation is already pending for this email."),
    "P0002": (404, "INVITATION_NOT_FOUND", "Invitation not found."),
    "22023": (422, "INVITATION_INVALID", "Check the email address, then try again."),
    "42501": (403, "FORBIDDEN", "You do not have permission to perform this action."),
}


def _call(operation, failure: str):
    try:
        return operation()
    except AppError:
        raise
    except Exception as exc:
        mapped = DATABASE_ERRORS.get(str(getattr(exc, "code", "")))
        if mapped:
            status, code, message = mapped
            raise AppError(message, status, code) from exc
        raise AppError(failure, 502, "ADMINISTRATOR_COMMAND_FAILED") from exc


def list_admins(actor: dict[str, Any], institution_id: UUID) -> InstitutionAdminList:
    data = _call(lambda: repo.read(get_admin_client(), actor["user_id"], institution_id),
                 "Administrators could not be loaded. Try again.")
    owner = data.get("owner_user_id")
    admins = [row | {"is_owner": owner is not None and str(row.get("user_id")) == str(owner)}
              for row in data.get("administrators") or []]
    return InstitutionAdminList(
        owner_user_id=owner,
        viewer_is_owner=owner is not None and str(owner) == str(actor["user_id"]),
        administrators=admins,
        invitations=data.get("invitations") or [],
        access_area_options=data.get("access_areas") or [],
    )


def invite(actor: dict[str, Any], institution_id: UUID, body: AdminInvitationCreate) -> InstitutionAdminResult:
    raw_token = invite_repo.generate_invitation_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=invitations.INVITATION_TTL_HOURS)
    _call(lambda: repo.create_invitation(
        get_admin_client(), actor_id=actor["user_id"], institution_id=institution_id,
        email=body.email, full_name=body.full_name, access_areas=body.access_areas,
        token_hash=invite_repo.hash_invitation_token(raw_token), expires_at=expires_at,
        protected_token=email_outbox_crypto.protect_invitation_token(raw_token),
    ), "The invitation could not be created. Try again.")
    # The raw token is delivered only by email; it is never returned.
    return InstitutionAdminResult(
        message=f"Invitation sent to {body.email}. They become an administrator once they accept.")


def cancel_invitation(actor: dict[str, Any], institution_id: UUID, invitation_id: UUID) -> InstitutionAdminResult:
    result = _call(lambda: repo.cancel_invitation(get_admin_client(), actor["user_id"], institution_id, invitation_id),
                   "The invitation could not be cancelled. Try again.")
    cancelled = bool(result.get("cancelled"))
    return InstitutionAdminResult(
        message="Invitation cancelled. The link no longer works." if cancelled
        else "This invitation was already closed.",
        already_applied=not cancelled,
    )


def revoke(actor: dict[str, Any], institution_id: UUID, user_id: UUID) -> InstitutionAdminResult:
    _call(lambda: repo.revoke(get_admin_client(), actor["user_id"], institution_id, user_id),
          "Administrator access could not be removed. Try again.")
    return InstitutionAdminResult(message="Administrator access removed. Their account and records are kept.")


def transfer_ownership(actor: dict[str, Any], institution_id: UUID, user_id: UUID) -> InstitutionAdminResult:
    result = _call(lambda: repo.transfer_ownership(get_admin_client(), actor["user_id"], institution_id, user_id),
                   "Ownership could not be transferred. Try again.")
    already = bool(result.get("already_applied"))
    return InstitutionAdminResult(
        message="You are already the Owner." if already
        else "Ownership transferred. You remain an administrator.",
        already_applied=already,
    )


def set_access(
    actor: dict[str, Any], institution_id: UUID, user_id: UUID, body: AdminAccessUpdate,
) -> InstitutionAdminResult:
    """Limit an administrator to some access areas, or give full access again."""
    result = _call(lambda: repo.set_access(get_admin_client(), actor["user_id"], institution_id, user_id,
                                           body.access_areas),
                   "Access could not be changed. Try again.")
    full = bool(result.get("full_access"))
    return InstitutionAdminResult(
        message="Full access given. Changes apply on their next request." if full
        else "Access updated. Changes apply on their next request.")
