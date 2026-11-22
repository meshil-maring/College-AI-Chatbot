"""Staff/Faculty employee profile and additional department endpoints.

The institution is always the administrator's own. The database commands
re-check the administrator, the member's Staff/Faculty grant in that
institution and every department before writing and auditing.
"""

from uuid import UUID

from fastapi import Depends

from app.api.admin import common
from app.api.admin.dependencies import _ADMIN, create_feature_router
from app.schemas.admin.member_profiles import (
    MemberAdditionalDepartmentsResult,
    MemberAdditionalDepartmentsWrite,
    MemberHistory,
    MemberProfileSaved,
    MemberProfileView,
    MemberProfileWrite,
)
from app.services.admin import member_history, member_profiles

router = create_feature_router()


@router.get("/memberships/{user_id}/profile", response_model=MemberProfileView)
def get_member_profile(
    user_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MemberProfileView:
    return member_profiles.get_profile(common.required_institution(current_user), user_id)


@router.get("/memberships/{user_id}/history", response_model=MemberHistory)
def get_member_history(
    user_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> MemberHistory:
    # Audit entries about this person in the administrator's own institution.
    return member_history.history(common.required_institution(current_user), user_id)


@router.put("/memberships/{user_id}/profile", response_model=MemberProfileSaved)
def save_member_profile(
    user_id: UUID,
    body: MemberProfileWrite,
    current_user: dict = Depends(_ADMIN),
) -> MemberProfileSaved:
    return member_profiles.save_profile(
        current_user, common.required_institution(current_user), user_id, body
    )


@router.put(
    "/memberships/{user_id}/departments/additional",
    response_model=MemberAdditionalDepartmentsResult,
)
def set_member_additional_departments(
    user_id: UUID,
    body: MemberAdditionalDepartmentsWrite,
    current_user: dict = Depends(_ADMIN),
) -> MemberAdditionalDepartmentsResult:
    return member_profiles.set_additional_departments(
        current_user, common.required_institution(current_user), user_id, body
    )
