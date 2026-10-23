from .support import (
    _approved_student_profile,
    _db_with_student_profile,
    _student_user,
    app,
    cleanup,
    client,
    get_current_user,
    patch,
)


class TestAuthAndEligibility:
    """4. Unauthenticated access is blocked.
    5. Ineligible/unapproved student is blocked."""

    def test_unauthenticated_access_blocked(self):
        """4. Unauthenticated access is blocked (401 AUTH_REQUIRED)."""
        app.dependency_overrides.pop(get_current_user, None)
        response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_unapproved_student_blocked(self):
        """5. Unapproved student is blocked (403 STUDENT_NOT_APPROVED)."""
        profile = _approved_student_profile()
        profile["approval_status"] = "pending"
        db = _db_with_student_profile(profile)
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "STUDENT_NOT_APPROVED"

    def test_inactive_student_blocked(self):
        """5. Inactive student is blocked (403 STUDENT_INACTIVE)."""
        profile = _approved_student_profile()
        profile["is_active"] = False
        db = _db_with_student_profile(profile)
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "STUDENT_INACTIVE"
