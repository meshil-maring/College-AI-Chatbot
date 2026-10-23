from .support import (
    AUTH_HEADERS,
    FOREIGN_TENANT,
    INSTITUTION_A,
    OTHER_STUDENT_ID,
    STUDENT_ID,
    USER_ID,
    _active_institution_authorization,
    _auth,
    client,
    patch,
)


def test_own_profile_is_resolved_from_the_authenticated_user():
    own = {"register_number": "REG-001", "institution_name": "My institution"}
    with (
        _auth("student"),
        patch(
            "app.api.students.students.student_data.get_own_profile", return_value=own
        ) as get_own,
    ):
        response = client.get(
            "/api/v1/students/me/profile",
            headers=AUTH_HEADERS,
            # A client-supplied identity parameter must never override the JWT.
            params={"student_id": OTHER_STUDENT_ID, "institution_id": FOREIGN_TENANT},
        )
    assert response.status_code == 200
    assert response.json()["register_number"] == "REG-001"
    assert "student_id" not in response.json()
    assert "institution_id" not in response.json()
    assert str(get_own.call_args.args[0]) == USER_ID
    assert get_own.call_args.kwargs["current_user"]["institution_id"] == INSTITUTION_A
