from .support import (
    ADMIN_ONLY_REQUESTS,
    INSTITUTION_B,
    STUDENT_B,
    USER_ID,
    _active_institution_authorization,
    _assert_forbidden,
    _assert_tenant_mismatch,
    _auth,
    patch,
)


def test_admin_only_matrix_is_closed_for_every_non_admin_role():
    """*    /admin/* (except the approval queue) is admin-only.

    Asserted for student, faculty AND staff so a staff session can never inherit
    administrative authority — including the mutation entries, which never reach
    a handler body.
    """
    for role in ("student", "faculty", "staff"):
        for method, path, kwargs in ADMIN_ONLY_REQUESTS:
            _assert_forbidden(role, method, path, **kwargs)


def test_student_a_cannot_reach_student_bs_identity_profile():
    """The student chain resolves from the JWT; a foreign students row is refused."""
    foreign = {
        "student_id": STUDENT_B,
        "user_id": USER_ID,
        "institution_id": INSTITUTION_B,
    }
    with (
        _auth("student"),
        patch("app.services.students.student_data.get_admin_client"),
        patch(
            "app.services.students.student_data.get_own_student", return_value=foreign
        ),
    ):
        _assert_tenant_mismatch("student", "GET", "/api/v1/students/me/profile")
