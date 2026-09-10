"""Phase Admin-2 tests for the admin academics repository."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories import admin_academics as repo

INSTITUTION_ID = uuid4()
PROGRAM_ID = uuid4()
STUDENT_ID = uuid4()
RESULT_ID = uuid4()
SEMESTER_ID = uuid4()
ACADEMIC_YEAR_ID = uuid4()


def test_list_students_filters_by_institution_and_orders_by_number() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.limit.return_value.range.return_value.execute.return_value.data = [
        {"student_id": str(STUDENT_ID)}
    ]

    rows = repo.list_students(client, INSTITUTION_ID)

    assert rows == [{"student_id": str(STUDENT_ID)}]
    client.table.assert_called_once_with("students")
    client.table.return_value.select.return_value.eq.assert_called_once_with(
        "institution_id", str(INSTITUTION_ID)
    )
    chain.order.assert_called_once_with("student_number")


def test_list_students_applies_optional_program_and_status_filters() -> None:
    client = MagicMock()
    base = client.table.return_value.select.return_value
    chain = base.eq.return_value
    chain.eq.return_value.eq.return_value.order.return_value.limit.return_value.range.return_value.execute.return_value.data = []

    rows = repo.list_students(
        client, INSTITUTION_ID, program_id=PROGRAM_ID, status="active"
    )

    assert rows == []
    base.eq.assert_called_once_with("institution_id", str(INSTITUTION_ID))
    chain.eq.assert_called_once_with("program_id", str(PROGRAM_ID))
    chain.eq.return_value.eq.assert_called_once_with("status", "active")


def test_get_student_and_get_student_by_user_id_use_maybe_single() -> None:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "student_id": str(STUDENT_ID)
    }

    row = repo.get_student(client, STUDENT_ID)
    assert row == {"student_id": str(STUDENT_ID)}
    client.table.return_value.select.return_value.eq.assert_called_with(
        "student_id", str(STUDENT_ID)
    )

    row = repo.get_student_by_user_id(client, STUDENT_ID)
    assert row == {"student_id": str(STUDENT_ID)}
    client.table.return_value.select.return_value.eq.assert_called_with(
        "user_id", str(STUDENT_ID)
    )


def test_list_student_results_orders_by_issued_at_desc() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.execute.return_value.data = [
        {"student_result_id": str(RESULT_ID)}
    ]

    rows = repo.list_student_results(client, STUDENT_ID)

    assert rows == [{"student_result_id": str(RESULT_ID)}]
    client.table.assert_called_once_with("student_results")
    client.table.return_value.select.return_value.eq.assert_called_once_with(
        "student_id", str(STUDENT_ID)
    )
    chain.order.assert_called_once_with("issued_at", desc=True)


def test_list_student_results_applies_year_and_semester_filters() -> None:
    client = MagicMock()
    base = client.table.return_value.select.return_value
    chain = base.eq.return_value
    chain.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = []

    repo.list_student_results(
        client,
        STUDENT_ID,
        academic_year_id=ACADEMIC_YEAR_ID,
        semester_id=SEMESTER_ID,
    )

    base.eq.assert_called_once_with("student_id", str(STUDENT_ID))
    chain.eq.assert_called_once_with("academic_year_id", str(ACADEMIC_YEAR_ID))
    chain.eq.return_value.eq.assert_called_once_with("semester_id", str(SEMESTER_ID))


def test_get_student_result_with_items_selects_nested_items() -> None:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "student_result_id": str(RESULT_ID),
        "student_result_items": [],
    }

    row = repo.get_student_result_with_items(client, RESULT_ID)

    assert row["student_result_id"] == str(RESULT_ID)
    client.table.assert_called_once_with("student_results")
    select_arg = client.table.return_value.select.call_args.args[0]
    assert "student_result_items(" in select_arg


def test_list_test_results_orders_by_conducted_at_desc() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.limit.return_value.execute.return_value.data = [
        {"test_result_id": "1"}
    ]

    rows = repo.list_test_results(client, STUDENT_ID)

    assert rows == [{"test_result_id": "1"}]
    client.table.assert_called_once_with("test_results")
    chain.order.assert_called_once_with("conducted_at", desc=True)


def test_list_test_results_applies_semester_filter() -> None:
    client = MagicMock()
    base = client.table.return_value.select.return_value
    chain = base.eq.return_value
    chain.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    repo.list_test_results(
        client, STUDENT_ID, academic_year_id=ACADEMIC_YEAR_ID, semester_id=SEMESTER_ID
    )

    chain.eq.assert_called_once_with("academic_year_id", str(ACADEMIC_YEAR_ID))
    chain.eq.return_value.eq.assert_called_once_with("semester_id", str(SEMESTER_ID))


def test_list_student_attendance_applies_date_range_filters() -> None:
    client = MagicMock()
    base = client.table.return_value.select.return_value
    chain = base.eq.return_value
    chain.eq.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"student_attendance_id": "1"}
    ]

    rows = repo.list_student_attendance(
        client,
        STUDENT_ID,
        academic_year_id=ACADEMIC_YEAR_ID,
        semester_id=SEMESTER_ID,
        date_from="2026-08-01",
        date_to="2026-08-31",
    )

    assert rows == [{"student_attendance_id": "1"}]
    client.table.assert_called_once_with("student_attendance")
    base.eq.assert_called_once_with("student_id", str(STUDENT_ID))
    chain.eq.assert_called_once_with("academic_year_id", str(ACADEMIC_YEAR_ID))
    chain.eq.return_value.eq.assert_called_once_with("semester_id", str(SEMESTER_ID))
    chain.eq.return_value.eq.return_value.gte.assert_called_once_with(
        "date", "2026-08-01"
    )
    chain.eq.return_value.eq.return_value.gte.return_value.lte.assert_called_once_with(
        "date", "2026-08-31"
    )
    chain.eq.return_value.eq.return_value.gte.return_value.lte.return_value.order.assert_called_once_with(
        "date", desc=True
    )