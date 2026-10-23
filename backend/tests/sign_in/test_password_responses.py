"""Test password responses."""

from __future__ import annotations

import json

from .credentials import (
    _assert_no_secret,
    auth_client,
    login_api,
    student_login_api,
)

from .identity import (
    _active_institution_authorization,
)

from .support import (
    APPROVED_EMAIL,
    APPROVED_REGISTER,
    INSTITUTION_CODE,
    SECRET_PASSWORD,
    student_account,
    student_row,
)


def test_22a_password_never_returned_on_student_login_success():
    response = student_login_api(
        student=student_row(),
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        password=SECRET_PASSWORD,
    )
    assert response.status_code == 200, response.text
    _assert_no_secret(response, SECRET_PASSWORD)


def test_22b_password_never_returned_on_email_login_success():
    response = login_api(account=student_account(), password=SECRET_PASSWORD)
    assert response.status_code == 200, response.text
    _assert_no_secret(response, SECRET_PASSWORD)


def test_22c_password_never_returned_on_failure():
    """Failures never echo the submitted password (student + email)."""
    student_fail = student_login_api(
        student=student_row(),
        identifier=APPROVED_EMAIL,
        password=SECRET_PASSWORD,
        auth=auth_client(success=False),
    )
    assert student_fail.status_code == 401
    _assert_no_secret(student_fail, SECRET_PASSWORD)

    email_fail = login_api(
        account=student_account(),
        password=SECRET_PASSWORD,
        auth=auth_client(success=False),
    )
    assert email_fail.status_code == 400
    _assert_no_secret(email_fail, SECRET_PASSWORD)


def test_22d_no_password_field_in_any_login_payload():
    """No ``password`` key is ever present in a login response body."""
    for response in (
        login_api(account=student_account()),
        student_login_api(
            student=student_row(),
            identifier=APPROVED_REGISTER,
            institution_code=INSTITUTION_CODE,
        ),
    ):
        body = response.json()
        assert "password" not in body
        assert "password" not in body.get("user", {})
        assert "password" not in json.dumps(body).lower().replace(
            '"invalid identifier or password"', ""
        )
