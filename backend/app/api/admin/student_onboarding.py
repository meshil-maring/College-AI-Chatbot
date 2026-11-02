"""Institution-admin student invitations and bulk onboarding."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query

from app.api.admin.dependencies import _ADMIN, create_feature_router
from app.schemas.invitations.student_onboarding import (
    StudentIdentityReviewRequest,
    StudentIdentityReviewResponse,
    StudentInvitationBulkRequest,
    StudentInvitationBulkResponse,
    StudentInvitationCancelResponse,
    StudentInvitationCreatedResponse,
    StudentInvitationCreateRequest,
    StudentInvitationListResponse,
    StudentInvitationReassignRequest,
    StudentInvitationView,
)
from app.schemas.invitations.student_onboarding_management import (
    StudentInvitationUpdateRequest,
    StudentInvitationUpdateResponse,
)
from app.schemas.students.student_directory import (
    StudentDirectoryFilter,
    StudentDirectoryResponse,
    StudentActiveResponse,
    StudentDeletionResponse,
    StudentProfileMutationResponse,
    StudentProfileUpdateRequest,
)
from app.services.invitations import student_onboarding
from app.services.invitations import student_onboarding_management
from app.services.students import student_management
from app.services.students import student_directory

router = create_feature_router()


@router.get(
    "/students/directory",
    response_model=StudentDirectoryResponse,
)
def list_student_directory(
    current_user: Annotated[dict, Depends(_ADMIN)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    status: Annotated[StudentDirectoryFilter | None, Query()] = None,
    program_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> StudentDirectoryResponse:
    return student_directory.list_directory(
        current_user,
        search=search,
        status=status,
        program_id=program_id,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/students/{student_id}",
    response_model=StudentProfileMutationResponse,
)
def update_student_profile(
    student_id: UUID,
    body: StudentProfileUpdateRequest,
    current_user: Annotated[dict, Depends(_ADMIN)],
) -> StudentProfileMutationResponse:
    result = student_management.update_profile(
        current_user, student_id, body.model_dump(mode="json")
    )
    return StudentProfileMutationResponse.model_validate(result)


@router.post(
    "/students/{student_id}/deactivate",
    response_model=StudentActiveResponse,
)
def deactivate_student(
    student_id: UUID,
    current_user: Annotated[dict, Depends(_ADMIN)],
) -> StudentActiveResponse:
    return student_management.set_active(current_user, student_id, False)


@router.post(
    "/students/{student_id}/reactivate",
    response_model=StudentActiveResponse,
)
def reactivate_student(
    student_id: UUID,
    current_user: Annotated[dict, Depends(_ADMIN)],
) -> StudentActiveResponse:
    return student_management.set_active(current_user, student_id, True)


@router.delete(
    "/students/{student_id}",
    response_model=StudentDeletionResponse,
)
def delete_student_profile(
    student_id: UUID,
    current_user: Annotated[dict, Depends(_ADMIN)],
) -> StudentDeletionResponse:
    return student_management.delete_profile(current_user, student_id)


@router.get(
    "/students/onboarding-invitations",
    response_model=StudentInvitationListResponse,
)
def list_student_invitations(
    current_user: dict = Depends(_ADMIN),
) -> StudentInvitationListResponse:
    return student_onboarding.list_pending(current_user)


@router.post(
    "/students/onboarding-invitations",
    response_model=StudentInvitationCreatedResponse,
    status_code=201,
)
def create_student_invitation(
    body: StudentInvitationCreateRequest,
    current_user: dict = Depends(_ADMIN),
) -> StudentInvitationCreatedResponse:
    return student_onboarding.create_invitation(current_user, body)


@router.post(
    "/students/onboarding-invitations/review",
    response_model=StudentIdentityReviewResponse,
)
def review_student_identity(
    body: StudentIdentityReviewRequest,
    current_user: dict = Depends(_ADMIN),
) -> StudentIdentityReviewResponse:
    return student_onboarding.review_identity(current_user, body)


@router.post(
    "/students/onboarding-invitations/bulk",
    response_model=StudentInvitationBulkResponse,
)
def create_student_invitations_bulk(
    body: StudentInvitationBulkRequest,
    current_user: dict = Depends(_ADMIN),
) -> StudentInvitationBulkResponse:
    return student_onboarding.create_bulk(current_user, body)


@router.patch(
    "/students/onboarding-invitations/{invitation_id}/section",
    response_model=StudentInvitationView,
)
def reassign_student_invitation_section(
    invitation_id: UUID,
    body: StudentInvitationReassignRequest,
    current_user: dict = Depends(_ADMIN),
) -> StudentInvitationView:
    return student_onboarding.reassign(
        current_user, invitation_id, body.academic_section_id
    )


@router.patch(
    "/students/onboarding-invitations/{invitation_id}",
    response_model=StudentInvitationUpdateResponse,
)
def update_student_invitation(
    invitation_id: UUID,
    body: StudentInvitationUpdateRequest,
    current_user: dict = Depends(_ADMIN),
) -> StudentInvitationUpdateResponse:
    return student_onboarding_management.update(
        current_user, invitation_id, body.model_dump(mode="json")
    )


@router.delete(
    "/students/onboarding-invitations/{invitation_id}",
    response_model=StudentInvitationCancelResponse,
)
def cancel_student_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> StudentInvitationCancelResponse:
    return student_onboarding_management.cancel(current_user, invitation_id)


@router.post(
    "/students/onboarding-invitations/{invitation_id}/resend",
    response_model=StudentInvitationCreatedResponse,
)
def resend_student_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> StudentInvitationCreatedResponse:
    return student_onboarding.resend(current_user, invitation_id)
