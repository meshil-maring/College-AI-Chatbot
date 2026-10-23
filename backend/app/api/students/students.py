"""Student account profile, institution notices and published resources."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.security import authorize_permissions, get_current_user
from app.schemas.students.student_notices import StudentNoticeList
from app.schemas.students.student_profile import StudentProfile
from app.schemas.students.student_resources import StudentResourceList
from app.services.students import student_data
from app.services.students import student_notices as student_notices_service
from app.services.students import student_resources as student_resources_service

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me/profile", response_model=StudentProfile)
def my_profile(current_user: dict = Depends(get_current_user)) -> StudentProfile:
    authorize_permissions(current_user, "profile.own.read")
    return student_data.get_own_profile(
        UUID(current_user["user_id"]), current_user=current_user
    )


@router.get(
    "/me/notices",
    response_model=StudentNoticeList,
)
def my_notices(
    limit: int = Query(
        student_notices_service.DEFAULT_NOTICE_LIMIT,
        ge=1,
        le=student_notices_service.MAX_NOTICE_LIMIT,
        description="Maximum number of notices to return",
    ),
    current_user: dict = Depends(get_current_user),
) -> StudentNoticeList:
    """Return published notices for the authenticated student's institution.

    Server-side scope: the student's OWN institution only (resolved from the
    JWT chain), published + active + unexpired rows only, pinned first then
    newest. An institution with no published notices returns an empty list.
    """
    notices = student_notices_service.get_own_notices(current_user, limit=limit)
    authorize_permissions(current_user, "notices.read")
    return notices


@router.get(
    "/me/resources",
    response_model=StudentResourceList,
)
def my_resources(
    limit: int = Query(
        student_resources_service.DEFAULT_RESOURCE_LIMIT,
        ge=1,
        le=student_resources_service.MAX_RESOURCE_LIMIT,
        description="Maximum number of learning resources to return",
    ),
    current_user: dict = Depends(get_current_user),
) -> StudentResourceList:
    """Return published learning resources for the student's institution.

    Server-side scope: the student's OWN institution only, ``published``
    knowledge sources only, newest first. Storage keys, storage buckets,
    document/version identifiers and internal database identifiers are never
    projected. An institution with no published resources returns an empty
    list.
    """
    resources = student_resources_service.get_own_resources(current_user, limit=limit)
    authorize_permissions(current_user, "documents.read")
    return resources
