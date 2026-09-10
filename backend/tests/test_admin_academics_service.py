"""Phase Admin-3 tests — academics service (CSV validation + CRUD rules)."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services import admin_academics as svc
from app.services.admin_academics import (
    AttendanceCreate,
    CsvUploadResult,
    ResultCreate,
    ResultItemCreate,
    StudentCreate,
    TestResultCreate,
    upload_results_csv,
)

INSTITUTION_ID = str(uuid4())
STUDENT_ID = str(uuid4())
AY_ID = str(uuid4())
SEM_ID = str(uuid4())
PROG_ID = str(uuid4())

CSV_HEADER = (
    "student_number,academic_year_id,semester_id,program_id,result_type,"
    "total_credits_earned,total_credits_max,sgpa,cgpa,status,issued_at\n"
)


def _csv_db(students=None) -> MagicMock:
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.range.return_value
    ).execute.return_value = MagicMock(data=students or [])
    (
        db.table.return_value.insert.return_value.execute
    ).return_value = MagicMock(data=[{"student_result_id": str(uuid4())}])
    return db


def _csv_rows(*rows: str) -> bytes:
    return (CSV_HEADER + "".join(r + "\n" for r in rows)).encode("utf-8")


# ============================================================================
# CSV validation
# ============================================================================


def _run_csv(content: bytes, students=None, db=None):
    if db is None:
        db = _csv_db(students=students)
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        result = upload_results_csv(content, INSTITUTION_ID)
    return result, db


def test_csv_upload_inserts_only_valid_rows() -> None:
    valid = f"S001,{AY_ID},{SEM_ID},{PROG_ID},semester,24,26,8.5,8.0,published,2026-06-01T00:00:00+00:00"
    result, db = _run_csv(
        _csv_rows(valid),
        students=[{"student_number": "S001", "student_id": STUDENT_ID}],
    )

    assert isinstance(result, CsvUploadResult)
    assert result.total_rows == 1
    assert result.inserted_count == 1
    assert result.row_errors == []
    inserted = db.table.return_value.insert.call_args.args[0]
    assert inserted["student_id"] == STUDENT_ID
    assert inserted["result_type"] == "semester"
    assert inserted["sgpa"] == 8.5
    assert inserted["status"] == "published"


def test_csv_upload_reports_row_level_errors_without_inserting_bad_rows() -> None:
    result, db = _run_csv(
        _csv_rows(
            f"S001,not-a-uuid,{SEM_ID},{PROG_ID},bogus,abc,-1,150,,draft,not-a-date",
            f"S999,{AY_ID},{SEM_ID},{PROG_ID},semester,,,,,,",
        ),
        students=[{"student_number": "S001", "student_id": STUDENT_ID}],
    )

    assert result.inserted_count == 0
    assert len(result.row_errors) == 2
    first = result.row_errors[0]
    assert first.row == 2
    joined = " ".join(first.errors)
    assert "valid UUID" in joined
    assert "result_type" in joined
    assert "issued_at" in joined
    assert any("sgpa" in e for e in first.errors)
    assert any("not found" in e for e in result.row_errors[1].errors)
    db.table.return_value.insert.assert_not_called()

def test_csv_upload_never_corrupts_existing_data_on_duplicate_insert() -> None:
    db = _csv_db(students=[{"student_number": "S001", "student_id": STUDENT_ID}])
    # Second insert (duplicate row) fails at DB level.
    db.table.return_value.insert.return_value.execute.side_effect = [
        MagicMock(data=[{"student_result_id": str(uuid4())}]),
        Exception("duplicate key"),
    ]
    result, _ = _run_csv(
        _csv_rows(
            f"S001,{AY_ID},{SEM_ID},{PROG_ID},semester,,,,,,",
            f"S001,{AY_ID},{SEM_ID},{PROG_ID},semester,,,,,,",
        ),
        db=db,
    )

    assert result.inserted_count == 1
    assert result.failed_count == 1
    assert len(result.row_errors) == 1


def test_csv_upload_rejects_missing_required_columns() -> None:
    db = _csv_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        with pytest.raises(AppError) as exc:
            upload_results_csv(b"student_number,sgpa\nS001,8.5\n", INSTITUTION_ID)
    assert exc.value.code == "CSV_MISSING_COLUMNS"
    assert "semester_id" in exc.value.message


def test_csv_upload_rejects_empty_file() -> None:
    db = _csv_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        with pytest.raises(AppError) as exc:
            upload_results_csv(b"", INSTITUTION_ID)
    assert exc.value.code == "CSV_EMPTY"


def test_csv_upload_rejects_non_utf8() -> None:
    db = _csv_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        with pytest.raises(AppError) as exc:
            upload_results_csv(b"\xff\xfe\x00bad", INSTITUTION_ID)
    assert exc.value.code == "CSV_INVALID_ENCODING"


# ============================================================================
# CRUD rules
# ============================================================================


def test_create_student_rejects_invalid_status() -> None:
    with pytest.raises(AppError) as exc:
        svc.create_student(
            StudentCreate(
                user_id=uuid4(),
                institution_id=uuid4(),
                student_number="S1",
                enrollment_date="2026-08-01",
                status="bogus",
            )
        )
    assert exc.value.code == "INVALID_STUDENT_STATUS"


def test_create_student_inserts_serialized_payload() -> None:
    db = MagicMock()
    (
        db.table.return_value.insert.return_value.execute
    ).return_value = MagicMock(data=[{"student_id": STUDENT_ID}])
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        result = svc.create_student(
            StudentCreate(
                user_id=uuid4(),
                institution_id=uuid4(),
                student_number="S1",
                enrollment_date="2026-08-01",
            )
        )
    assert result == {"student_id": STUDENT_ID}


def test_create_result_with_items_persists_both_tables() -> None:
    db = MagicMock()
    result_id = str(uuid4())
    (
        db.table.return_value.insert.return_value.execute
    ).side_effect = [
        MagicMock(data=[{"student_result_id": result_id}]),
        MagicMock(data=[{"student_result_item_id": str(uuid4())}]),
    ]
    payload = ResultCreate(
        student_id=uuid4(),
        academic_year_id=uuid4(),
        semester_id=uuid4(),
        program_id=uuid4(),
        result_type="semester",
        sgpa=8.5,
        items=[ResultItemCreate(course_id=uuid4(), credits_earned=4, letter_grade="A")],
    )
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        result = svc.create_result(payload)

    assert result["student_result_id"] == result_id
    assert len(result["items"]) == 1
    tables = [call.args[0] for call in db.table.call_args_list]
    assert tables == ["student_results", "student_result_items"]
    item_rows = db.table.return_value.insert.call_args_list[1].args[0]
    assert item_rows[0]["student_result_id"] == result_id


def test_create_test_result_rejects_scored_over_max() -> None:
    with pytest.raises(AppError) as exc:
        svc.create_test_result(
            TestResultCreate(
                student_id=uuid4(),
                course_id=uuid4(),
                academic_year_id=uuid4(),
                semester_id=uuid4(),
                test_name="Quiz 1",
                test_type="quiz",
                max_marks=20,
                scored_marks=25,
            )
        )
    assert exc.value.code == "INVALID_SCORES"


def test_create_attendance_rejects_invalid_status() -> None:
    with pytest.raises(AppError) as exc:
        svc.create_attendance(
            AttendanceCreate(
                student_id=uuid4(),
                section_id=uuid4(),
                academic_year_id=uuid4(),
                semester_id=uuid4(),
                date="2026-09-01",
                status="bogus",
            )
        )
    assert exc.value.code == "INVALID_ATTENDANCE_STATUS"


