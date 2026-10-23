from .support import (
    _active_institution_authorization,
    _assert_staff_forbidden,
)


def test_staff_denied_admin_dashboard():
    _assert_staff_forbidden("GET", "/api/v1/admin/dashboard")
