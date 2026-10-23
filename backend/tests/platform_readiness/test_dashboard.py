from .support import (
    AUTH_HEADERS,
    TENANT_A,
    _active_institution_authorization,
    _auth,
    _envelope,
    client,
)


def test_student_cannot_reach_admin_dashboard():
    with _auth("student", TENANT_A):
        r = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert r.status_code == 403
    assert _envelope(r)["code"] == "FORBIDDEN"
