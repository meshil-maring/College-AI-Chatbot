from .support import (
    _LOGIN_URL,
    _SESSION,
    _active_institution_authorization,
    _envelope,
    client,
    patch,
    pytest,
)


def test_email_login_needs_no_institution_context():
    with (
        patch(
            "app.api.auth.student_auth.authenticate_student", return_value=_SESSION
        ) as auth,
        patch("app.api.auth.student_auth.record_auth_security_event"),
    ):
        response = client.post(
            _LOGIN_URL,
            json={"identifier": "student@college.edu", "password": "secret123"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "student.session.token"
    assert body["user"]["email"] == "student@college.edu"
    assert auth.call_args.args[2] is None


def test_academic_identifier_login_requires_institution_code():
    response = client.post(
        _LOGIN_URL, json={"identifier": "2448052", "password": "secret123"}
    )
    assert response.status_code == 422
    _envelope(response)


@pytest.mark.parametrize("identifier", ["622001", "R622001"])
def test_academic_identifier_login_forwards_the_institution_code(identifier):
    with (
        patch(
            "app.api.auth.student_auth.authenticate_student", return_value=_SESSION
        ) as auth,
        patch("app.api.auth.student_auth.record_auth_security_event"),
    ):
        response = client.post(
            _LOGIN_URL,
            json={
                "identifier": identifier,
                "password": "secret123",
                "institution_code": "GIT",
            },
        )
    assert response.status_code == 200
    assert auth.call_args.args[2] == "GIT"
