"""Test validation."""

from __future__ import annotations

import pytest

from .credentials import (
    assert_student_failure,
    student_login_api,
)

from .identity import (
    _active_institution_authorization,
)

from .support import (
    ACCOUNT_PASSWORD,
    APPROVED_EMAIL,
    APPROVED_REGISTER,
    APPROVED_ROLL,
    LOGIN_URL,
    STUDENT_LOGIN_URL,
    client,
)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"identifier": "", "password": ACCOUNT_PASSWORD},
        {"identifier": "   ", "password": ACCOUNT_PASSWORD},
        {"identifier": APPROVED_EMAIL},
        {"identifier": APPROVED_EMAIL, "password": ""},
        {"password": ACCOUNT_PASSWORD},
    ],
)
def test_21a_student_login_invalid_input_rejected(payload):
    response = client.post(STUDENT_LOGIN_URL, json=payload)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("identifier", [APPROVED_REGISTER, APPROVED_ROLL])
def test_21b_academic_identifier_requires_institution_code(identifier):
    """Register/roll number login without institution_code is invalid input."""
    response = client.post(
        STUDENT_LOGIN_URL, json={"identifier": identifier, "password": ACCOUNT_PASSWORD}
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "institution_code" in body["error"]["message"]


@pytest.mark.parametrize("blank", ["", "   "])
def test_21c_blank_institution_code_rejected(blank):
    response = client.post(
        STUDENT_LOGIN_URL,
        json={
            "identifier": APPROVED_REGISTER,
            "password": ACCOUNT_PASSWORD,
            "institution_code": blank,
        },
    )
    assert response.status_code == 422, response.text


def test_21d_unknown_institution_code_denied_generically():
    """An unknown institution code yields the generic credentials failure."""
    response = student_login_api(
        student=None,
        identifier=APPROVED_REGISTER,
        institution_code="NOPE",
        institution=None,
        by_register=None,
        by_roll=None,
        by_email=None,
    )
    assert_student_failure(response)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": APPROVED_EMAIL},
        {"password": ACCOUNT_PASSWORD},
        {"email": "not-an-email", "password": ACCOUNT_PASSWORD},
        {"email": APPROVED_EMAIL, "password": "short"},
    ],
)
def test_21e_email_login_invalid_input_rejected(payload):
    response = client.post(LOGIN_URL, json=payload)
    assert response.status_code == 422, response.text


def test_21f_malformed_json_body_rejected():
    response = client.post(
        STUDENT_LOGIN_URL,
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422, response.text
