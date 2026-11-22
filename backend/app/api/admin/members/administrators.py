"""Institution administrator endpoints: list, Owner invitations, access, removal and ownership.

The institution is always the signed-in administrator's own. Any administrator
may read the list; the database lets only the Owner change it.
"""

from uuid import UUID

from fastapi import Depends, Request

from app.api.admin import common
from app.api.admin.dependencies import _ADMIN, create_feature_router
from app.schemas.admin.member_profiles import CommonProfile
from app.schemas.admin.institution_admins import (
    AdminAccessUpdate,
    AdminInvitationCreate,
    InstitutionAdminList,
    InstitutionAdminResult,
    OwnershipTransfer,
)
from app.services.admin import institution_admins

router = create_feature_router()


@router.get("/institution-admins", response_model=InstitutionAdminList)
def list_administrators(current_user: dict = Depends(_ADMIN)) -> InstitutionAdminList:
    return institution_admins.list_admins(current_user, common.required_institution(current_user))


@router.post("/institution-admins/invitations", response_model=InstitutionAdminResult, status_code=201)
def invite_administrator(
    body: AdminInvitationCreate, current_user: dict = Depends(_ADMIN),
) -> InstitutionAdminResult:
    return institution_admins.invite(current_user, common.required_institution(current_user), body)


@router.post("/institution-admins/invitations/{invitation_id}/cancel", response_model=InstitutionAdminResult)
def cancel_administrator_invitation(
    invitation_id: UUID, current_user: dict = Depends(_ADMIN),
) -> InstitutionAdminResult:
    return institution_admins.cancel_invitation(
        current_user, common.required_institution(current_user), invitation_id
    )


@router.post(
    "/institution-admins/invitations/{invitation_id}/resend", response_model=InstitutionAdminResult,
)
def resend_administrator_invitation(
    invitation_id: UUID, request: Request, current_user: dict = Depends(_ADMIN),
) -> InstitutionAdminResult:
    peer = request.client.host if request.client else "unknown"
    return institution_admins.resend_invitation(
        current_user, common.required_institution(current_user), invitation_id, peer
    )


@router.put("/institution-admins/{user_id}/profile", response_model=InstitutionAdminResult)
def save_administrator_profile(
    user_id: UUID, body: CommonProfile, current_user: dict = Depends(_ADMIN),
) -> InstitutionAdminResult:
    # The Owner edits anyone's profile; an administrator edits their own (checked in the database).
    return institution_admins.save_profile(current_user, common.required_institution(current_user), user_id, body)


@router.delete("/institution-admins/{user_id}", response_model=InstitutionAdminResult)
def revoke_administrator(user_id: UUID, current_user: dict = Depends(_ADMIN)) -> InstitutionAdminResult:
    return institution_admins.revoke(current_user, common.required_institution(current_user), user_id)


@router.put("/institution-admins/{user_id}/access", response_model=InstitutionAdminResult)
def set_administrator_access(
    user_id: UUID, body: AdminAccessUpdate, current_user: dict = Depends(_ADMIN),
) -> InstitutionAdminResult:
    return institution_admins.set_access(current_user, common.required_institution(current_user), user_id, body)


@router.put("/institution-admins/owner", response_model=InstitutionAdminResult)
def transfer_institution_ownership(
    body: OwnershipTransfer, current_user: dict = Depends(_ADMIN),
) -> InstitutionAdminResult:
    return institution_admins.transfer_ownership(
        current_user, common.required_institution(current_user), body.user_id
    )
