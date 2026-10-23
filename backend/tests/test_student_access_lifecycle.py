"""Student login lifecycle remains enforced after academic retirement."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.auth.student_auth import SafeAuthFailure, authenticate_student

USER = "71000000-0000-0000-0000-000000000001"
AUTH = "81000000-0000-0000-0000-000000000001"
STUDENT = "91000000-0000-0000-0000-000000000001"
TENANT = "a1111111-0000-0000-0000-000000000001"
OTHER = "b2222222-0000-0000-0000-000000000002"


def profile(**changes):
    return dict(student_id=STUDENT, user_id=USER, institution_id=TENANT,
                email="fixture@example.com", approval_status="approved",
                is_active=True, **changes)


@pytest.mark.parametrize("account", [None, {"status": "inactive", "auth_user_id": AUTH},
                                    {"status": "deactivated", "auth_user_id": AUTH},
                                    {"status": "active", "auth_user_id": None}])
def test_identifier_login_rejects_unusable_public_account(account):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = account
    with (
        patch("app.services.auth.student_auth.get_admin_client", return_value=db),
        patch("app.services.auth.student_auth._resolve_identity", return_value=("fixture@example.com", TENANT, profile())),
        patch("app.services.auth.student_auth._assert_institution_active"),
        patch("app.services.auth.student_auth._supabase_sign_in") as provider,
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
        patch("app.services.auth.student_auth.get_admin_client", return_value=db),
        patch("app.services.auth.student_auth._resolve_identity", return_value=("fixture@example.com", TENANT, profile())),
        patch("app.services.auth.student_auth._assert_institution_active"),
        patch("app.services.auth.student_auth._supabase_sign_in", return_value={"user": {"id": OTHER}}),
    ):
        with pytest.raises(SafeAuthFailure):
            authenticate_student("REG-FIXTURE", "test-password", "FIXTURE")
