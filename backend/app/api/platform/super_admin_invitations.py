"""Platform super admin invitations."""

from uuid import UUID
from fastapi import Depends, status
from app.schemas.invitations.super_admin_registration import (
    SuperAdminInvitationListResponse,
    SuperAdminInvitationView,
    SuperAdminInviteCreatedResponse,
    SuperAdminInviteRequest,
)
from app.services.invitations import super_admin_registration as super_admin_service
from fastapi import APIRouter
from app.api.platform.dependencies import _SUPER_ADMIN

router = APIRouter(prefix="/platform")


@router.post(
    "/super-admins/invitations",
    response_model=SuperAdminInviteCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite another Super Admin (Super Admin)",
)
async def create_super_admin_invitation(
    body: SuperAdminInviteRequest,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> SuperAdminInviteCreatedResponse:
    """Issue a single-use, expiring Super Admin registration link."""
    return super_admin_service.create_invitation(current_user, body.email)


@router.get(
    "/super-admins/invitations",
    response_model=SuperAdminInvitationListResponse,
    summary="List Super Admin invitations (Super Admin)",
)
async def list_super_admin_invitations(
    current_user: dict = Depends(_SUPER_ADMIN),
) -> SuperAdminInvitationListResponse:
    return super_admin_service.list_invitations()


@router.post(
    "/super-admins/invitations/{invitation_id}/cancel",
    response_model=SuperAdminInvitationView,
    summary="Cancel a pending Super Admin invitation (Super Admin)",
)
async def cancel_super_admin_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> SuperAdminInvitationView:
    return super_admin_service.cancel_invitation(current_user, str(invitation_id))
