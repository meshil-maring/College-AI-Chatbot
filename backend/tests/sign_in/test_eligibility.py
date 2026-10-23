"""Test eligibility."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4
from .support import FACULTY_EMAIL

from .credentials import (
    assert_login_failure,
    login_api,
    student_login_api,
)

from .identity import (
    _active_institution_authorization,
)

from .support import (
    APPROVED_EMAIL,
    APPROVED_REGISTER,
    INSTITUTION_A,
    INSTITUTION_CODE,
    institution_db,
    sign_in_account,
    student_account,
    student_row,
)


def test_08_pending_user_sign_in_denied():
    """PENDING student (approval_status='pending') cannot sign in."""
    student = student_row(approval_status="pending")
    response = student_login_api(student=student, identifier=APPROVED_EMAIL)
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_09_rejected_user_sign_in_denied():
    """REJECTED student (approval_status='rejected') cannot sign in."""
    student = student_row(approval_status="rejected")
    response = student_login_api(student=student, identifier=APPROVED_EMAIL)
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_09b_inactive_student_profile_sign_in_denied():
    """A lifecycle-inactive students profile cannot sign in."""
    student = student_row(is_active=False)
    response = student_login_api(student=student, identifier=APPROVED_EMAIL)
    assert response.status_code == 401, response.text


def test_10_inactive_institution_denied():
    """is_active=False institution -> protected access denied."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_EMAIL,
        db=institution_db(is_active=False),
    )
    assert response.status_code == 401, response.text


def test_11_pending_institution_denied():
    """status='pending' institution (is_active=False) -> denied."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        institution={
            "institution_id": str(INSTITUTION_A),
            "name": "Pending College",
            "code": INSTITUTION_CODE,
            "status": "pending",
            "is_active": False,
        },
        db=institution_db(is_active=False),
        by_register=student,
    )
    assert response.status_code == 401, response.text


def test_12_approved_active_student_succeeds():
    """ACTIVE user + ACTIVE institution -> normal authenticated access."""
    student = student_row(approval_status="approved", is_active=True)
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        by_register=student,
        by_roll=None,
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"


def test_08b_pending_user_email_login_denied():
    account = student_account(approval_status="pending")
    assert_login_failure(login_api(account=account, db=institution_db(is_active=True)))


def test_09c_rejected_user_email_login_denied():
    account = student_account(approval_status="rejected")
    assert_login_failure(login_api(account=account, db=institution_db(is_active=True)))


def test_10b_inactive_institution_email_login_denied():
    account = student_account()
    assert_login_failure(login_api(account=account, db=institution_db(is_active=False)))


def test_11b_pending_institution_email_login_denied():
    account = student_account()
    assert_login_failure(login_api(account=account, db=institution_db(is_active=False)))


def test_12b_active_student_email_login_succeeds():
    response = login_api(account=student_account(), db=institution_db(is_active=True))
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"
    assert response.json()["message"] == "Login successful."


def test_12c_missing_public_users_row_denied():
    """No public.users row -> no application account -> sign-in denied."""
    assert_login_failure(login_api(account=None))


def test_12d_non_active_users_status_denied():
    """users.status values other than 'active' are denied (fail-closed)."""
    for status in ("inactive", "deactivated", None, "unknown"):
        assert_login_failure(login_api(account=sign_in_account(status=status)))


def test_pending_faculty_login_returns_actionable_message_after_credentials_verify():
    """A real password plus a pending request explains the required next step."""
    pending = {
        "request_id": str(uuid4()),
        "requested_role": "faculty",
        "status": "pending",
    }
    with patch(
        "app.repositories.platform.tenancy.get_pending_membership_request_for_user",
        return_value=pending,
    ):
        response = login_api(
            account=sign_in_account(status="active"),
            email=FACULTY_EMAIL,
            db=institution_db(),
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "REGISTRATION_PENDING",
            "message": (
                "Your faculty registration is pending. Contact your "
                "institution administrator to continue."
            ),
        }
    }


def test_pending_staff_login_returns_actionable_message_after_credentials_verify():
    """Pending staff receive the same safe state guidance after verification."""
    pending = {
        "request_id": str(uuid4()),
        "requested_role": "staff",
        "status": "pending",
    }
    with patch(
        "app.repositories.platform.tenancy.get_pending_membership_request_for_user",
        return_value=pending,
    ):
        response = login_api(
            account=sign_in_account(status="active"),
            email="staff@example.com",
            db=institution_db(),
        )

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "REGISTRATION_PENDING",
        "message": (
            "Your staff registration is pending. Contact your institution "
            "administrator to continue."
        ),
    }
