"""Admin academics service (Phase Admin-3).

Management operations over the student academic tables created in Phase
Admin-1 (students, student_results, student_result_items, test_results,
student_attendance), plus validated CSV result upload.

Read paths reuse the Phase Admin-2 repositories in
``app.repositories.admin_academics``; write paths use the service-role
Supabase client directly (the Admin-2 repositories are read-only by design).
Student academic data is never injected into the RAG pipeline.
"""

import csv
import io
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import admin_academics as academics_repo

# Enum values mirror the CHECK constraints in the Admin-1 migration.
STUDENT_STATUSES = ["active", "inactive", "graduated", "withdrawn"]
RESULT_TYPES = ["semester", "supplementary", "final", "provisional"]
RESULT_STATUSES = ["draft", "published", "withheld"]
TEST_TYPES = ["quiz", "assignment", "midterm", "final", "project", "internal", "external"]
TEST_RESULT_STATUSES = ["draft", "published", "withheld"]
ATTENDANCE_STATUSES = ["present", "absent", "late", "excused"]

RESULT_CSV_REQUIRED_COLUMNS = (
    "student_number",
    "academic_year_id",
    "semester_id",
    "program_id",
    "result_type",
)
RESULT_CSV_NUMERIC_COLUMNS = (
    "total_credits_earned",
    "total_credits_max",
    "sgpa",
    "cgpa",
)


# ============================================================================
# Contracts (new in Admin-3; existing Admin-2 schema files are untouched)
# ============================================================================


class StudentCreate(BaseModel):
    user_id: UUID
    institution_id: UUID
    student_number: str
    program_id: UUID | None = None
    academic_year_id: UUID | None = None
    enrollment_date: date
    expected_graduation_date: date | None = None
    status: str = "active"


class StudentUpdate(BaseModel):
    student_number: str | None = None
    program_id: UUID | None = None
    academic_year_id: UUID | None = None
    expected_graduation_date: date | None = None
    status: str | None = None
    is_active: bool | None = None


class ResultItemCreate(BaseModel):
    course_id: UUID
    section_id: UUID | None = None
    credits_earned: float | None = Field(default=None, ge=0)
    credits_max: float | None = Field(default=None, ge=0)
    grade_points: float | None = Field(default=None, ge=0)
    letter_grade: str | None = None
    grade_value: float | None = None
    status: str = "published"


class ResultCreate(BaseModel):
    student_id: UUID
    academic_year_id: UUID
    semester_id: UUID
    program_id: UUID
    result_type: str
    total_credits_earned: float | None = Field(default=None, ge=0)
    total_credits_max: float | None = Field(default=None, ge=0)
    sgpa: float | None = Field(default=None, ge=0, le=100)
    cgpa: float | None = Field(default=None, ge=0, le=100)
    status: str = "published"
    issued_at: datetime | None = None
    items: list[ResultItemCreate] = Field(default_factory=list)


class ResultUpdate(BaseModel):
    result_type: str | None = None
    total_credits_earned: float | None = Field(default=None, ge=0)
    total_credits_max: float | None = Field(default=None, ge=0)
    sgpa: float | None = Field(default=None, ge=0, le=100)
    cgpa: float | None = Field(default=None, ge=0, le=100)
    status: str | None = None
    issued_at: datetime | None = None


class TestResultCreate(BaseModel):
    student_id: UUID
    course_id: UUID
    section_id: UUID | None = None
    academic_year_id: UUID
    semester_id: UUID
    test_name: str
    test_type: str
    max_marks: float = Field(gt=0)
    scored_marks: float | None = Field(default=None, ge=0)
    percentage: float | None = Field(default=None, ge=0, le=100)
    letter_grade: str | None = None
    conducted_at: datetime | None = None
    status: str = "published"


