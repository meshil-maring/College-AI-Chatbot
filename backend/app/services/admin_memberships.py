"""Phase 7.23 institution-scoped Staff/Faculty lifecycle orchestration."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import admin_memberships as repo
from app.repositories import platform_admin_invitations as invitation_repo
from app.repositories.admin_audit import record_admin_action
from app.schemas.admin import AdminAuditLogCreate
from app.schemas.admin_memberships import (
    MembershipDecisionResult,
    MembershipLifecycleResult,
    MembershipRequestList,
    MembershipRequestView,
    MembershipRoster,
    MembershipRosterEntry,
)
from app.services import platform_admin_invitations as invitations
from app.services import email_outbox_crypto

ALLOWED_ROLES = frozenset({"staff", "faculty"})
REQUEST_STATUSES = frozenset({"pending", "approved", "rejected"})
ROSTER_STATUSES = frozenset(
    {"active", "inactive", "deactivated", "invited", "pending"}
)


def _audit(actor: dict[str, Any], action: str, record_id: str, data: dict[str, Any]) -> None:
    record_admin_action(
        get_admin_client(),
        AdminAuditLogCreate(
            actor_user_id=UUID(str(actor["user_id"])),
            action=action,
            table_name="institution_membership_requests",
            record_id=record_id,
            record_data=data,
        ),
    )


def _role(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in ALLOWED_ROLES:
        raise AppError("Unsupported membership role", 422, "INVALID_MEMBERSHIP_ROLE")
    return value


def list_requests(
    institution_id: UUID, *, role: str | None = None, status: str | None = None
) -> MembershipRequestList:
    role = _role(role)
    if status is not None and status not in REQUEST_STATUSES:
        raise AppError("Unsupported request status", 422, "INVALID_MEMBERSHIP_STATUS")
    rows = repo.list_requests(
        get_admin_client(), institution_id, role=role, status=status
    )
    requests = [
        MembershipRequestView(
            request_id=row["request_id"],
            full_name=str(row.get("full_name") or ""),
            email=str(row.get("official_email") or ""),
            requested_role=row["requested_role"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
        if row.get("requested_role") in ALLOWED_ROLES
    ]
    return MembershipRequestList(requests=requests, total=len(requests))


def decide_request(
    actor: dict[str, Any],
    institution_id: UUID,
    request_id: UUID,
    *,
    approve: bool,
    reason: str | None,
) -> MembershipDecisionResult:
    client = get_admin_client()
    row = repo.get_request_for_institution(client, request_id, institution_id)
    if row is None:
        raise AppError("Membership request not found", 404, "MEMBERSHIP_REQUEST_NOT_FOUND")
    role = _role(str(row.get("requested_role")))
    desired = "approved" if approve else "rejected"
    current = str(row.get("status"))
    if current == desired:
        return MembershipDecisionResult(
            request_id=request_id,
            status=desired,
            already_applied=True,
            message=f"Membership request is already {desired}.",
        )
    if current != "pending":
        raise AppError(
            "Membership request has already received a different decision",
            409,
            "MEMBERSHIP_REQUEST_ALREADY_DECIDED",
        )
    if approve:
        applicant = repo.get_user(client, row.get("user_id"))
        if (
            applicant is None
            or str(applicant.get("id")) != str(row.get("user_id"))
            or str(applicant.get("email") or "").strip().lower()
            != str(row.get("official_email") or "").strip().lower()
            or applicant.get("status") != "active"
        ):
            raise AppError(
                "The applicant account is not in a valid state",
                409,
                "APPLICANT_STATE_INVALID",
            )
    if approve:
        raw_token = invitation_repo.generate_invitation_token()
        decided = repo.approve_with_invitation(
            client,
            request_id=request_id,
            institution_id=institution_id,
            decided_by_user_id=actor["user_id"],
            reason=reason,
            token_hash=invitation_repo.hash_invitation_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=invitations.INVITATION_TTL_HOURS),
            protected_token=email_outbox_crypto.protect_invitation_token(raw_token),
        )
        if decided.get("already_applied"):
            return MembershipDecisionResult(
                request_id=request_id,
                status="approved",
                already_applied=True,
                message="Membership request is already approved.",
            )
        if decided.get("not_found"):
            raise AppError("Membership request not found", 404, "MEMBERSHIP_REQUEST_NOT_FOUND")
        if decided.get("invalid_role"):
            raise AppError("Unsupported membership role", 422, "INVALID_MEMBERSHIP_ROLE")
        if decided.get("invalid_state"):
            raise AppError("The applicant account is not in a valid state", 409, "APPLICANT_STATE_INVALID")
        if decided.get("conflict"):
            raise AppError("Membership request was decided concurrently", 409, "MEMBERSHIP_REQUEST_CONFLICT")
    else:
        decided = repo.decide_pending_request(
            client,
            request_id=request_id,
            institution_id=institution_id,
            status=desired,
            decided_by_user_id=actor["user_id"],
            reason=reason,
        )
    if decided is None:
        latest = repo.get_request_for_institution(client, request_id, institution_id)
        if latest is not None and latest.get("status") == desired:
            return MembershipDecisionResult(
                request_id=request_id,
                status=desired,
                already_applied=True,
                message=f"Membership request is already {desired}.",
            )
        raise AppError(
            "Membership request was decided concurrently",
            409,
            "MEMBERSHIP_REQUEST_CONFLICT",
        )

    invitation_status = None
    if approve:
        invitation_status = "invited"
        action = f"{role}_invitation_created"
    else:
        action = "membership_request_rejected"
    _audit(
        actor,
        action if approve else "membership_request_rejected",
        str(request_id),
        {"role": role, "status": desired},
    )
    if approve:
        _audit(
            actor,
            "membership_request_approved",
            str(request_id),
            {"role": role, "status": desired},
        )
    return MembershipDecisionResult(
        request_id=request_id,
        status=desired,
        invitation_status=invitation_status,
        message=(
            "Membership request approved and invitation queued."
            if approve
            else "Membership request rejected. No role was assigned."
        ),
    )


def list_roster(
    institution_id: UUID, *, role: str | None = None, status: str | None = None
) -> MembershipRoster:
    role = _role(role)
    if status is not None and status not in ROSTER_STATUSES:
        raise AppError("Unsupported roster status", 422, "INVALID_MEMBERSHIP_STATUS")
    if status == "pending":
        status = "invited"
    client = get_admin_client()
    entries: list[MembershipRosterEntry] = []
    for grant in repo.list_scoped_role_grants(client, institution_id):
        role_row = grant.get("roles") or {}
        role_name = role_row.get("name") if isinstance(role_row, dict) else None
        user = grant.get("users") or {}
        if role_name not in ALLOWED_ROLES or (role is not None and role_name != role):
            continue
        account_status = str(user.get("status") or "inactive")
        if status is not None and status != account_status:
            continue
        entries.append(
            MembershipRosterEntry(
                user_id=user.get("id") or grant.get("user_id"),
                name=" ".join(
                    part for part in [user.get("first_name"), user.get("last_name")] if part
                ),
                email=str(user.get("email") or ""),
                role=role_name,
                status=account_status,
                created_at=user.get("created_at") or grant.get("created_at"),
                updated_at=user.get("updated_at") or grant.get("updated_at"),
            )
        )
    if status is None or status == "invited":
        for invitation in invitation_repo.list_invitations(client, institution_id):
            role_name = invitation.get("role_name")
            if role_name not in ALLOWED_ROLES or (role is not None and role_name != role):
                continue
            if invitation.get("status") != invitation_repo.STATUS_INVITED:
                continue
            entries.append(
                MembershipRosterEntry(
                    invitation_id=invitation["invitation_id"],
                    name="",
                    email=str(invitation.get("email") or ""),
                    role=role_name,
                    status="invited",
                    invitation_status=str(invitation.get("email_delivery_status") or "pending"),
                    created_at=invitation.get("created_at"),
                    updated_at=invitation.get("updated_at"),
                )
            )
    entries.sort(key=lambda item: (item.role, item.email.lower()))
    return MembershipRoster(members=entries, total=len(entries))


def set_active(
    actor: dict[str, Any], institution_id: UUID, user_id: UUID, *, active: bool
) -> MembershipLifecycleResult:
    client = get_admin_client()
    user = repo.get_user(client, user_id)
    grants = repo.list_user_grants(client, user_id)
    scoped_roles: set[str] = set()
    has_target_scope = False
    for grant in grants:
        role_row = grant.get("roles") or {}
        role_name = role_row.get("name") if isinstance(role_row, dict) else None
        if role_name:
            scoped_roles.add(str(role_name))
        if (
            role_name in ALLOWED_ROLES
            and grant.get("scope_type") == "institution"
            and str(grant.get("scope_id")) == str(institution_id)
        ):
            has_target_scope = True
    if user is None or not has_target_scope:
        raise AppError("Staff or faculty member not found", 404, "MEMBERSHIP_NOT_FOUND")
    if scoped_roles - ALLOWED_ROLES:
        raise AppError(
            "Accounts with other roles cannot be changed through this roster",
            409,
            "PROTECTED_ROLE",
        )
    desired = "active" if active else "deactivated"
    current = str(user.get("status"))
    if current == desired:
        return MembershipLifecycleResult(
            user_id=user_id,
            status=desired,
            already_applied=True,
            message=f"Member is already {desired}.",
        )
    expected = ("inactive", "deactivated") if active else ("active", "inactive")
    if not repo.set_user_status(client, user_id, expected=expected, status=desired):
        raise AppError("Member status changed concurrently", 409, "MEMBERSHIP_STATUS_CONFLICT")
    role_label = "faculty" if "faculty" in scoped_roles else "staff"
    _audit(
        actor,
        f"{role_label}_{'reactivated' if active else 'deactivated'}",
        str(user_id),
        {"role": role_label, "status": desired},
    )
    return MembershipLifecycleResult(
        user_id=user_id,
        status=desired,
        already_applied=False,
        message=f"Member {desired}.",
    )


def resend(
    actor: dict[str, Any], institution_id: UUID, invitation_id: UUID, peer: str | None
):
    invitation = invitation_repo.get_invitation_by_id(get_admin_client(), invitation_id)
    if (
        invitation is None
        or str(invitation.get("institution_id")) != str(institution_id)
        or invitation.get("role_name") not in ALLOWED_ROLES
    ):
        raise AppError("Invitation not found", 404, "INVITATION_NOT_FOUND")
    result = invitations.resend_invitation(
        actor, institution_id, invitation_id, peer=peer
    )
    _audit(
        actor,
        "membership_invitation_resent",
        str(invitation_id),
        {"role": invitation["role_name"], "email": invitation["email"]},
    )
    return result
