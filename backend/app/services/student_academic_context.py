"""Phase 6.14.4 — Student academic context resolver.

Single server-side aggregation layer that assembles the authenticated
student's safe academic context from the EXISTING student-facing services:

    JWT
     |
    current_user (get_current_user: users.user_id + server-resolved tenant)
     |
    Student Academic Context Resolver (this module)
     |-- Phase 6.14.1 profile service   (identity + institution labels)
     |-- Phase 6.14.2 attendance service (summary + safe records)
     |-- Phase 6.14.3 results services   (published academic + test results)
     |
    StudentAcademicContext

Security model (nothing weakened, nothing duplicated):

* Identity is derived EXCLUSIVELY from ``current_user`` (JWT ``user_id`` ->
  ``students.user_id`` inside the existing services). The resolver accepts NO
  identity parameters -- there is no ``student_id`` / ``user_id`` /
  ``institution_id`` / email / register-number / roll-number argument -- so a
  client-supplied identifier can never override the authenticated student.
* Every underlying service keeps its own authorization chain (JWT identity,
  tenant validation via ``assert_tenant_object``, own-student-only access,
  published-results-only). The resolver never queries the underlying tables
  directly and never catches or bypasses a service denial: if any service
  raises (400 INVALID_USER_CONTEXT / 404 STUDENT_PROFILE_NOT_FOUND / 403
  TENANT_MISMATCH / 422 INVALID_FILTER), the error propagates and no
  context is produced.
* Data minimization: only whitelisted, student-safe fields enter the context
  (see ``app.schemas.student_academic_context``). No internal database ids,
  no passwords/auth secrets, and no other student's data ever enter it.
* Empty academic data is NOT an authorization failure: students with no
  attendance and/or no results receive a valid context with empty
  collections/summaries (the existing services already guarantee this).
* Context size: bounded by reusing the existing service limits and filters --
  ``academic_year_id`` / ``semester_id`` / ``date_from`` / ``date_to`` are
  forwarded verbatim (validated by the existing services) and the existing
  ``limit`` parameters are reused. No LLM compression/summarization here.

This phase does NOT touch the generation pipeline, ``AIContext``, prompts,
retrieval, attendance, results, or authentication code.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.schemas.student_academic_context import (
    StudentAcademicContext,
    StudentAcademicIdentity,
    StudentAcademicInstitution,
    StudentContextResults,
)
from app.services import student_academic_profile as profile_service
from app.services import student_attendance as attendance_service
from app.services import student_results as results_service

DEFAULT_ATTENDANCE_LIMIT = 200
DEFAULT_TEST_RESULTS_LIMIT = 100


def get_student_academic_context(
    current_user: dict[str, Any],
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    client: Any | None = None,
    attendance_limit: int = DEFAULT_ATTENDANCE_LIMIT,
    test_results_limit: int = DEFAULT_TEST_RESULTS_LIMIT,
) -> StudentAcademicContext:
    """Assemble the authenticated student's safe academic context.

    Args:
        current_user: the dict returned by ``get_current_user()`` (JWT
            ``sub`` -> users row -> server-resolved tenant). ``user_id`` is
            the ONLY identity source; every underlying service re-resolves
            the student from it server-side.
        academic_year_id / semester_id / date_from / date_to: optional
            NON-identity academic filters, forwarded verbatim to the
            existing attendance/results services (which validate them and
            scope them to the caller's own rows).
        client: optional already-created Supabase client (tests inject a
            mock; production uses the service-role admin client).
        attendance_limit / test_results_limit: existing service limits
            (defaults mirror the services' own defaults) to bound context
            size.

    Returns:
        StudentAcademicContext -- student-safe model (``extra="forbid"``),
        with empty attendance/results when the student has none.

    Raises:
        AppError 400 INVALID_USER_CONTEXT: no user_id in the authenticated
            context (raised by the underlying services).
        AppError 404 STUDENT_PROFILE_NOT_FOUND: no students row for the user.
        AppError 403 TENANT_MISMATCH: the student row belongs to another
            institution (tenant isolation, fail-closed).
        AppError 422 INVALID_FILTER: malformed academic filter (existing
            validation, forwarded).
    """
    # Phase 6.14.1 service: resolves students.user_id from the JWT-derived
    # user_id and enforces the tenant boundary. Raises 404/403 -- never
    # bypassed, never caught here.
    profile = profile_service.get_academic_profile(current_user, client=client)

    # Phase 6.14.2 service: own attendance only (summary + safe records).
    attendance = attendance_service.get_own_attendance(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
        client=client,
        limit=attendance_limit,
    )

    # Phase 6.14.3 services: own PUBLISHED results only (both families).
    results = results_service.get_own_results(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        client=client,
    )
    test_results = results_service.get_own_test_results(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        client=client,
        limit=test_results_limit,
    )

    return StudentAcademicContext(
        student=StudentAcademicIdentity(
            # No verified name field exists in the students contract consumed
            # by the existing self-service layer; none is fabricated here.
            name=None,
            student_number=profile.student_number,
            register_number=profile.register_number,
            university_roll_number=profile.university_roll_number,
        ),
        institution=StudentAcademicInstitution(
            institution_name=profile.institution_name,
            institution_code=profile.institution_code,
        ),
        attendance=attendance,
        results=StudentContextResults(
            summary=results.summary,
            records=results.records,
            test_summary=test_results.summary,
            test_records=test_results.records,
        ),
    )
