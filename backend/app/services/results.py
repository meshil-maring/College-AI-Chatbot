"""Phase 6.8 — Test / exam results service.

Business rules and tenant-safe orchestration over the EXISTING result tables
(``test_results`` per-test/per-exam scores and ``student_results`` per-semester
consolidated summaries, both created in Phase Admin-1) hardened by the Phase
6.8 migration.

Authorization is enforced by the API layer (authentication, role, tenant,
ownership — locked Phase 6.6 RBAC: admin-only mutation, staff/faculty denied).
This service validates the academic context and derives every security-relevant
value server-side — never from the client:

  * ``institution_id`` is server-derived from the STUDENT record (the payload
    carries no tenant field; the DB guard trigger re-derives it anyway);
  * the academic year must exist and belong to the student's institution
    (``academic_years.institution_id`` is NOT NULL — a strong tenant anchor);
  * the semester must belong to the academic year
    (``semesters.academic_year_id``);
  * the course (courses -> departments) and program (programs -> departments)
    must belong to the student's institution;
  * an attached section's offering (section -> course_offerings) must match
    the row's course / academic year / semester — no inconsistent context;
  * ``percentage`` is DERIVED from scored_marks / max_marks, never accepted
    from the client;
  * ``letter_grade`` is normalized (trimmed; blank -> NULL) — the project has
    no grading-scale table, so no scale is invented here;
  * ownership fields can never be reassigned (schema + DB guard trigger);
  * duplicate creation is rejected with stable 409 codes
    (TEST_RESULT_DUPLICATE / RESULT_DUPLICATE) backed by the Admin-1 UNIQUE
    constraints, so concurrent duplicates are safe at the database level.

The database guard triggers (``test_results_tenant_guard``,
``student_results_tenant_guard``) are the backstop for every invariant
enforced here.
"""

from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import attendance as attendance_repo
from app.repositories import results as results_repo
from app.services.admin_academics import (
    RESULT_STATUSES,
    RESULT_TYPES,
    TEST_RESULT_STATUSES,
    TEST_TYPES,
    ResultCreate,
    ResultUpdate,
    TestResultCreate,
    TestResultUpdate,
    _validate_choice,
)


# ============================================================================
# Validation helpers
# ============================================================================


def _normalize_letter_grade(value: str | None) -> str | None:
    """Trim a client-supplied letter grade; blank becomes NULL.

    The project has no grading-scale reference table, so the grade is stored
    as recorded (consistent with the existing Admin-1 schema) but never blank.
    """
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _derive_percentage(
    scored_marks: float | None, max_marks: float | None
) -> float | None:
    """Percentage is derived, never client-trusted (Phase 6.8 model rule).

    None when no score is recorded; otherwise scored / max * 100 rounded to 2
    decimals (matches the numeric(5,2) column and the Admin-1 seed data).
    """
    if scored_marks is None or max_marks is None:
        return None
    return round((float(scored_marks) / float(max_marks)) * 100, 2)


def _validate_scores(scored_marks: float | None, max_marks: float | None) -> None:
    """Strict score validation (422 INVALID_SCORES on any violation)."""
    if scored_marks is not None and scored_marks < 0:
        raise AppError(
            "scored_marks cannot be negative",
            status_code=422,
            code="INVALID_SCORES",
        )
    if max_marks is not None and max_marks <= 0:
        raise AppError(
            "max_marks must be positive",
            status_code=422,
            code="INVALID_SCORES",
        )
    if (
        scored_marks is not None
        and max_marks is not None
        and scored_marks > max_marks
    ):
        raise AppError(
            "scored_marks cannot exceed max_marks",
            status_code=422,
            code="INVALID_SCORES",
        )


def _test_result_duplicate_error(exc: Exception) -> AppError:
    """Map an insert/update failure to the most accurate business error.

    PostgREST surfaces the Postgres unique-violation SQLSTATE ``23505`` (or a
    ``duplicate key...`` message) for the Admin-1
    UNIQUE(student_id, course_id, test_name, academic_year_id, semester_id)
    constraint. Everything else (FK violations, guard-trigger rejections)
    stays a generic 409 so no underlying schema detail leaks.
    """
    message = str(exc).lower()
    if "23505" in message or "duplicate" in message:
        return AppError(
            "Test result already exists for this student, course, test, and term",
            status_code=409,
            code="TEST_RESULT_DUPLICATE",
        )
    return AppError(
        "Test result creation failed",
        status_code=409,
        code="TEST_RESULT_CREATE_FAILED",
    )


