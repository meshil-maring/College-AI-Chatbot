"""Class In-Charge and Subject Coordinator endpoints.

The institution is always the administrator's own. Head of Department
appointments use ``/admin/department-heads`` (student transfers feature).
"""

from uuid import UUID

from fastapi import Depends

from app.api.admin import common
from app.api.admin.dependencies import _ADMIN, create_feature_router
from app.schemas.admin.member_responsibilities import (
    MemberResponsibilityAssign,
    MemberResponsibilityList,
    MemberResponsibilityResult,
)
from app.services.admin import member_responsibilities

router = create_feature_router()


@router.get("/memberships/responsibilities", response_model=MemberResponsibilityList)
def list_member_responsibilities(current_user: dict = Depends(_ADMIN)) -> MemberResponsibilityList:
    return member_responsibilities.list_responsibilities(
        current_user, common.required_institution(current_user)
    )


@router.post("/memberships/responsibilities", response_model=MemberResponsibilityResult, status_code=201)
def assign_member_responsibility(
    body: MemberResponsibilityAssign,
    current_user: dict = Depends(_ADMIN),
) -> MemberResponsibilityResult:
    return member_responsibilities.assign(current_user, common.required_institution(current_user), body)


@router.post(
    "/memberships/responsibilities/{responsibility_id}/end",
    response_model=MemberResponsibilityResult,
)
def end_member_responsibility(
    responsibility_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MemberResponsibilityResult:
    return member_responsibilities.end(
        current_user, common.required_institution(current_user), responsibility_id
    )
