from .support import (
    _active_institution_authorization,
    _assert_staff_denied_on_student_endpoint,
)


def test_staff_cannot_read_own_student_profile():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/profile")