def _result_duplicate_error(exc: Exception) -> AppError:
    """Same mapping for the consolidated student_results unique rule
    UNIQUE(student_id, academic_year_id, semester_id, program_id)."""
    message = str(exc).lower()
    if "23505" in message or "duplicate" in message:
        return AppError(
            "Result already exists for this student, term, and program",
            status_code=409,
            code="RESULT_DUPLICATE",
        )
    return AppError(
        "Result creation failed",
        status_code=409,
        code="RESULT_CREATE_FAILED",
    )


# ============================================================================
# Academic-context validation (fail closed)
# ============================================================================


def _require_student(db, student_id: UUID | str) -> dict:
    """Resolve the student tenant anchor, or raise 404 (unknown student)."""
    student = results_repo.get_student_context(db, student_id)
    if student is None:
        raise AppError(
            "Student not found", status_code=404, code="STUDENT_NOT_FOUND"
        )
    return student


def _validate_academic_year(db, academic_year_id: UUID | str, student: dict) -> None:
    """The academic year must exist and belong to the student's institution."""
    year = results_repo.get_academic_year_context(db, academic_year_id)
    if year is None:
        raise AppError(
            "Academic year not found",
            status_code=404,
            code="ACADEMIC_CONTEXT_INVALID",
        )
    if year.get("institution_id") != student.get("institution_id"):
        raise AppError(
            "The academic year does not belong to the student's institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )


def _validate_semester(db, semester_id: UUID | str, academic_year_id: UUID | str) -> None:
    """The semester must exist and belong to the same academic year."""
    semester = results_repo.get_semester_context(db, semester_id)
    if semester is None:
        raise AppError(
            "Semester not found",
            status_code=404,
            code="ACADEMIC_CONTEXT_INVALID",
        )
    if semester.get("academic_year_id") != str(academic_year_id):
        raise AppError(
            "Academic context (academic_year_id/semester_id) mismatch",
            status_code=422,
            code="ACADEMIC_CONTEXT_MISMATCH",
        )


def _validate_course(db, course_id: UUID | str, institution_id) -> None:
    """The course must exist and belong to the student's institution."""
    course_institution = results_repo.get_course_institution(db, course_id)
    if course_institution is None:
        raise AppError(
            "Course not found (or its department chain is broken)",
            status_code=404,
            code="COURSE_NOT_FOUND",
        )
    if course_institution != institution_id:
        raise AppError(
            "The course does not belong to the student's institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )


def _validate_program(db, program_id: UUID | str, institution_id) -> None:
    """The program must exist and belong to the student's institution."""
    program_institution = results_repo.get_program_institution(db, program_id)
    if program_institution is None:
        raise AppError(
            "Program not found (or its department chain is broken)",
            status_code=404,
            code="PROGRAM_NOT_FOUND",
        )
    if program_institution != institution_id:
        raise AppError(
            "The program does not belong to the student's institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )


def _validate_section(
    db,
    section_id: UUID | str,
    *,
    course_id: UUID | str,
    academic_year_id: UUID | str,
    semester_id: UUID | str,
    institution_id,
) -> None:
    """The attached section must exist, belong to the student's institution,
    and its offering must describe the SAME course / year / semester."""
    context = attendance_repo.get_section_academic_context(db, section_id)
    if context is None:
        raise AppError(
            "Section not found (or its offering chain is broken)",
            status_code=404,
            code="SECTION_NOT_FOUND",
        )
    if context.get("institution_id") != institution_id:
        raise AppError(
            "The section does not belong to the student's institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )
    if (
        context.get("course_id") != str(course_id)
        or context.get("academic_year_id") != str(academic_year_id)
        or context.get("semester_id") != str(semester_id)
    ):
        raise AppError(
            "Academic context (academic_year_id/semester_id) does not match the section",
            status_code=422,
            code="ACADEMIC_CONTEXT_MISMATCH",
        )


# ============================================================================
# Test results (per-test / per-exam scores)
# ============================================================================


def get_test_result(test_result_id: UUID | str) -> dict:
    """Return one test result row, or raise 404 (tenant-guard entrypoint)."""
    db = get_admin_client()
    existing = results_repo.get_test_result_row(db, test_result_id)
    if existing is None:
        raise AppError(
            "Test result not found", status_code=404, code="TEST_RESULT_NOT_FOUND"
        )
    return existing


def list_test_results_for_student(
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List per-test scores for one student, newest conducted first."""
    db = get_admin_client()
    return results_repo.list_test_results(
        db,
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        limit=limit,
    )


def create_test_result(payload: TestResultCreate) -> dict:
    """Create one test result row with full academic-context validation."""
    _validate_choice(payload.test_type, TEST_TYPES, "test type")
    _validate_choice(payload.status, TEST_RESULT_STATUSES, "test result status")
    _validate_scores(payload.scored_marks, payload.max_marks)

    db = get_admin_client()
    student = _require_student(db, payload.student_id)
    institution_id = student.get("institution_id")

    # Academic context: fail closed on unknown or cross-tenant context.
    _validate_academic_year(db, payload.academic_year_id, student)
    _validate_semester(db, payload.semester_id, payload.academic_year_id)
    _validate_course(db, payload.course_id, institution_id)
    if payload.section_id is not None:
        _validate_section(
            db,
            payload.section_id,
            course_id=payload.course_id,
            academic_year_id=payload.academic_year_id,
            semester_id=payload.semester_id,
            institution_id=institution_id,
        )

    row = payload.model_dump(mode="json", exclude={"percentage"})
    # The tenant and percentage are server-derived — never client input.
    row["institution_id"] = institution_id
    row["letter_grade"] = _normalize_letter_grade(row.get("letter_grade"))
    row["percentage"] = _derive_percentage(payload.scored_marks, payload.max_marks)

    try:
        return results_repo.insert_test_result(db, row)
    except Exception as exc:
        raise _test_result_duplicate_error(exc) from exc


def update_test_result(test_result_id: UUID | str, payload: TestResultUpdate) -> dict:
    """Update the mutable fields of one test result row.

    Ownership fields (student_id, course_id, academic_year_id, semester_id,
    institution_id) are not present in TestResultUpdate — the schema rejects
    them, and the Phase 6.8 DB trigger refuses ownership reassignment even if
    a write bypasses this API. ``section_id`` may be corrected but the new
    section is revalidated against the row's course / year / semester.
    """
    db = get_admin_client()
    existing = results_repo.get_test_result_row(db, test_result_id)
    if existing is None:
        raise AppError(
            "Test result not found", status_code=404, code="TEST_RESULT_NOT_FOUND"
        )
    fields = payload.model_dump(mode="json", exclude_unset=True, exclude={"percentage"})
    if not fields:
        raise AppError(
            "Test result update payload is empty", status_code=422, code="EMPTY_UPDATE"
        )
    if "test_type" in fields:
        _validate_choice(fields["test_type"], TEST_TYPES, "test type")
    if "status" in fields:
        _validate_choice(fields["status"], TEST_RESULT_STATUSES, "test result status")

    scored_marks = fields.get("scored_marks", existing.get("scored_marks"))
    max_marks = fields.get("max_marks", existing.get("max_marks"))
    _validate_scores(scored_marks, max_marks)

    if "letter_grade" in fields:
        fields["letter_grade"] = _normalize_letter_grade(fields["letter_grade"])

    # Percentage is re-derived whenever a marks component changes.
    if "scored_marks" in fields or "max_marks" in fields:
        fields["percentage"] = _derive_percentage(scored_marks, max_marks)

    if fields.get("section_id") is not None and "section_id" in fields:
        _validate_section(
            db,
            fields["section_id"],
            course_id=existing["course_id"],
            academic_year_id=existing["academic_year_id"],
            semester_id=existing["semester_id"],
            institution_id=existing.get("institution_id"),
        )

    updated = results_repo.update_test_result_row(db, test_result_id, fields)
    return updated if updated is not None else existing


def delete_test_result(test_result_id: UUID | str) -> dict:
    """Hard-delete one test result row (Phase Admin-1 policy).

    The caller must have passed tenant authorization with the returned row in
    mind — the API layer asserts it before calling here.
    """
    db = get_admin_client()
    existing = results_repo.get_test_result_row(db, test_result_id)
    if existing is None:
        raise AppError(
            "Test result not found", status_code=404, code="TEST_RESULT_NOT_FOUND"
        )
    results_repo.delete_test_result_row(db, test_result_id)
    return existing


# ============================================================================
# Student results (consolidated per-semester summaries)
# ============================================================================


def get_result(result_id: UUID | str) -> dict:
    """Return one result summary row, or raise 404 (tenant-guard entrypoint)."""
    db = get_admin_client()
    existing = results_repo.get_student_result_row(db, result_id)
    if existing is None:
        raise AppError("Result not found", status_code=404, code="RESULT_NOT_FOUND")
    return existing


def list_results_for_student(
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
) -> list[dict]:
    """List result summaries for one student, newest issued first."""
    db = get_admin_client()
    return results_repo.list_student_results(
        db,
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )


def create_result(payload: ResultCreate) -> dict:
    """Create one result summary with items, with full academic-context
    validation of the student / year / semester / program pairing and of
    every per-course item."""
    _validate_choice(payload.result_type, RESULT_TYPES, "result type")
    _validate_choice(payload.status, RESULT_STATUSES, "result status")

    db = get_admin_client()
    student = _require_student(db, payload.student_id)
    institution_id = student.get("institution_id")

    # Academic context: fail closed on unknown or cross-tenant context.
    _validate_academic_year(db, payload.academic_year_id, student)
    _validate_semester(db, payload.semester_id, payload.academic_year_id)
    _validate_program(db, payload.program_id, institution_id)

    for item in payload.items:
        _validate_course(db, item.course_id, institution_id)
        if item.section_id is not None:
            _validate_section(
                db,
                item.section_id,
                course_id=item.course_id,
                academic_year_id=payload.academic_year_id,
                semester_id=payload.semester_id,
                institution_id=institution_id,
            )

    row = payload.model_dump(mode="json", exclude={"items"})
    # The tenant is server-derived from the student record — never client input.
    row["institution_id"] = institution_id

    try:
        created = results_repo.insert_student_result(db, row)
        if payload.items:
            item_rows = []
            for item in payload.items:
                item_row = item.model_dump(mode="json")
                item_row["letter_grade"] = _normalize_letter_grade(
                    item_row.get("letter_grade")
                )
                item_row["student_result_id"] = created["student_result_id"]
                item_rows.append(item_row)
            stored_items = results_repo.insert_student_result_items(db, item_rows)
            created["items"] = stored_items
        return created
    except AppError:
        raise
    except Exception as exc:
        raise _result_duplicate_error(exc) from exc


def update_result(result_id: UUID | str, payload: ResultUpdate) -> dict:
    """Update the mutable fields of one result summary row.

    Ownership fields (student_id, academic_year_id, semester_id, program_id,
    institution_id) are not present in ResultUpdate — the schema rejects
    them, and the Phase 6.8 DB trigger refuses ownership reassignment even if
    a write bypasses this API.
    """
    db = get_admin_client()
    existing = results_repo.get_student_result_row(db, result_id)
    if existing is None:
        raise AppError("Result not found", status_code=404, code="RESULT_NOT_FOUND")
    fields = payload.model_dump(mode="json", exclude_unset=True)
    if not fields:
        raise AppError(
            "Result update payload is empty", status_code=422, code="EMPTY_UPDATE"
        )
    if "result_type" in fields:
        _validate_choice(fields["result_type"], RESULT_TYPES, "result type")
    if "status" in fields:
        _validate_choice(fields["status"], RESULT_STATUSES, "result status")
    updated = results_repo.update_student_result_row(db, result_id, fields)
    return updated if updated is not None else existing


def delete_result(result_id: UUID | str) -> dict:
    """Hard-delete one result summary and its items (Phase Admin-1 policy).

    The caller must have passed tenant authorization with the returned row in
    mind — the API layer asserts it before calling here.
    """
    db = get_admin_client()
    existing = results_repo.get_student_result_with_items(db, result_id)
    if existing is None:
        raise AppError("Result not found", status_code=404, code="RESULT_NOT_FOUND")
    results_repo.delete_student_result(db, result_id)
    return existing