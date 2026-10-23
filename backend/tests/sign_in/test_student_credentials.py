"""Test student credentials."""

from __future__ import annotations

from .credentials import (
    assert_student_failure,
    auth_client,
    student_login_api,
)

from .identity import (
    _active_institution_authorization,
)

from .support import (
    APPROVED_EMAIL,
    APPROVED_REGISTER,
    APPROVED_ROLL,
    INSTITUTION_B,
    INSTITUTION_CODE,
    student_row,
)


def test_01_student_email_login_succeeds():
    """Email + password needs no institution context (globally unique)."""
    student = student_row()
    response = student_login_api(student=student, identifier=APPROVED_EMAIL)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"] == "mock-access-token"
    assert body["message"] == "Login successful."
    assert body["user"]["email"] == APPROVED_EMAIL


def test_02_student_register_number_login_succeeds():
    """Register number + password + institution_code."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        by_register=student,
        by_roll=None,
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"


def test_03_student_university_roll_number_login_succeeds():
    """University roll number + password + institution_code."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_ROLL,
        institution_code=INSTITUTION_CODE,
        by_register=None,
        by_roll=student,
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"
    assert response.json()["access_token"] == "mock-access-token"


def test_04_register_number_wrong_institution_code_denied():
    """The institution code scopes the lookup — a wrong code finds nobody."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code="WRONG",
        institution={
            "institution_id": str(INSTITUTION_B),
            "name": "Other College",
            "code": "WRONG",
            "status": "active",
            "is_active": True,
        },
        by_register=None,
        by_roll=None,
    )
    assert_student_failure(response)


def test_05_roll_number_wrong_institution_code_denied():
    """Same fail-closed scoping for the university roll number path."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_ROLL,
        institution_code="WRONG",
        institution={
            "institution_id": str(INSTITUTION_B),
            "name": "Other College",
            "code": "WRONG",
            "status": "active",
            "is_active": True,
        },
        by_register=None,
        by_roll=None,
    )
    assert_student_failure(response)


def test_06_nonexistent_student_denied():
    """Unknown identifier -> generic credentials failure (never 404)."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier="does-not-exist@college.edu",
        by_email=None,
    )
    # Phase 6.5 contract: the student endpoint normalizes every failure to the
    # SafeAuthFailure envelope (401 INVALID_CREDENTIALS); existence is never
    # disclosed and 404 is never returned.
    assert_student_failure(response)


def test_07_wrong_password_denied():
    """Supabase Auth rejects the credential — no session is issued."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_EMAIL,
        password="wrong-password",
        auth=auth_client(student, success=False),
    )
    assert_student_failure(response)