class TestResultUpdate(BaseModel):
    section_id: UUID | None = None
    test_name: str | None = None
    test_type: str | None = None
    max_marks: float | None = Field(default=None, gt=0)
    scored_marks: float | None = Field(default=None, ge=0)
    percentage: float | None = Field(default=None, ge=0, le=100)
    letter_grade: str | None = None
    conducted_at: datetime | None = None
    status: str | None = None


class AttendanceCreate(BaseModel):
    student_id: UUID
    section_id: UUID
    academic_year_id: UUID
    semester_id: UUID
    date: date
    status: str
    notes: str | None = None


class AttendanceUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class CsvRowError(BaseModel):
    row: int
    student_number: str | None = None
    errors: list[str]


class CsvUploadResult(BaseModel):
    total_rows: int
    inserted_count: int
    failed_count: int
    row_errors: list[CsvRowError] = Field(default_factory=list)

# ============================================================================
# Validation helpers
# ============================================================================


def _validate_choice(value: str | None, allowed: list[str], field: str) -> str:
    if value not in allowed:
        code = "INVALID_" + field.upper().replace(" ", "_")
        raise AppError(
            f"Invalid {field}: must be one of {', '.join(allowed)}",
            status_code=422,
            code=code,
        )
    return value  # type: ignore[return-value]


# ============================================================================
# Students management
# ============================================================================


def list_students(
    institution_id: UUID | str,
    program_id: UUID | str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    db = get_admin_client()
    return academics_repo.list_students(
        db,
        institution_id,
        program_id=program_id,
        status=status,
        limit=limit,
        offset=offset,
    )


def get_student(student_id: UUID | str) -> dict:
    db = get_admin_client()
    student = academics_repo.get_student(db, student_id)
    if student is None:
        raise AppError("Student not found", status_code=404, code="STUDENT_NOT_FOUND")
    return student


def create_student(payload: StudentCreate) -> dict:
    db = get_admin_client()
    _validate_choice(payload.status, STUDENT_STATUSES, "student status")
    row = payload.model_dump(mode="json")
    try:
        response = db.table("students").insert(row).execute()
    except Exception as exc:
        raise AppError(
            "Student creation failed (student number or user may already be registered)",
            status_code=409,
            code="STUDENT_CREATE_FAILED",
        ) from exc
    return response.data[0]


def update_student(student_id: UUID | str, payload: StudentUpdate) -> dict:
    db = get_admin_client()
    existing = academics_repo.get_student(db, student_id)
    if existing is None:
        raise AppError("Student not found", status_code=404, code="STUDENT_NOT_FOUND")
    fields = payload.model_dump(mode="json", exclude_unset=True)
    if not fields:
        raise AppError(
            "Student update payload is empty",
            status_code=422,
            code="EMPTY_UPDATE",
        )
    if "status" in fields:
        _validate_choice(fields["status"], STUDENT_STATUSES, "student status")
    response = (
        db.table("students")
        .update(fields)
        .eq("student_id", str(student_id))
        .execute()
    )
    return response.data[0] if response.data else existing


def archive_student(student_id: UUID | str) -> dict:
    """Soft-delete a student: academic history is retained but access ends."""
    db = get_admin_client()
    existing = academics_repo.get_student(db, student_id)
    if existing is None:
        raise AppError("Student not found", status_code=404, code="STUDENT_NOT_FOUND")
    response = (
        db.table("students")
        .update({"status": "inactive", "is_active": False})
        .eq("student_id", str(student_id))
        .execute()
    )
    return response.data[0] if response.data else existing

# ============================================================================
# Results management
# ============================================================================


def list_results_for_student(
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
) -> list[dict]:
    db = get_admin_client()
    return academics_repo.list_student_results(
        db, student_id, academic_year_id=academic_year_id, semester_id=semester_id
    )


def get_result(result_id: UUID | str) -> dict:
    db = get_admin_client()
    result = academics_repo.get_student_result_with_items(db, result_id)
    if result is None:
        raise AppError("Result not found", status_code=404, code="RESULT_NOT_FOUND")
    return result


def create_result(payload: ResultCreate) -> dict:
    db = get_admin_client()
    _validate_choice(payload.result_type, RESULT_TYPES, "result type")
    _validate_choice(payload.status, RESULT_STATUSES, "result status")

    row = payload.model_dump(mode="json", exclude={"items"})
    try:
        response = db.table("student_results").insert(row).execute()
        created = response.data[0]
        if payload.items:
            item_rows = []
            for item in payload.items:
                item_row = item.model_dump(mode="json")
                item_row["student_result_id"] = created["student_result_id"]
                item_rows.append(item_row)
            db.table("student_result_items").insert(item_rows).execute()
            created["items"] = item_rows
        return created
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "Result creation failed (student/year/semester/program combination "
            "may already exist)",
            status_code=409,
            code="RESULT_CREATE_FAILED",
        ) from exc


