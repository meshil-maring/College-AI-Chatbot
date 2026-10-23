from .support import (
    AUTH_HEADERS,
    FOREIGN_TENANT,
    INSTITUTION_A,
    OTHER_STUDENT_ID,
    _active_institution_authorization,
    _auth,
    _envelope,
    client,
    patch,
)


def test_cross_tenant_student_row_is_denied():
    foreign = {"student_id": OTHER_STUDENT_ID, "institution_id": FOREIGN_TENANT}
    with (
        _auth("student", tenant=INSTITUTION_A),
        patch("app.services.students.student_data.get_admin_client"),
        patch(
            "app.services.students.student_data.get_own_student", return_value=foreign
        ),
    ):
        response = client.get("/api/v1/students/me/profile", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _envelope(response)["code"] == "TENANT_MISMATCH"
