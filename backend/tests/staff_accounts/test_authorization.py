from .support import (
    STUDENT_A,
    SUPPORTED_ROLES,
    _active_institution_authorization,
    _assert_staff_denied_on_student_endpoint,
    _assert_staff_forbidden,
    resolve_primary_role,
    _patch_staff_auth,
    client,
    AUTH_HEADERS,
)


def test_staff_multi_role_precedence_unchanged():
    """admin > staff > faculty > student precedence is untouched."""
    assert resolve_primary_role(["student", "staff"]) == "staff"
    assert resolve_primary_role(["faculty", "staff"]) == "staff"
    assert resolve_primary_role(["staff", "admin"]) == "admin"
    assert resolve_primary_role(list(SUPPORTED_ROLES)) == "super_admin"


def test_staff_denied_admin_identity():
    _assert_staff_forbidden("GET", "/api/v1/admin/me")












def test_staff_denied_admin_audit_logs():
    _assert_staff_forbidden("GET", "/api/v1/admin/audit-logs")


def test_staff_cannot_read_student_resources():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/resources")


def test_retired_student_crud_is_unavailable():
    with _patch_staff_auth():
        response = client.get(f"/api/v1/admin/students/{STUDENT_A}", headers=AUTH_HEADERS)
    assert response.status_code == 404
