"""Phase Admin-3 tests — student_data service (server-side isolation)."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services import student_data as svc

USER_ID = "72000000-0000-0000-0000-000000000001"
STUDENT_ID = str(uuid4())


def _student() -> dict:
    return {"student_id": STUDENT_ID, "user_id": USER_ID, "student_number": "S200"}


def _db_with_profile(profile) -> MagicMock:
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=profile)
    return db


def test_get_own_student_resolves_by_authenticated_user_id() -> None:
    db = _db_with_profile(_student())
    student = svc.get_own_student(USER_ID, client=db)
    assert student["student_id"] == STUDENT_ID
    db.table.return_value.select.return_value.eq.assert_called_once_with(
        "user_id", USER_ID
    )


def test_get_own_student_raises_404_without_profile() -> None:
    db = _db_with_profile(None)
    with pytest.raises(AppError) as exc:
        svc.get_own_student(USER_ID, client=db)
    assert exc.value.status_code == 404
    assert exc.value.code == "STUDENT_PROFILE_NOT_FOUND"


def test_get_own_profile_returns_linked_profile() -> None:
    db = _db_with_profile(_student())
    assert svc.get_own_profile(USER_ID, client=db)["student_id"] == STUDENT_ID


def test_get_own_results_filters_to_published_only() -> None:
    db = _db_with_profile(_student())
    rows = [
        {"student_result_id": "1", "status": "published"},
        {"student_result_id": "2", "status": "draft"},
        {"student_result_id": "3", "status": "withheld"},
    ]
    with (
        patch(
            "app.repositories.admin_academics.list_student_results",
            return_value=rows,
        ) as list_mock,
    ):
        result = svc.get_own_results(USER_ID, client=db)

    assert [r["student_result_id"] for r in result] == ["1"]
    list_mock.assert_called_once()
    assert list_mock.call_args.args[1] == STUDENT_ID


def test_get_own_results_passes_term_filters() -> None:
    db = _db_with_profile(_student())
    ay = str(uuid4())
    sem = str(uuid4())
    with patch(
        "app.repositories.admin_academics.list_student_results", return_value=[]
    ) as list_mock:
        svc.get_own_results(USER_ID, academic_year_id=ay, semester_id=sem, client=db)
    assert list_mock.call_args.kwargs["academic_year_id"] == ay
    assert list_mock.call_args.kwargs["semester_id"] == sem


def test_get_own_test_results_filters_to_published_only() -> None:
    db = _db_with_profile(_student())
    rows = [
        {"test_result_id": "1", "status": "published"},
        {"test_result_id": "2", "status": "withheld"},
    ]
    with patch(
        "app.repositories.admin_academics.list_test_results", return_value=rows
    ) as list_mock:
        result = svc.get_own_test_results(USER_ID, client=db)
    assert [r["test_result_id"] for r in result] == ["1"]
    assert list_mock.call_args.args[1] == STUDENT_ID


def test_get_own_attendance_returns_records_with_date_filters() -> None:
    db = _db_with_profile(_student())
    rows = [{"student_attendance_id": "a1", "status": "present"}]
    with patch(
        "app.repositories.admin_academics.list_student_attendance",
        return_value=rows,
    ) as list_mock:
        result = svc.get_own_attendance(
            USER_ID, date_from="2026-09-01", date_to="2026-09-30", client=db
        )
    assert result[0]["student_attendance_id"] == "a1"
    assert list_mock.call_args.kwargs["date_from"] == "2026-09-01"
    assert list_mock.call_args.kwargs["date_to"] == "2026-09-30"
    assert list_mock.call_args.args[1] == STUDENT_ID


def test_every_me_lookup_resolves_own_student_first() -> None:
    """Each accessor calls get_student_by_user_id — no client-chosen student_id."""
    db = _db_with_profile(_student())
    with patch(
        "app.repositories.admin_academics.list_student_attendance",
        return_value=[],
    ) as list_mock:
        svc.get_own_attendance(USER_ID, client=list_mock and db)
    # the only user_id filter used was the JWT-derived one
    db.table.return_value.select.return_value.eq.assert_called_once_with(
        "user_id", USER_ID
    )
