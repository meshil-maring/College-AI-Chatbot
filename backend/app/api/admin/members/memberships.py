"""Admin memberships endpoints: requests, roster, role, department, status, invitations."""

from uuid import UUID

from fastapi import Depends, Request

from app.schemas.invitations.admin_invitations import AdminInvitationResendResponse
from app.schemas.admin.admin_memberships import (
    MemberDepartmentResult,
    MemberDepartmentWrite,
    MemberRoleResult,
    MemberRoleWrite,
    MembershipDecisionBody,
    MembershipDecisionResult,
    MembershipLifecycleResult,
    MembershipRequestList,
    MembershipRoster,
)
from app.schemas.admin.member_invitations import (
    MemberInvitationCancelled,
    MemberInvitationCreate,
    MemberInvitationCreated,
    MemberInvitationList,
)
from app.services.admin import (
    admin_memberships,
    member_departments,
    member_invitations,
    member_profiles,
    member_roles,
    member_status,
)
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
    # The administrator chooses the new member's department while approving.
    return member_departments.approve_request(
        current_user,
        common.required_institution(current_user),
        request_id,
        department_id=body.department_id if body else None,
        reason=body.reason if body else None,
        role=body.role if body else None,
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
    institution_id = common.required_institution(current_user)
    roster = admin_memberships.list_roster(institution_id, role=role, status=status)
    roster = member_departments.with_departments(institution_id, roster)
    return member_profiles.with_profiles(institution_id, roster)


@router.put(
    "/memberships/{user_id}/role",
    response_model=MemberRoleResult,
)
def set_member_role(
    user_id: UUID,
    body: MemberRoleWrite,
    current_user: dict = Depends(_ADMIN),
) -> MemberRoleResult:
    return member_roles.change_role(
        current_user, common.required_institution(current_user), user_id, body.role
    )


@router.put(
    "/memberships/{user_id}/department",
    response_model=MemberDepartmentResult,
)
def set_member_department(
    user_id: UUID,
    body: MemberDepartmentWrite,
    current_user: dict = Depends(_ADMIN),
) -> MemberDepartmentResult:
    return member_departments.assign(
        current_user, common.required_institution(current_user), user_id, body.department_id
    )


@router.post(
    "/memberships/{user_id}/deactivate",
    response_model=MembershipLifecycleResult,
)
def deactivate_membership(
    user_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MembershipLifecycleResult:
    return member_status.set_status(
        current_user, common.required_institution(current_user), user_id, "deactivated"
    )


@router.post(
    "/memberships/{user_id}/reactivate",
    response_model=MembershipLifecycleResult,
)
def reactivate_membership(
    user_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MembershipLifecycleResult:
    return member_status.set_status(
        current_user, common.required_institution(current_user), user_id, "active"
    )


@router.post(
    "/memberships/{user_id}/suspend",
    response_model=MembershipLifecycleResult,
)
def suspend_membership(
    user_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MembershipLifecycleResult:
    # Pauses access until reactivated; the account and its records are kept.
    return member_status.set_status(
        current_user, common.required_institution(current_user), user_id, "suspended"
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
    return member_invitations.resend(
        current_user, common.required_institution(current_user), invitation_id, peer
    )


# Staff and Faculty invited by the administrator. The institution is always the
# administrator's own; role, department and name come from the body.
@router.get("/memberships/invitations", response_model=MemberInvitationList)
def list_membership_invitations(current_user: dict = Depends(_ADMIN)) -> MemberInvitationList:
    return member_invitations.list_pending(common.required_institution(current_user))


@router.post("/memberships/invitations", response_model=MemberInvitationCreated, status_code=201)
def create_membership_invitation(
    body: MemberInvitationCreate,
    current_user: dict = Depends(_ADMIN),
) -> MemberInvitationCreated:
    return member_invitations.create(current_user, common.required_institution(current_user), body)


@router.post(
    "/memberships/invitations/{invitation_id}/cancel",
    response_model=MemberInvitationCancelled,
)
def cancel_membership_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MemberInvitationCancelled:
    return member_invitations.cancel(
        current_user, common.required_institution(current_user), invitation_id
    )