def update_result(result_id: UUID | str, payload: ResultUpdate) -> dict:
    db = get_admin_client()
    existing = db.table("student_results").select("student_result_id").eq(
        "student_result_id", str(result_id)
    ).maybe_single().execute()
    if existing.data is None:
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
    response = (
        db.table("student_results")
        .update(fields)
        .eq("student_result_id", str(result_id))
        .execute()
    )
    return response.data[0] if response.data else fields


def delete_result(result_id: UUID | str) -> dict:
    db = get_admin_client()
    existing = academics_repo.get_student_result_with_items(db, result_id)
    if existing is None:
        raise AppError("Result not found", status_code=404, code="RESULT_NOT_FOUND")
    db.table("student_result_items").delete().eq(
        "student_result_id", str(result_id)
    ).execute()
    db.table("student_results").delete().eq(
        "student_result_id", str(result_id)
    ).execute()
    return existing

# ============================================================================
# Test results management
# ============================================================================


def _get_test_result(db, test_result_id: UUID | str) -> dict | None:
    response = (
        db.table("test_results")
        .select(academics_repo.TEST_RESULT_COLUMNS)
        .eq("test_result_id", str(test_result_id))
        .maybe_single()
        .execute()
    )
    return response.data


def list_test_results_for_student(
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    limit: int = 100,
) -> list[dict]:
    db = get_admin_client()
    return academics_repo.list_test_results(
        db,
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        limit=limit,
    )


def create_test_result(payload: TestResultCreate) -> dict:
    db = get_admin_client()
    _validate_choice(payload.test_type, TEST_TYPES, "test type")
    _validate_choice(payload.status, TEST_RESULT_STATUSES, "test result status")
    if (
        payload.scored_marks is not None
        and payload.max_marks is not None
        and payload.scored_marks > payload.max_marks
    ):
        raise AppError(
            "scored_marks cannot exceed max_marks",
            status_code=422,
            code="INVALID_SCORES",
        )
    row = payload.model_dump(mode="json")
    try:
        response = db.table("test_results").insert(row).execute()
    except Exception as exc:
        raise AppError(
            "Test result creation failed (duplicate test for student/course/term?)",
            status_code=409,
            code="TEST_RESULT_CREATE_FAILED",
        ) from exc
    return response.data[0]


def update_test_result(test_result_id: UUID | str, payload: TestResultUpdate) -> dict:
    db = get_admin_client()
    existing = _get_test_result(db, test_result_id)
    if existing is None:
        raise AppError("Test result not found", status_code=404, code="TEST_RESULT_NOT_FOUND")
    fields = payload.model_dump(mode="json", exclude_unset=True)
    if not fields:
        raise AppError(
            "Test result update payload is empty", status_code=422, code="EMPTY_UPDATE"
        )
    if "test_type" in fields:
        _validate_choice(fields["test_type"], TEST_TYPES, "test type")
    if "status" in fields:
        _validate_choice(fields["status"], TEST_RESULT_STATUSES, "test result status")
    max_marks = fields.get("max_marks", existing.get("max_marks"))
    scored_marks = fields.get("scored_marks", existing.get("scored_marks"))
    if (
        max_marks is not None
        and scored_marks is not None
        and float(scored_marks) > float(max_marks)
    ):
        raise AppError(
            "scored_marks cannot exceed max_marks",
            status_code=422,
            code="INVALID_SCORES",
        )
    response = (
        db.table("test_results")
        .update(fields)
        .eq("test_result_id", str(test_result_id))
        .execute()
    )
    return response.data[0] if response.data else existing


