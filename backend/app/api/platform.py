"""Platform API boundary.

Phase 7.12 established ``/platform/me`` as the proof that a principal holds
platform scope. Phase 7.13 adds the first real platform-management capability:
institution management.

Every route below depends on ``require_super_admin``, which re-reads the account
lifecycle and the active ``super_admin`` platform grant from the database on
each request. There is no role, scope or tenant parameter for a client to
supply: an ``institution_id`` in the path is a *resource* identifier only, and
the actor is always the server-resolved application user behind the verified JWT.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.core.security import require_super_admin
from app.schemas.admin_invitations import (
    AdminInvitationCancellationResponse,
    AdminInvitationCreateRequest,
    AdminInvitationCreatedResponse,
    AdminInvitationExpirySweepResult,
    AdminInvitationResendResponse,
    AdminRevocationResponse,
    AdminRosterResponse,
    PlatformAuditListResponse,
)
from app.schemas.platform import (
    AdminAssignmentRequest,
    InstitutionAdminAssignmentResponse,
    InstitutionCreateRequest,
    InstitutionDetailResponse,
    InstitutionLifecycleResponse,
    InstitutionListResponse,
    InstitutionUpdateRequest,
)
from app.services import platform_admin_invitations as invitations_service
from app.services import platform_institutions as service

router = APIRouter(prefix="/platform", tags=["platform"])

# One dependency bound once so it is impossible for a platform route to be
# added without the same authorization guard.
_SUPER_ADMIN = require_super_admin


@router.get("/me")
async def platform_me(current_user: dict = Depends(_SUPER_ADMIN)) -> dict[str, str]:
    """Return only the safe identity needed to prove platform authorization."""
    return {"role": "super_admin", "scope": "platform"}


@router.get(
    "/institutions",
    response_model=InstitutionListResponse,
    summary="List every institution on the platform (Super Admin)",
)
async def list_platform_institutions(
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionListResponse:
    """Return safe platform metadata for every institution.

    Exposes only id, code, name, lifecycle status, availability and the count
    of assigned admins. Never student information, academic records, documents,
    credentials or any other tenant-owned data.
    """
    return service.list_institutions()


@router.post(
    "/institutions",
    response_model=InstitutionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an institution (Super Admin)",
)
async def create_platform_institution(
    body: InstitutionCreateRequest,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionDetailResponse:
    """Create an institution in ACTIVE status.

    Only ``name`` and ``code`` are required; branding is optional. The code is
    normalized and validated server-side and must be unique. The institution is
    attached to the reserved platform organization, so the Super Admin never
    selects a tenant parent. The action is audited as ``institution_created``.
    """
    return service.create_institution(current_user, body)


@router.get(
    "/institutions/{institution_id}",
    response_model=InstitutionDetailResponse,
    summary="Read one institution's platform configuration (Super Admin)",
)
async def read_platform_institution(
    institution_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionDetailResponse:
    """Return one institution's safe detail projection."""
    return service.get_institution(institution_id)


