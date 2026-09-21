"""Student self-service API (Phase Admin-3).

All "me" endpoints authenticate with the existing ``get_current_user``
dependency. The student identity is resolved server-side from the
authenticated JWT (users.user_id → students.user_id); the client can never
supply another student's id.

Tenant isolation: the authenticated user's tenant (institution_id, resolved
from their students profile) must match the tenant of the student profile
whose data is returned — defence-in-depth against a stale/moved profile.

Phase 6.16 adds two read-only endpoints that close the student experience
dashboard's data gaps (``/me/notices`` and ``/me/resources``). Both reuse the
same server-side identity/tenant resolution as every endpoint above and expose
no mutation path.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.security import assert_tenant_object, get_current_user
from app.schemas.student_attendance import StudentOwnAttendance
from app.schemas.student_notices import StudentNoticeList
from app.schemas.student_profile import StudentAcademicProfile
from app.schemas.student_resources import StudentResourceList
from app.schemas.student_results import (
    StudentAcademicResultDetail,
    StudentOwnResults,
    StudentOwnTestResults,
)
from app.services import student_academic_profile as academic_profile_service
from app.services import student_attendance as student_attendance_service
from app.services import student_data
from app.services import student_notices as student_notices_service
from app.services import student_resources as student_resources_service
from app.services import student_results as student_results_service

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me/profile")
def my_profile(current_user: dict = Depends(get_current_user)) -> dict:
    """Return the authenticated student's own profile."""
    student = student_data.get_own_profile(UUID(current_user["user_id"]))
    assert_tenant_object(current_user, student.get("institution_id"))
    return student


@router.get("/me/academic-profile", response_model=StudentAcademicProfile)
def my_academic_profile(
    current_user: dict = Depends(get_current_user),
) -> StudentAcademicProfile:
    """Return the authenticated student's reusable academic profile.

    Phase 6.14.1: student-facing projection (no internal database
    identifiers). Identity and tenant are resolved server-side from the
    authenticated JWT via ``get_current_user``; the endpoint accepts NO
    identity parameters, so client-supplied ``student_id`` / ``user_id`` /
    ``institution_id`` / email / register-number / roll-number values can
    never override the authenticated identity (extra query/body fields are
    rejected with 422).
    """
    return academic_profile_service.get_academic_profile(current_user)


@router.get("/me/results")
def my_results(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own published result summaries."""
    return student_data.get_own_results(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )


@router.get("/me/results/summary", response_model=StudentOwnResults)
def my_results_summary(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
) -> StudentOwnResults:
    """Return the authenticated student's own published results (safe view).

    Phase 6.14.3: student-safe projection (no internal database
    identifiers). Identity and tenant are resolved server-side from the
    authenticated JWT; only non-identity filters already supported by the
    existing schema (academic_year_id / semester_id) narrow the caller's
    own rows. The legacy raw ``GET /me/results`` contract is unchanged.
    """
    return student_results_service.get_own_results(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )


@router.get("/me/results/{result_id}/detail",
    response_model=StudentAcademicResultDetail)
def my_result_detail(
    result_id: UUID,
    current_user: dict = Depends(get_current_user),
) -> StudentAcademicResultDetail:
    """Return ONE own published result with subject rows (safe view).

    Phase 6.14.3: ownership + published status + tenant are enforced in
    the service; foreign/unpublished/missing rows yield 404
    RESULT_NOT_FOUND. The legacy raw ``GET /me/results/{result_id}``
    contract is unchanged.
    """
    return student_results_service.get_own_result(current_user, result_id)


@router.get("/me/results/{result_id}")
def my_result(
    result_id: UUID,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return ONE of the authenticated student's own published result
    summaries with its per-course grade rows (Phase 6.8).

    Identity is resolved server-side from the JWT; a missing, foreign, or
    unpublished result always yields the same 404 RESULT_NOT_FOUND so the
    endpoint cannot be used to enumerate other students' results.
    """
    result = student_data.get_own_result(UUID(current_user["user_id"]), result_id)
    assert_tenant_object(current_user, result.get("institution_id"))
    return result


@router.get("/me/test-results/summary", response_model=StudentOwnTestResults)
def my_test_results_summary(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
) -> StudentOwnTestResults:
    """Return the authenticated student's own published test scores (safe).

    Phase 6.14.3: student-safe projection (no internal database
    identifiers). Identity and tenant are resolved server-side from the
    authenticated JWT; only non-identity filters already supported by the
    existing schema (academic_year_id / semester_id) narrow the caller's
    own rows. The legacy raw ``GET /me/test-results`` contract is unchanged.
    """
    return student_results_service.get_own_test_results(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )


@router.get("/me/test-results")
def my_test_results(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own published test scores."""
    return student_data.get_own_test_results(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )


@router.get("/me/attendance/summary", response_model=StudentOwnAttendance)
def my_attendance_summary(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> StudentOwnAttendance:
    """Return the authenticated student's own attendance summary + records.

    Phase 6.14.2: reusable student-safe attendance data layer (no
    internal database identifiers). Identity and tenant are resolved
    server-side from the authenticated JWT via ``get_current_user``;
    the endpoint accepts NO identity parameters, so client-supplied
    ``student_id`` / ``user_id`` / ``institution_id`` / email /
    register-number / roll-number values can never override the
    authenticated identity (extra query fields are rejected with 422).
    Only non-identity filters already supported by the existing schema
    (academic_year_id / semester_id / date_from / date_to) narrow the
    caller's own rows.
    """
    return student_attendance_service.get_own_attendance(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/me/attendance")
def my_attendance(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own attendance records."""
    return student_data.get_own_attendance(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
    )


# ============================================================================
# Phase 6.16 — Student experience: notices and learning resources
# ============================================================================
# Both endpoints close the two dashboard data gaps found during the Phase 6.16
# audit: institution notices and institution learning resources previously had
# NO student-scoped read path (only /admin/* with require_roles("admin")).
#
# They follow the exact pattern already used by every other /students/me/*
# endpoint: identity and tenant come exclusively from the authenticated JWT via
# the server-resolved student context. There is no identity parameter on either
# endpoint, so a client-supplied ``institution_id`` / ``student_id`` query value
# is simply ignored and can never widen the scope.
#
# Both are strictly READ-ONLY: there is no student-facing create/update/publish
# /delete route for notices or resources.


@router.get("/me/notices", response_model=StudentNoticeList)
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
    return student_notices_service.get_own_notices(current_user, limit=limit)


@router.get("/me/resources", response_model=StudentResourceList)
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
    return student_resources_service.get_own_resources(current_user, limit=limit)