def delete_test_result(test_result_id: UUID | str) -> dict:
    db = get_admin_client()
    existing = _get_test_result(db, test_result_id)
    if existing is None:
        raise AppError("Test result not found", status_code=404, code="TEST_RESULT_NOT_FOUND")
    db.table("test_results").delete().eq(
        "test_result_id", str(test_result_id)
    ).execute()
    return existing

# ============================================================================
# Attendance management
# ============================================================================


def _get_attendance(db, attendance_id: UUID | str) -> dict | None:
    response = (
        db.table("student_attendance")
        .select(academics_repo.STUDENT_ATTENDANCE_COLUMNS)
        .eq("student_attendance_id", str(attendance_id))
        .maybe_single()
        .execute()
    )
    return response.data


def list_attendance_for_student(
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 200,
) -> list[dict]:
    db = get_admin_client()
    return academics_repo.list_student_attendance(
        db,
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


def create_attendance(payload: AttendanceCreate) -> dict:
    db = get_admin_client()
    _validate_choice(payload.status, ATTENDANCE_STATUSES, "attendance status")
    row = payload.model_dump(mode="json")
    try:
        response = db.table("student_attendance").insert(row).execute()
    except Exception as exc:
        raise AppError(
            "Attendance creation failed (a record for this student, section, "
            "and date may already exist)",
            status_code=409,
            code="ATTENDANCE_CREATE_FAILED",
        ) from exc
    return response.data[0]


def update_attendance(attendance_id: UUID | str, payload: AttendanceUpdate) -> dict:
    db = get_admin_client()
    existing = _get_attendance(db, attendance_id)
    if existing is None:
        raise AppError("Attendance record not found", status_code=404, code="ATTENDANCE_NOT_FOUND")
    fields = payload.model_dump(mode="json", exclude_unset=True)
    if not fields:
        raise AppError(
            "Attendance update payload is empty", status_code=422, code="EMPTY_UPDATE"
        )
    if "status" in fields:
        _validate_choice(fields["status"], ATTENDANCE_STATUSES, "attendance status")
    response = (
        db.table("student_attendance")
        .update(fields)
        .eq("student_attendance_id", str(attendance_id))
        .execute()
    )
    return response.data[0] if response.data else existing


def delete_attendance(attendance_id: UUID | str) -> dict:
    db = get_admin_client()
    existing = _get_attendance(db, attendance_id)
    if existing is None:
        raise AppError("Attendance record not found", status_code=404, code="ATTENDANCE_NOT_FOUND")
    db.table("student_attendance").delete().eq(
        "student_attendance_id", str(attendance_id)
    ).execute()
    return existing

# ============================================================================
# Results CSV upload
# ============================================================================
# Rows are validated individually; only fully valid rows are inserted, so a
# bad row never corrupts valid existing data. Row-level errors are returned.


def _validate_csv_result_row(row: dict) -> list[str]:
    errors: list[str] = []

    for column in ("academic_year_id", "semester_id", "program_id"):
        value = row.get(column) or ""
        try:
            UUID(value)
        except (ValueError, AttributeError):
            errors.append(f"{column} must be a valid UUID")

    result_type = row.get("result_type") or ""
    if result_type not in RESULT_TYPES:
        errors.append(
            f"result_type must be one of {', '.join(RESULT_TYPES)}"
        )

    status = row.get("status") or "published"
    if status not in RESULT_STATUSES:
        errors.append(f"status must be one of {', '.join(RESULT_STATUSES)}")

    for column in RESULT_CSV_NUMERIC_COLUMNS:
        value = (row.get(column) or "").strip()
        if not value:
            continue
        try:
            number = float(value)
        except ValueError:
            errors.append(f"{column} must be a number")
            continue
        if number < 0:
            errors.append(f"{column} must be >= 0")
        elif column in ("sgpa", "cgpa") and number > 100:
            errors.append(f"{column} must be <= 100")

    issued_at = (row.get("issued_at") or "").strip()
    if issued_at:
        try:
            datetime.fromisoformat(issued_at)
        except ValueError:
            errors.append("issued_at must be an ISO-8601 datetime")

    return errors


def _csv_row_to_payload(row: dict, student_id: str) -> dict:
    def _num(column: str) -> float | None:
        value = (row.get(column) or "").strip()
        return float(value) if value else None

    def _uuid(column: str) -> str:
        return str(UUID(row[column]))

    issued_at = (row.get("issued_at") or "").strip()
    return {
        "student_id": student_id,
        "academic_year_id": _uuid("academic_year_id"),
        "semester_id": _uuid("semester_id"),
        "program_id": _uuid("program_id"),
        "result_type": row["result_type"],
        "total_credits_earned": _num("total_credits_earned"),
        "total_credits_max": _num("total_credits_max"),
        "sgpa": _num("sgpa"),
        "cgpa": _num("cgpa"),
        "status": (row.get("status") or "").strip() or "published",
        "issued_at": (
            datetime.fromisoformat(issued_at).isoformat() if issued_at else None
        ),
    }


def upload_results_csv(
    content: bytes,
    institution_id: UUID | str,
) -> CsvUploadResult:
    """Validate and import result-summary rows from a CSV file.

    Required columns: student_number, academic_year_id, semester_id,
    program_id, result_type. Optional: total_credits_earned, total_credits_max,
    sgpa, cgpa, status, issued_at. ``student_number`` is resolved to a student
    within the given institution; unknown students are reported per-row.
    """
    db = get_admin_client()

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(
            "CSV file must be UTF-8 encoded",
            status_code=422,
            code="CSV_INVALID_ENCODING",
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise AppError("CSV file is empty", status_code=422, code="CSV_EMPTY")

    headers = [(name or "").strip() for name in reader.fieldnames]
    missing = [
        column for column in RESULT_CSV_REQUIRED_COLUMNS if column not in headers
    ]
    if missing:
        raise AppError(
            f"CSV is missing required columns: {', '.join(missing)}",
            status_code=422,
            code="CSV_MISSING_COLUMNS",
        )

    student_map = {
        s["student_number"]: s
        for s in academics_repo.list_students(db, institution_id, limit=10000)
    }

    row_errors: list[CsvRowError] = []
    valid_rows: list[tuple[int, dict]] = []
    total_rows = 0

    for line_no, raw in enumerate(reader, start=2):
        total_rows += 1
        row = {
            (key or "").strip(): (value.strip() if isinstance(value, str) else value)
            for key, value in raw.items()
            if key is not None
        }
        row_errors_this = _validate_csv_result_row(row)

        student_number = (row.get("student_number") or "").strip()
        student = student_map.get(student_number)
        if student is None:
            row_errors_this.append(
                "student_number not found in this institution"
            )

        if row_errors_this:
            row_errors.append(
                CsvRowError(
                    row=line_no,
                    student_number=student_number or None,
                    errors=row_errors_this,
                )
            )
            continue

        valid_rows.append((line_no, _csv_row_to_payload(row, student["student_id"])))

    inserted_count = 0
    failed_count = 0
    for line_no, payload in valid_rows:
        try:
            db.table("student_results").insert(payload).execute()
            inserted_count += 1
        except Exception:
            failed_count += 1
            row_errors.append(
                CsvRowError(
                    row=line_no,
                    student_number=None,
                    errors=["database insert failed (duplicate result row?)"],
                )
            )

    return CsvUploadResult(
        total_rows=total_rows,
        inserted_count=inserted_count,
        failed_count=failed_count,
        row_errors=row_errors,
    )





