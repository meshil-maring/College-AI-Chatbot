from .support import (
    NOTIFICATION_ID,
    _db_with_notification_row,
    _db_with_student_profile,
    _notification_row,
    _student_user,
    app,
    cleanup,
    client,
    get_current_user,
    patch,
)


class TestReadStateMutation:
    """6. Student can mark own notification as read.
    8. Student cannot modify notification content."""

    def test_can_mark_own_notification_read(self):
        """6. Student can mark their own notification as read."""
        db = _db_with_notification_row(_notification_row(is_read=False))
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
                    f"/api/v1/students/me/notifications/{NOTIFICATION_ID}/read"
                )
        assert response.status_code == 200
        body = response.json()
        assert body["is_read"] is True
        assert body["read_at"] is not None
        assert body["notification_id"] == NOTIFICATION_ID
        assert body["title"] == "Test notification"
        assert body["message"] == "Test message"

    def test_cannot_modify_notification_content(self):
        """8. Student cannot modify notification content via read endpoint."""
        db = _db_with_notification_row(
            _notification_row(title="Original title", message="Original message")
        )
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
                    json={"title": "Hacked title", "message": "Hacked message"},
                )
        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Original title"
        assert body["message"] == "Original message"

    def test_mark_read_returns_404_for_nonexistent(self):
        """Marking a nonexistent notification returns 404."""
        db = _db_with_notification_row(None)
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
                    f"/api/v1/students/me/notifications/{NOTIFICATION_ID}/read"
                )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"
