"""Admin memberships endpoints."""

from uuid import UUID

from fastapi import Depends, Request

from app.schemas.invitations.admin_invitations import AdminInvitationResendResponse
from app.schemas.admin.admin_memberships import (
    MembershipDecisionBody,
    MembershipDecisionResult,
    MembershipLifecycleResult,
    MembershipRequestList,
    MembershipRoster,
)
from app.services.admin import admin_memberships
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/memberships/requests", response_model=MembershipRequestList)
def list_membership_requests(
    role: str | None = None,
    status: str | None = None,
    current_user: dict = Depends(_ADMIN),
) -> MembershipRequestList:
    return admin_memberships.list_requests(
        common.required_institution(current_user), role=role, status=status
    )


@router.post(
    "/memberships/requests/{request_id}/approve",
    response_model=MembershipDecisionResult,
)
def approve_membership_request(
    request_id: UUID,
    body: MembershipDecisionBody | None = None,
    current_user: dict = Depends(_ADMIN),
) -> MembershipDecisionResult:
    return admin_memberships.decide_request(
        current_user,
        common.required_institution(current_user),
        request_id,
        approve=True,
        reason=body.reason if body else None,
    )


@router.post(
    "/memberships/requests/{request_id}/reject",
    response_model=MembershipDecisionResult,
)
def reject_membership_request(
    request_id: UUID,
    body: MembershipDecisionBody | None = None,
    current_user: dict = Depends(_ADMIN),
) -> MembershipDecisionResult:
    return admin_memberships.decide_request(
        current_user,
        common.required_institution(current_user),
        request_id,
        approve=False,
        reason=body.reason if body else None,
    )


@router.get("/memberships", response_model=MembershipRoster)
def list_membership_roster(
    role: str | None = None,
    status: str | None = None,
    current_user: dict = Depends(_ADMIN),
) -> MembershipRoster:
    return admin_memberships.list_roster(
        common.required_institution(current_user), role=role, status=status
    )


@router.post(
    "/memberships/{user_id}/deactivate",
    response_model=MembershipLifecycleResult,
)
def deactivate_membership(
    user_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MembershipLifecycleResult:
    return admin_memberships.set_active(
        current_user, common.required_institution(current_user), user_id, active=False
    )


@router.post(
    "/memberships/{user_id}/reactivate",
    response_model=MembershipLifecycleResult,
)
def reactivate_membership(
    user_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MembershipLifecycleResult:
    return admin_memberships.set_active(
        current_user, common.required_institution(current_user), user_id, active=True
    )


@router.post(
    "/memberships/invitations/{invitation_id}/resend",
    response_model=AdminInvitationResendResponse,
)
def resend_membership_invitation(
    invitation_id: UUID,
    request: Request,
    current_user: dict = Depends(_ADMIN),
) -> AdminInvitationResendResponse:
    peer = request.client.host if request.client else "unknown"
    return admin_memberships.resend(
        current_user, common.required_institution(current_user), invitation_id, peer
    )
