"""Test password privacy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import logging

from .credentials import (
    auth_client,
    login_api,
    student_login_api,
)

from .identity import (
    _active_institution_authorization,
)

from .support import (
    ACCOUNT_PASSWORD,
    APPROVED_EMAIL,
    APPROVED_REGISTER,
    INSTITUTION_CODE,
    SECRET_PASSWORD,
    institution_db,
    student_account,
    student_row,
)


def test_23a_password_never_logged(caplog):
    """No code path logs the submitted password (success, wrong password,
    pending account, and academic identifier login included)."""
    caplog.set_level(logging.DEBUG)

    login_api(account=student_account(), password=SECRET_PASSWORD)
    login_api(
        account=student_account(),
        password=SECRET_PASSWORD,
        auth=auth_client(success=False),
    )
    login_api(
        account=student_account(approval_status="pending"), password=SECRET_PASSWORD
    )
    student_login_api(
        student=student_row(),
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        password=SECRET_PASSWORD,
    )
    student_login_api(
        student=student_row(),
        identifier=APPROVED_EMAIL,
        password=SECRET_PASSWORD,
        auth=auth_client(success=False),
    )

    assert SECRET_PASSWORD not in caplog.text
    assert ACCOUNT_PASSWORD not in caplog.text


def test_23b_password_never_written_to_database():
    """The password is only ever handed to Supabase Auth, never to a DB call.

    Every PostgREST call made during a successful student login is inspected:
    no insert/update/eq/select payload may contain the password.
    """
    db = institution_db()
    response = student_login_api(
        student=student_row(),
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        password=SECRET_PASSWORD,
        db=db,
    )
    assert response.status_code == 200, response.text

    for call in db.method_calls:
        assert SECRET_PASSWORD not in repr(call), call


def test_23c_password_never_persisted_by_the_service_layer():
    """The service layer never writes a password column and never sends it to
    the identity repositories — only the identifier is looked up."""
    student = student_row()
    with (
        patch(
            "app.services.auth.student_auth.get_admin_client",
            return_value=institution_db(auth_user_id=student["user_id"]),
        ),
        patch(
            "app.services.auth.student_auth.create_supabase_client",
            return_value=auth_client(student),
        ),
        patch(
            "app.repositories.admin.admin_academics.get_student_by_register_number",
            return_value=student,
        ) as lookup,
        patch(
            "app.repositories.admin.admin_academics.get_student_by_university_roll_number",
            return_value=None,
        ),
    ):
        from app.services.auth.student_auth import authenticate_student

        authenticate_student(APPROVED_REGISTER, SECRET_PASSWORD, INSTITUTION_CODE)

    lookup_args = repr(lookup.call_args)
    assert SECRET_PASSWORD not in lookup_args
    assert APPROVED_REGISTER in lookup_args


def test_23d_password_forwarded_only_to_supabase_auth():
    """The password is handed to GoTrue exactly once and nowhere else."""
    student = student_row()
    auth = auth_client(student)
    with (
        patch(
            "app.services.auth.student_auth.get_admin_client",
            return_value=institution_db(auth_user_id=student["user_id"]),
        ),
        patch(
            "app.services.auth.student_auth.create_supabase_client", return_value=auth
        ),
        patch(
            "app.repositories.admin.admin_academics.get_student_by_email_global",
            return_value=student,
        ),
    ):
        from app.services.auth.student_auth import authenticate_student

        authenticate_student(APPROVED_EMAIL, SECRET_PASSWORD)

    auth.auth.sign_in_with_password.assert_called_once_with(
        {"email": APPROVED_EMAIL, "password": SECRET_PASSWORD}
    )


def test_23e_login_schemas_carry_no_password_storage_field():
    """No response schema anywhere exposes a stored/plaintext password field."""
    from app.schemas.auth.student_auth import StudentLoginRequest, StudentLoginResponse
    from app.schemas.auth.users import UserRegistrationResponse

    assert set(StudentLoginRequest.model_fields) == {
        "identifier",
        "password",
        "institution_code",
    }
    assert set(StudentLoginResponse.model_fields) == {
        "access_token",
        "refresh_token",
        "expires_in",
        "message",
        "user",
    }
    assert "password" not in set(UserRegistrationResponse.model_fields)
