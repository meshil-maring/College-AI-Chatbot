"""Offline regressions for legacy academic access and student account lifecycle."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app
from app.services.student_auth import SafeAuthFailure, authenticate_student

USER = "71000000-0000-0000-0000-000000000001"
AUTH = "81000000-0000-0000-0000-000000000001"
STUDENT = "91000000-0000-0000-0000-000000000001"
TENANT = "a1111111-0000-0000-0000-000000000001"
OTHER = "b2222222-0000-0000-0000-000000000002"
RESULT = "c3333333-0000-0000-0000-000000000003"
PATHS = ["results", f"results/{RESULT}", "test-results", "attendance"]


def profile(**changes):
    return dict(student_id=STUDENT, user_id=USER, institution_id=TENANT,
                email="fixture@example.com", approval_status="approved",
                is_active=True, **changes)


@pytest.fixture
def academic_client():
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": USER, "auth_user_id": AUTH, "roles": ["student"],
        "institution_id": TENANT,
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("state", ["pending", "rejected", "inactive", "other_tenant", "institution_inactive"])
def test_legacy_academics_recheck_eligibility_before_read(academic_client, path, state):
    row = profile()
    if state in {"pending", "rejected"}:
        row["approval_status"] = state
    elif state == "inactive":
        row["is_active"] = False
    elif state == "other_tenant":
        row["institution_id"] = OTHER
    with (
        patch("app.services.student_context.get_admin_client", return_value=MagicMock()),
        patch("app.repositories.admin_academics.get_student_approval_row_by_user_id", return_value=row),
        patch("app.services.student_auth._assert_institution_active", side_effect=SafeAuthFailure() if state == "institution_inactive" else None),
        patch("app.api.students.student_data.get_own_results") as results,
        patch("app.api.students.student_data.get_own_result") as detail,
        patch("app.api.students.student_data.get_own_test_results") as tests,
        patch("app.api.students.student_data.get_own_attendance") as attendance,
    ):
        response = academic_client.get(f"/api/v1/students/me/{path}")
    assert response.status_code == (401 if state == "institution_inactive" else 403)
    for read in (results, detail, tests, attendance):
        read.assert_not_called()


@pytest.mark.parametrize("path", ["results", "test-results", "attendance"])
def test_approved_legacy_academics_use_only_authenticated_identity(academic_client, path):
    db = MagicMock()
    with (
        patch("app.services.student_context.get_admin_client", return_value=db),
        patch("app.services.student_data.get_admin_client", return_value=db),
        patch("app.repositories.admin_academics.get_student_approval_row_by_user_id", return_value=profile()) as identity,
        patch("app.repositories.admin_academics.get_student_by_user_id", return_value=profile()),
        patch("app.services.student_auth._assert_institution_active"),
        patch("app.repositories.admin_academics.list_student_results", return_value=[]) as results,
        patch("app.repositories.admin_academics.list_test_results", return_value=[]) as tests,
        patch("app.repositories.admin_academics.list_student_attendance", return_value=[]) as attendance,
    ):
        response = academic_client.get(f"/api/v1/students/me/{path}", params={"student_id": OTHER, "institution_id": OTHER})
    assert response.status_code == 200
    identity.assert_called_once_with(db, USER)
    read = {"results": results, "test-results": tests, "attendance": attendance}[path]
    assert read.call_args.args[1] == STUDENT


@pytest.mark.parametrize("foreign_tenant", [False, True])
def test_approved_student_cannot_read_another_students_result(academic_client, foreign_tenant):
    row = {"student_id": OTHER, "institution_id": OTHER if foreign_tenant else TENANT,
           "status": "published"}
    with (
        patch("app.services.student_context.get_admin_client", return_value=MagicMock()),
        patch("app.services.student_data.get_admin_client", return_value=MagicMock()),
        patch("app.repositories.admin_academics.get_student_approval_row_by_user_id", return_value=profile()),
        patch("app.repositories.admin_academics.get_student_by_user_id", return_value=profile()),
        patch("app.services.student_auth._assert_institution_active"),
        patch("app.repositories.results.get_student_result_with_items", return_value=row),
    ):
        response = academic_client.get(f"/api/v1/students/me/results/{RESULT}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"


@pytest.mark.parametrize("account", [None, {"status": "inactive", "auth_user_id": AUTH},
                                    {"status": "deactivated", "auth_user_id": AUTH},
                                    {"status": "active", "auth_user_id": None}])
def test_identifier_login_rejects_unusable_public_account(account):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = account
    with (
        patch("app.services.student_auth.get_admin_client", return_value=db),
        patch("app.services.student_auth._resolve_identity", return_value=("fixture@example.com", TENANT, profile())),
        patch("app.services.student_auth._assert_institution_active"),
        patch("app.services.student_auth._supabase_sign_in") as provider,
    ):
        with pytest.raises(SafeAuthFailure):
            authenticate_student("REG-FIXTURE", "test-password", "FIXTURE")
    provider.assert_not_called()


def test_identifier_login_rejects_mismatched_auth_link():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "status": "active", "auth_user_id": AUTH,
    }
    with (
        patch("app.services.student_auth.get_admin_client", return_value=db),
        patch("app.services.student_auth._resolve_identity", return_value=("fixture@example.com", TENANT, profile())),
        patch("app.services.student_auth._assert_institution_active"),
        patch("app.services.student_auth._supabase_sign_in", return_value={"user": {"id": OTHER}}),
    ):
        with pytest.raises(SafeAuthFailure):
            authenticate_student("REG-FIXTURE", "test-password", "FIXTURE")
