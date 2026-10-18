"""Registration provider failures must not create unusable/orphaned accounts."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import AppError
from app.schemas.users import UserRegistrationRequest
from app.services import student_registration as student
from app.services import user_registration as unified

INST = "a1111111-0000-0000-0000-000000000001"


def test_public_signup_duplicate_with_no_identities_is_a_conflict():
    provider = MagicMock()
    provider.auth.sign_up.return_value = SimpleNamespace(
        user=SimpleNamespace(id="synthetic-user", identities=[]),
    )
    with patch.object(student, "create_supabase_client", return_value=provider):
        with pytest.raises(AppError) as exc:
            student._create_auth_account("fixture@example.com", "test-password")
    assert exc.value.status_code == 409
    assert exc.value.code == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.parametrize("entrypoint", ["legacy", "unified"])
def test_account_write_app_error_compensates_new_auth_user(entrypoint):
    fields = dict(email="fixture@example.com", password="test-password",
                  first_name="Test", last_name="Student", register_number="FIXTURE-1")
    payload = (student.StudentRegistrationRequest(institution_id=INST, **fields)
               if entrypoint == "legacy" else UserRegistrationRequest(
                   registration_type="student", institution_code="TEST", **fields))
    failure = AppError("Account write failed", status_code=503, code="ACCOUNT_WRITE_FAILED")
    with (
        patch.object(student, "get_admin_client", return_value=MagicMock()),
        patch.object(unified, "get_admin_client", return_value=MagicMock()),
        patch.object(student, "_get_institution"),
        patch.object(unified, "_resolve_institution", return_value={"institution_id": INST}),
        patch.object(student, "_find_user_by_email", return_value=None),
        patch.object(student, "_assert_no_duplicate_identities"),
        patch.object(student, "_create_auth_account", return_value="new-auth-user"),
        patch.object(student, "_create_public_user", side_effect=failure),
        patch.object(student, "_try_delete_auth_user") as cleanup,
    ):
        with pytest.raises(AppError) as exc:
            (student.register_student if entrypoint == "legacy" else unified.register_user)(payload)
    assert exc.value is failure
    cleanup.assert_called_once_with("new-auth-user")
