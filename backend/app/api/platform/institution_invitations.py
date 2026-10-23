"""Platform institution invitations."""

from uuid import UUID
from fastapi import Depends, Request, status
from app.schemas.invitations.admin_invitations import (
    AdminInvitationCancellationResponse,
    AdminInvitationCreateRequest,
    AdminInvitationCreatedResponse,
    AdminInvitationExpirySweepResult,
    AdminInvitationResendResponse,
    AdminRevocationResponse,
    AdminRosterResponse,
)
from app.services.invitations import platform_admin_invitations as invitations_service
from fastapi import APIRouter
from app.api.platform.dependencies import _SUPER_ADMIN

router = APIRouter(prefix="/platform")


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