@router.patch(
    "/institutions/{institution_id}",
    response_model=InstitutionDetailResponse,
    summary="Update an institution's configuration (Super Admin)",
)
async def update_platform_institution(
    institution_id: UUID,
    body: InstitutionUpdateRequest,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionDetailResponse:
    """Update name, routing code and optional branding/contact configuration.

    The primary key and the owning organization are structurally unchangeable, so
    this can never reassign an existing institution's students, knowledge or
    documents. Lifecycle status is intentionally NOT part of this payload: use
    the dedicated suspend/activate endpoints so each transition is separately
    confirmed and separately audited.
    """
    return service.update_institution(current_user, institution_id, body)


@router.post(
    "/institutions/{institution_id}/suspend",
    response_model=InstitutionLifecycleResponse,
    summary="Suspend an institution (Super Admin)",
)
async def suspend_platform_institution(
    institution_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionLifecycleResponse:
    """Restrict an institution's normal access while retaining all its data.

    No student, faculty, staff, admin, knowledge or document row is deleted and
    no account is revoked. Audited as ``institution_suspended``.
    """
    return service.suspend_institution(current_user, institution_id)


@router.post(
    "/institutions/{institution_id}/activate",
    response_model=InstitutionLifecycleResponse,
    summary="Approve/activate a pending or suspended institution (Super Admin)",
)
async def activate_platform_institution(
    institution_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionLifecycleResponse:
    """Approve a pending institution or restore a suspended institution.

    Pending self-registrations become usable only through this explicit,
    protected platform action. Because suspension never removed data,
    restoring active status also fully restores a suspended tenant. Audited as
    ``institution_activated``.
    """
    return service.activate_institution(current_user, institution_id)


@router.post(
    "/institutions/{institution_id}/admins",
    response_model=InstitutionAdminAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign an existing account as University Admin (Super Admin)",
)
async def assign_platform_institution_admin(
    institution_id: UUID,
    body: AdminAssignmentRequest,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionAdminAssignmentResponse:
    """Grant the institution-scoped ``admin`` role to an existing account.

    The account must already exist; this endpoint never provisions an Auth
    account and accepts no password. The granted role is fixed to
    institution-scoped ``admin``, so it can never confer ``super_admin`` or any
    platform scope. Audited as ``admin_assigned``.
    """
    return service.assign_university_admin(current_user, institution_id, body)


# ===========================================================================
# Phase 7.14 — University Admin lifecycle (invite / roster / revoke / audit)
#
# Every route below re-declares the SAME `Depends(_SUPER_ADMIN)` guard used by
# the Phase 7.12/7.13 routes. A University Admin of ANY institution — including
# the very institution named in the path — receives 403 here, because platform
# authority is decided by the server-resolved `super_admin` grant alone.
# ===========================================================================


@router.post(
    "/institutions/{institution_id}/admins/invitations",
    response_model=AdminInvitationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a University Admin (Super Admin)",
)
async def create_platform_admin_invitation(
    institution_id: UUID,
    body: AdminInvitationCreateRequest,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> AdminInvitationCreatedResponse:
    """Issue a one-time, expiring University Admin invitation.

    The payload is an email and nothing else: no password, no Auth credential,
    and no role/scope/institution field. The granted role is the server constant
    ``admin`` and the invitation is bound to exactly one institution, so it can
    never confer ``super_admin`` and can never reach another tenant. The raw
    token is returned exactly once in this response and is stored only as a
    SHA-256 digest. Audited as ``institution_admin_invited``.
    """
    return invitations_service.create_invitation(current_user, institution_id, body)


@router.get(
    "/institutions/{institution_id}/admins/roster",
    response_model=AdminRosterResponse,
    summary="Read the University Admin roster (Super Admin)",
)
async def read_platform_admin_roster(
    institution_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> AdminRosterResponse:
    """List an institution's accepted admins plus its pending invitations.

    Exposes only email, lifecycle status, opaque ids and the expiry. Never a
    password, token, name record or student data.
    """
    return invitations_service.get_admin_roster(institution_id)


@router.post(
    "/institutions/{institution_id}/admins/invitations/{invitation_id}/cancel",
    response_model=AdminInvitationCancellationResponse,
    summary="Cancel a pending University Admin invitation (Super Admin)",
)
async def cancel_platform_admin_invitation(
    institution_id: UUID,
    invitation_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> AdminInvitationCancellationResponse:
    """Make a pending invitation's token permanently unusable.

    The institution binding is verified before any mutation, so an invitation
    belonging to another tenant can never be cancelled through this path. The
    invitation record itself is retained for the audit trail. Audited as
    ``institution_admin_invitation_cancelled``.
    """
    return invitations_service.cancel_invitation(
        current_user, institution_id, invitation_id
    )


@router.post(
    "/institutions/{institution_id}/admins/invitations/{invitation_id}/resend",
    response_model=AdminInvitationResendResponse,
    summary="Resend a pending University Admin invitation (Super Admin)",
)
async def resend_platform_admin_invitation(
    institution_id: UUID,
    invitation_id: UUID,
    request: Request,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> AdminInvitationResendResponse:
    """Issue a NEW link for a pending invitation and email it.

    The previous token is overwritten in the same row, so the old URL stops
    working immediately and only one invitation URL is ever live. Only a
    PENDING invitation can be resent — an accepted, cancelled or expired one is
    refused with 409 and left untouched. The institution binding is verified
    before anything is written, so another tenant's invitation cannot be resent
    by guessing its id.

    Rate limited per invitation, per institution, per actor and per peer
    address (3/10/20/5 per 300 s by default), returning a safe 429.

    Audited as ``institution_admin_invitation_resent``, plus
    ``..._email_sent`` / ``..._email_failed`` for the delivery outcome. The new
    raw token appears only in this response; it is stored solely as a SHA-256
    digest.
    """
    client = request.client
    return invitations_service.resend_invitation(
        current_user,
        institution_id,
        invitation_id,
        peer=client.host if client is not None else "unknown",
    )


@router.post(
    "/admin-invitations/expire-sweep",
    response_model=AdminInvitationExpirySweepResult,
    summary="Run the University Admin invitation expiry sweep (Super Admin)",
)
async def expire_platform_admin_invitations(
    limit: int = 200,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> AdminInvitationExpirySweepResult:
    """Transition elapsed pending invitations to ``expired``.

    CLEANUP, NOT A SECURITY BOUNDARY: acceptance independently refuses an
    elapsed invitation through the ``expires_at > now()`` predicate inside the
    atomic claim, so this route's absence or failure cannot make an expired
    invitation usable.

    It is a manual execution boundary for local development, tests and a future
    scheduler. No background worker runs in this deployment, and none is
    claimed: wiring this to cron or a platform scheduler is a deployment
    concern for a later phase. Running it twice is safe and reports
    ``expired=0`` the second time.
    """
    return invitations_service.expire_pending_admin_invitations(limit=limit)


@router.post(
    "/institutions/{institution_id}/admins/{user_id}/revoke",
    response_model=AdminRevocationResponse,
    summary="Revoke a University Admin (Super Admin)",
)
async def revoke_platform_institution_admin(
    institution_id: UUID,
    user_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> AdminRevocationResponse:
    """Remove one institution-scoped ``admin`` grant.

    Only the exact (admin, institution, this institution) tuple is deleted, so a
    Super Admin grant, another institution's admin grant and any unrelated role
    are all preserved, as is the Auth account itself. Audited as
    ``institution_admin_revoked``.
    """
    return invitations_service.revoke_admin(current_user, institution_id, user_id)


@router.get(
    "/audit",
    response_model=PlatformAuditListResponse,
    summary="Read the platform audit ledger (Super Admin, read-only)",
)
async def read_platform_audit(
    institution_id: UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> PlatformAuditListResponse:
    """Return one bounded page of platform audit records, newest first.

    Read-only by construction: there is no write, update or delete route for
    this ledger anywhere in the API. The optional filters are deliberately few —
    the platform audit volume is small and an over-engineered filter surface
    would be a disclosure risk rather than a feature.
    """
    return invitations_service.list_platform_audit(
        institution_id=institution_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

