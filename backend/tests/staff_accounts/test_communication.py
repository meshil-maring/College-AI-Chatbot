from .support import (
    _active_institution_authorization,
    _assert_staff_denied_on_student_endpoint,
    _assert_staff_forbidden,
)


def test_staff_denied_admin_notices_list():
    _assert_staff_forbidden("GET", "/api/v1/admin/notices")


def test_staff_denied_admin_notice_create():
    _assert_staff_forbidden("POST", "/api/v1/admin/notices", json={})


def test_staff_denied_admin_faqs_list():
    _assert_staff_forbidden("GET", "/api/v1/admin/faqs")


def test_staff_cannot_read_student_notices():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/notices")
