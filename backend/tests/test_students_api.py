"""Phase Admin-3 tests — Student "me" endpoints (authorization + isolation).

The student identity is resolved server-side from the authenticated JWT;
the client can never select another student's data.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

STUDENT_USER_ID = "71000000-0000-0000-0000-000000000001"
OTHER_USER_ID = "71000000-0000-0000-0000-000000000002"
STUDENT_ID = str(uuid4())
OTHER_STUDENT_ID = str(uuid4())


def _student_user(user_id: str = STUDENT_USER_ID):
    return {
        "user_id": user_id,
        "auth_user_id": str(uuid4()),
        "email": "student@example.com",
        "roles": ["student"],
    }


def _student_row(student_id: str = STUDENT_ID) -> dict:
    return {
        "student_id": student_id,
        "user_id": STUDENT_USER_ID,
        "institution_id": str(uuid4()),
        "student_number": "S100",
        "program_id": None,
        "academic_year_id": None,
        "enrollment_date": "2025-08-01",
        "expected_graduation_date": None,
        "status": "active",
        "is_active": True,
        "created_at": "2025-08-01T00:00:00+00:00",
        "updated_at": "2025-08-01T00:00:00+00:00",
    }


@pytest.fixture(autouse=True)
def student_auth():
    app.dependency_overrides[get_current_user] = _student_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _resolved_db():
    """Mock DB whose students lookup resolves the JWT user to a profile."""
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=_student_row())
    return db


def test_me_profile_requires_authentication() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get("/api/v1/students/me/profile")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_me_profile_resolves_student_server_side_from_jwt() -> None:
    db = _resolved_db()
    with patch("app.services.student_data.get_admin_client", return_value=db):
        response = client.get("/api/v1/students/me/profile")

    assert response.status_code == 200
    assert response.json()["student_id"] == STUDENT_ID
    # The lookup key is the JWT-derived user id — never anything client-supplied.
    db.table.return_value.select.return_value.eq.assert_called_once_with(
        "user_id", STUDENT_USER_ID
    )


def test_me_profile_ignores_client_supplied_student_id() -> None:
    """Even if a client passes ?student_id=..., the profile is the caller's own."""
    db = _resolved_db()
    with patch("app.services.student_data.get_admin_client", return_value=db):
        response = client.get(
            "/api/v1/students/me/profile",
            params={"student_id": OTHER_STUDENT_ID},
        )

    assert response.status_code == 200
    assert response.json()["student_id"] == STUDENT_ID
    db.table.return_value.select.return_value.eq.assert_called_once_with(
        "user_id", STUDENT_USER_ID
    )


def test_me_profile_404_when_no_student_profile_linked() -> None:
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=None)
    with patch("app.services.student_data.get_admin_client", return_value=db):
        response = client.get("/api/v1/students/me/profile")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"

def test_me_results_returns_only_own_published_rows() -> None:
    db = _resolved_db()
    results = [
        {"student_result_id": str(uuid4()), "student_id": STUDENT_ID, "status": "published", "sgpa": 8.5},
        {"student_result_id": str(uuid4()), "student_id": STUDENT_ID, "status": "draft", "sgpa": 7.0},
        {"student_result_id": str(uuid4()), "student_id": STUDENT_ID, "status": "withheld", "sgpa": 6.0},
    ]
    with (
        patch("app.services.student_data.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin_academics.list_student_results",
            return_value=results,
        ) as list_mock,
    ):
        response = client.get("/api/v1/students/me/results")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["student_id"] == STUDENT_ID
    assert body[0]["status"] == "published"
    list_mock.assert_called_once()
    # Ownership enforced server-side: the queried student_id comes from the JWT.
    assert list_mock.call_args.args[1] == STUDENT_ID


def test_me_test_results_returns_only_own_published_rows() -> None:
    db = _resolved_db()
    rows = [
        {"test_result_id": str(uuid4()), "student_id": STUDENT_ID, "status": "published"},
        {"test_result_id": str(uuid4()), "student_id": STUDENT_ID, "status": "withheld"},
    ]
    with (
        patch("app.services.student_data.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin_academics.list_test_results",
            return_value=rows,
        ) as list_mock,
    ):
        response = client.get("/api/v1/students/me/test-results")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "published"
    assert list_mock.call_args.args[1] == STUDENT_ID


def test_me_attendance_returns_own_records() -> None:
    db = _resolved_db()
    rows = [
        {"student_attendance_id": str(uuid4()), "student_id": STUDENT_ID, "status": "present"}
    ]
    with (
        patch("app.services.student_data.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin_academics.list_student_attendance",
            return_value=rows,
        ) as list_mock,
    ):
        response = client.get(
            "/api/v1/students/me/attendance",
            params={"date_from": "2026-09-01", "date_to": "2026-09-30"},
        )

    assert response.status_code == 200
    assert response.json()[0]["student_id"] == STUDENT_ID
    kwargs = list_mock.call_args.kwargs
    assert kwargs["date_from"] == "2026-09-01"
    assert kwargs["date_to"] == "2026-09-30"


def test_me_results_404_when_no_profile() -> None:
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=None)
    with patch("app.services.student_data.get_admin_client", return_value=db):
        response = client.get("/api/v1/students/me/results")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


def test_other_student_token_cannot_leak_first_students_data() -> None:
    """A different JWT resolves to a different (or no) profile — never student A's."""
    app.dependency_overrides[get_current_user] = lambda: _student_user(OTHER_USER_ID)
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=None)
    with patch("app.services.student_data.get_admin_client", return_value=db):
        response = client.get("/api/v1/students/me/profile")
    assert response.status_code == 404
    db.table.return_value.select.return_value.eq.assert_called_once_with(
        "user_id", OTHER_USER_ID
    )

