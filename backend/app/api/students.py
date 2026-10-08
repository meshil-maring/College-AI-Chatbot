"""Student self-service API (Phase Admin-3).

All "me" endpoints authenticate with the existing ``get_current_user``
dependency. The student identity is resolved server-side from the
authenticated JWT (users.id → students.user_id); the client can never
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

from app.core.security import (
    assert_tenant_object,
    authorize_permissions,
    get_current_user,
)
from app.schemas.student_academic_experience import (
    StudentAcademicTimeline,
    StudentSubjectAttendance,
    StudentSubjectPerformanceList,
    StudentUpcomingAssessments,
)
from app.schemas.student_attendance import StudentOwnAttendance
from app.schemas.student_notices import StudentNoticeList
from app.schemas.student_profile import StudentAcademicProfile
from app.schemas.student_resources import StudentResourceList
from app.schemas.student_results import (
    StudentAcademicResultDetail,
    StudentOwnResults,
    StudentOwnTestResults,
)
from app.services import student_academic_experience as academic_experience_service
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
    authorize_permissions(current_user, "profile.own.read")
    return student


@router.get(
    "/me/academic-profile",
    response_model=StudentAcademicProfile,
)
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
    profile = academic_profile_service.get_academic_profile(current_user)
    authorize_permissions(current_user, "profile.own.read")
    return profile


@router.get("/me/results")
def my_results(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own published result summaries."""
    results = student_data.get_own_results(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )
    authorize_permissions(current_user, "results.own.read")
    return results


@router.get(
    "/me/results/summary",
    response_model=StudentOwnResults,
)
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
    results = student_results_service.get_own_results(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )
    authorize_permissions(current_user, "results.own.read")
    return results


@router.get(
    "/me/results/{result_id}/detail",
    response_model=StudentAcademicResultDetail,
)
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
    result = student_results_service.get_own_result(current_user, result_id)
    authorize_permissions(current_user, "results.own.read")
    return result


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
    authorize_permissions(current_user, "results.own.read")
    return result


@router.get(
    "/me/test-results/summary",
    response_model=StudentOwnTestResults,
)
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
    results = student_results_service.get_own_test_results(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )
    authorize_permissions(current_user, "results.own.read")
    return results


@router.get("/me/test-results")
def my_test_results(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own published test scores."""
    results = student_data.get_own_test_results(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )
    authorize_permissions(current_user, "results.own.read")
    return results


@router.get(
    "/me/attendance/summary",
    response_model=StudentOwnAttendance,
)
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
    attendance = student_attendance_service.get_own_attendance(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
    )
    authorize_permissions(current_user, "attendance.own.read")
    return attendance


@router.get("/me/attendance")
def my_attendance(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own attendance records."""
    attendance = student_data.get_own_attendance(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
    )
    authorize_permissions(current_user, "attendance.own.read")
    return attendance


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


# ============================================================================
# Student Academic Experience & Performance — read-only aggregations
# ============================================================================
# This block is a READ LAYER over the EXISTING authoritative systems: the
# Faculty Attendance records/sessions (aggregated with the same statistics()
# helper and the same MONITORING_THRESHOLD the faculty surface uses), the
# Faculty Tests lifecycle (DRAFT/CANCELLED never student-visible) and the
# existing publication-filtered result services. No new storage, no write
# path, no AI summarization.
#
# Identity: every endpoint accepts the authenticated ``current_user`` dict
# ONLY. Identity and tenant are resolved server-side by
# ``student_context.get_student_context`` (JWT -> users.id -> students row,
# eligibility: approved + active + institution active) plus the
# ``assert_student_context_tenant`` defence-in-depth check. The optional
# ``subject`` query field is a course-code NARROWING key applied after the
# server-side scope is fixed; it is never an identity selector, and a
# client-supplied ``student_id`` / ``user_id`` / ``register_number`` /
# ``institution_id`` query value is not part of any contract here (extra
# query fields are simply ignored and can never widen the scope).


_SUBJECT_QUERY = Query(
    None,
    max_length=64,
    description="Optional course code/name narrowing key (own records only)",
)


@router.get(
    "/me/attendance/subjects",
    response_model=StudentSubjectAttendance,
)
def my_subject_attendance(
    subject: str | None = _SUBJECT_QUERY,
    current_user: dict = Depends(get_current_user),
) -> StudentSubjectAttendance:
    """Return the authenticated student's subject-wise attendance.

    Data source: the Faculty Attendance system's own sessions/records for the
    student's linked rosters (merged with the legacy mirror exactly like the
    faculty reporting surface), aggregated by the shared ``statistics()``
    helper. ``monitoring_threshold`` is the existing project-wide value — no
    new policy is introduced. Students with no recorded sessions receive
    ``records_available=false`` rather than fabricated zeros.
    """
    attendance = academic_experience_service.get_subject_attendance(
        current_user, subject=subject
    )
    authorize_permissions(current_user, "attendance.own.read")
    return attendance


@router.get(
    "/me/assessments/upcoming",
    response_model=StudentUpcomingAssessments,
)
def my_upcoming_assessments(
    subject: str | None = _SUBJECT_QUERY,
    limit: int = Query(
        academic_experience_service.DEFAULT_UPCOMING_LIMIT,
        ge=1,
        le=academic_experience_service.MAX_UPCOMING_LIMIT,
        description="Maximum number of assessments to return",
    ),
    current_user: dict = Depends(get_current_user),
) -> StudentUpcomingAssessments:
    """Return the authenticated student's upcoming assessments.

    Visibility follows the existing ``faculty_tests`` lifecycle: only
    ``SCHEDULED`` (dated today or later) and ``ONGOING`` rows for the
    student's own sections are returned. Draft, cancelled, unpublished marks,
    teacher remarks, descriptions and actor metadata are never exposed.
    """
    assessments = academic_experience_service.get_upcoming_assessments(
        current_user, subject=subject, limit=limit
    )
    authorize_permissions(current_user, "results.own.read")
    return assessments


@router.get(
    "/me/performance/subjects",
    response_model=StudentSubjectPerformanceList,
)
def my_subject_performance(
    subject: str | None = _SUBJECT_QUERY,
    current_user: dict = Depends(get_current_user),
) -> StudentSubjectPerformanceList:
    """Return the authenticated student's subject performance summary.

    Attendance figures reuse the subject-wise aggregation above; score figures
    come from the existing publication-filtered test-result service (own
    PUBLISHED rows only). Averages are computed only when at least one
    published score exists for the subject — otherwise the field is ``null``
    and ``results_available=false``; no GPA/grade is invented.
    """
    performance = academic_experience_service.get_subject_performance(
        current_user, subject=subject
    )
    authorize_permissions(
        current_user, "attendance.own.read", "results.own.read"
    )
    return performance


@router.get("/me/timeline", response_model=StudentAcademicTimeline)
def my_academic_timeline(
    limit: int = Query(
        academic_experience_service.DEFAULT_TIMELINE_LIMIT,
        ge=1,
        le=academic_experience_service.MAX_TIMELINE_LIMIT,
        description="Maximum number of timeline events to return",
    ),
    current_user: dict = Depends(get_current_user),
) -> StudentAcademicTimeline:
    """Return a timeline derived from the student's own authorized records.

    Events are derived deterministically from existing rows only:
    upcoming assessments, published test scores (conducted date) and
    published academic results (issued date). No timeline table exists, no
    event is fabricated, and no internal identifiers, teacher remarks or
    audit metadata are included.
    """
    timeline = academic_experience_service.get_academic_timeline(
        current_user, limit=limit
    )
    authorize_permissions(current_user, "results.own.read")
    return timeline
