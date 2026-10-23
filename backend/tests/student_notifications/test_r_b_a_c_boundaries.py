from .support import (
    NOTIFICATION_ID,
    _db_with_notification_row,
    _db_with_student_profile,
    _db_without_profile,
    _student_user,
    app,
    cleanup,
    client,
    get_current_user,
    patch,
)


class TestRBACBoundaries:
    """17. RBAC boundaries remain correct."""

    def test_student_cannot_create_notification_via_api(self):
        """Students have no API endpoint to create arbitrary notifications."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.post("/api/v1/students/me/notifications", json={})
        assert response.status_code == 405

    def test_student_cannot_modify_notification_type(self):
        """The read endpoint accepts no payload and cannot change the type."""
        db = _db_with_notification_row()
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch(
            "app.services.students.student_context.get_admin_client",
            return_value=_db_with_student_profile(),
        ):
            with patch(
                "app.services.students.student_notifications.get_admin_client",
                return_value=db,
            ):
                response = client.patch(
                    f"/api/v1/students/me/notifications/{NOTIFICATION_ID}/read",
                    json={"notification_type": "academic_status"},
                )
        assert response.status_code == 200
        assert response.json()["notification_type"] == "academic_admin"

    def test_non_student_cannot_access_notifications(self):
        """A non-student account has no student context -> 404."""
        admin_user = _student_user()
        admin_user["roles"] = ["admin"]
        app.dependency_overrides[get_current_user] = lambda: admin_user
        with patch(
            "app.services.students.student_context.get_admin_client",
            return_value=_db_without_profile(),
        ):
            response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"
