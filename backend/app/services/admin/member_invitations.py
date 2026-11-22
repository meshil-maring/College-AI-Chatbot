"""Staff and Faculty invited by an institution administrator.

The administrator chooses the person's email, name, role and department. The
institution comes from the administrator's own scope and the expiry, token and
role grant are server-side. The database function re-checks that the actor
administers the institution, that the department is active and belongs to it,
that the person is not already a member and that no invitation is pending.

Acceptance uses the existing invitation link and account setup. When the person
accepts, the database records an approved membership request decided by the
inviting administrator, grants the role and assigns the department together.
An invitation may also carry the employee profile and additional departments;
the database applies them in the same acceptance transaction.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import member_invitations as repo
from app.repositories.admin.admin_audit import record_admin_action
from app.repositories.invitations import platform_admin_invitations as invite_repo
from app.schemas.admin.admin import AdminAuditLogCreate
from app.schemas.admin.member_invitations import (
    MemberInvitationCancelled,
    MemberInvitationCreate,
    MemberInvitationCreated,
    MemberInvitationList,
    MemberInvitationView,
)
from app.schemas.invitations.admin_invitations import EmailDeliveryOutcome
from app.services.email import email_outbox_crypto
from app.services.invitations import platform_admin_invitations as invitations

INVITATION_TTL_HOURS = invitations.INVITATION_TTL_HOURS

DATABASE_ERRORS = {
    "P1201": (422, "DEPARTMENT_INVALID", "Choose an active department of your institution."),
    "P1202": (
        409, "MEMBER_ALREADY_EXISTS",
        "This email already belongs to a member of your institution. Manage them from the roster.",
    ),
    "P1203": (
        409, "INVITATION_ALREADY_PENDING",
        "An invitation is already pending for this email. Resend it from Pending invitations.",
    ),
    "P1204": (409, "EMPLOYEE_ID_IN_USE", "This employee ID is already used in your institution."),
    "22023": (422, "INVITATION_INVALID", "Check the email, role and department, then try again."),
    "42501": (403, "FORBIDDEN", "You do not have permission to perform this action."),
}


def _audit(
    actor: dict[str, Any], institution_id: UUID, action: str, record_id: str, data: dict,
    *, table_name: str = "platform_admin_invitations",
) -> None:
    record_admin_action(
        get_admin_client(),
        AdminAuditLogCreate(
            actor_user_id=UUID(str(actor["user_id"])),
            institution_id=institution_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            record_data=data,
        ),
    )


def _status(row: dict[str, Any]) -> str:
    """A pending invitation past its expiry is shown as expired before the sweep runs."""
    status = str(row.get("status") or invite_repo.STATUS_INVITED)
    if status != invite_repo.STATUS_INVITED:
        return status
    expires = row.get("expires_at")
    try:
        moment = datetime.fromisoformat(str(expires).replace("Z", "+00:00")) if expires else None
    except ValueError:
        moment = None
    if moment is not None and moment.tzinfo is not None and moment <= datetime.now(timezone.utc):
        return invite_repo.STATUS_EXPIRED
    return status


def _view(row: dict[str, Any]) -> MemberInvitationView:
    department = row.get("invited_department_id")
    profile = row.get("invited_profile") or {}
    common = profile.get("common") if isinstance(profile, dict) else None
    common = common if isinstance(common, dict) else {}
    return MemberInvitationView(
        invitation_id=UUID(str(row["invitation_id"])),
        email=str(row["email"]),
        full_name=row.get("invited_full_name"),
        role=row["role_name"],
        department_id=UUID(str(department)) if department else None,
        employee_id=common.get("employee_id"),
        designation=common.get("designation"),
        status=_status(row),
        expires_at=row.get("expires_at"),
        created_at=row.get("created_at"),
        email_delivery_status=str(row.get("email_delivery_status") or invite_repo.DELIVERY_PENDING),
        resend_count=int(row.get("resend_count") or 0),
        last_sent_at=row.get("last_sent_at"),
    )


def create(actor: dict[str, Any], institution_id: UUID, body: MemberInvitationCreate) -> MemberInvitationCreated:
    raw_token = invite_repo.generate_invitation_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITATION_TTL_HOURS)
    try:
        row = repo.create(
            get_admin_client(),
            actor_id=actor["user_id"],
            institution_id=institution_id,
            email=body.email,
            full_name=body.full_name,
            role=body.role,
            department_id=body.department_id,
            token_hash=invite_repo.hash_invitation_token(raw_token),
            expires_at=expires_at,
            protected_token=email_outbox_crypto.protect_invitation_token(raw_token),
            profile=body.database_profile(),
        )
    except AppError:
        raise
    except Exception as exc:
        mapped = DATABASE_ERRORS.get(str(getattr(exc, "code", "")))
        if mapped:
            status, code, message = mapped
            raise AppError(message, status, code) from exc
        raise AppError("The invitation could not be created. Try again.", 502, "INVITATION_CREATE_FAILED") from exc
    # The raw token is never returned: it is delivered only by email.
    # Teachers are Faculty; there is no separate Teacher role.
    role = "Staff" if body.role == "staff" else "Faculty (Teacher)"
    return MemberInvitationCreated(
        invitation=_view(row),
        email_delivery=EmailDeliveryOutcome(status="pending", provider="outbox"),
        expires_in_hours=INVITATION_TTL_HOURS,
        message=f"Invitation sent to {body.email}. They join as {role} once they accept.",
    )


def list_pending(institution_id: UUID) -> MemberInvitationList:
    """Invitations still waiting for the person, plus recently expired ones to resend."""
    rows = repo.list_staff_faculty(get_admin_client(), institution_id)
    views = [_view(row) for row in rows]
    shown = [view for view in views if view.status in ("invited", "expired")]
    return MemberInvitationList(invitations=shown, total=len(shown))


def cancel(actor: dict[str, Any], institution_id: UUID, invitation_id: UUID) -> MemberInvitationCancelled:
    invitation = repo.get(get_admin_client(), institution_id, invitation_id)
    if invitation is None:
        raise AppError("Invitation not found", 404, "INVITATION_NOT_FOUND")
    result = invitations.cancel_invitation(actor, institution_id, invitation_id)
    if not result.already_applied:
        _audit(actor, institution_id, "membership_invitation_cancelled", str(invitation_id),
               {"role": invitation["role_name"], "email": invitation["email"]})
    return MemberInvitationCancelled(
        invitation_id=invitation_id,
        already_applied=result.already_applied,
        message="Invitation cancelled. The link no longer works.",
    )


def resend(actor: dict[str, Any], institution_id: UUID, invitation_id: UUID, peer: str | None):
    """Send a Staff/Faculty invitation again, only within the administrator's institution."""
    invitation = invite_repo.get_invitation_by_id(get_admin_client(), invitation_id)
    if (
        invitation is None
        or str(invitation.get("institution_id")) != str(institution_id)
        or invitation.get("role_name") not in ("staff", "faculty")
    ):
        raise AppError("Invitation not found", 404, "INVITATION_NOT_FOUND")
    result = invitations.resend_invitation(actor, institution_id, invitation_id, peer=peer)
    _audit(actor, institution_id, "membership_invitation_resent", str(invitation_id),
           {"role": invitation["role_name"], "email": invitation["email"]},
           table_name="institution_membership_requests")
    return result
