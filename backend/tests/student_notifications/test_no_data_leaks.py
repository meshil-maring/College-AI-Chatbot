from .support import (
    _approved_student_profile,
    _student_user,
    app,
    cleanup,
    client,
    get_current_user,
    patch,
)


class TestNoDataLeaks:
    """18. No notification data leaks through unrelated endpoints."""

    def test_notifications_not_in_profile_response(self):
        """Notification data is not embedded in the profile endpoint."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch(
            "app.services.students.student_data.get_own_profile",
            return_value={"email": "student@example.test", "approval_status": "approved"},
        ):
            response = client.get("/api/v1/students/me/profile")
        assert response.status_code == 200
        body = response.json()
        assert "notifications" not in body
        assert "notification_id" not in body

    def test_retired_results_route_does_not_expose_notifications(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.get("/api/v1/students/me/results")
        assert response.status_code == 404
        assert "notifications" not in response.json()

    def test_retired_attendance_route_does_not_expose_notifications(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.get("/api/v1/students/me/attendance")
        assert response.status_code == 404
        assert "notifications" not in response.json()
