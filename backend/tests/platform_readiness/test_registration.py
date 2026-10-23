from .support import (
    AppError,
    TENANT_A,
    _active_institution_authorization,
    _assert_no_leak,
    _envelope,
    client,
    patch,
)


def test_registration_unexpected_failure_is_safe_500():
    with patch(
        "app.services.auth.student_registration._register_student",
        side_effect=RuntimeError("SELECT FROM users WHERE boom"),
    ):
        r = client.post(
            "/api/v1/registration",
            json={
                "institution_id": TENANT_A,
                "email": "n@college.edu",
                "password": "secret12",
                "first_name": "Nia",
                "last_name": "Rao",
                "register_number": "REG-903",
            },
        )
    assert r.status_code == 500
    assert _envelope(r)["code"] == "REGISTRATION_FAILED"
    _assert_no_leak(r.text)
    assert "secret12" not in r.text


def test_duplicate_registration_is_409():
    with patch(
        "app.services.auth.student_registration._register_student",
        side_effect=AppError("dup", status_code=409, code="EMAIL_ALREADY_REGISTERED"),
    ):
        r = client.post(
            "/api/v1/registration",
            json={
                "institution_id": TENANT_A,
                "email": "d@college.edu",
                "password": "secret12",
                "first_name": "Dee",
                "last_name": "Iyer",
                "register_number": "REG-904",
            },
        )
    assert r.status_code == 409
    assert _envelope(r)["code"] == "EMAIL_ALREADY_REGISTERED"
    _assert_no_leak(r.text)
