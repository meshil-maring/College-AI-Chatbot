from .support import (
    NOTIFICATION_ID,
    STUDENT_ID,
    TENANT_A,
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


class TestSingleNotificationEndpoint:
    """GET /api/v1/students/me/notifications/{id}"""

    def test_get_own_notification(self):
        """Student can retrieve one of their own notifications by id."""
        db = _db_with_notification_row(_notification_row(student_id=STUDENT_ID))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch(
            "app.services.students.student_context.get_admin_client",
            return_value=_db_with_student_profile(),
        ):
            with patch(
                "app.services.students.student_notifications.get_admin_client",
                return_value=db,
            ):
                response = client.get(
                    f"/api/v1/students/me/notifications/{NOTIFICATION_ID}"
                )
        assert response.status_code == 200
        body = response.json()
        assert body["notification_id"] == NOTIFICATION_ID
        assert body["student_id"] == STUDENT_ID
        assert body["institution_id"] == TENANT_A

    def test_get_nonexistent_notification_returns_404(self):
        """Nonexistent notification returns 404 NOTIFICATION_NOT_FOUND."""
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
                response = client.get(
                    f"/api/v1/students/me/notifications/{NOTIFICATION_ID}"
                )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"


from .support import (
    MagicMock,
    _db_with_student_profile,
    _student_user,
    app,
    cleanup,
    client,
    get_current_user,
    patch,
)


class TestUnreadCountEndpoint:
    """GET /api/v1/students/me/notifications/unread-count"""

    def test_unread_count_returns_correct_count(self):
        """Unread count is scoped to the authenticated student."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch(
            "app.services.students.student_context.get_admin_client",
            return_value=_db_with_student_profile(),
        ):
            with patch(
                "app.services.students.student_notifications.get_admin_client",
                return_value=MagicMock(),
            ):
                with patch(
                    "app.repositories.students.student_notifications.count_unread_by_student",
                    return_value=3,
                ):
                    response = client.get(
                        "/api/v1/students/me/notifications/unread-count"
                    )
        assert response.status_code == 200
        assert response.json()["unread_count"] == 3

    def test_unread_count_requires_authentication(self):
        """Unauthenticated unread-count request is blocked (401)."""
        app.dependency_overrides.pop(get_current_user, None)
        response = client.get("/api/v1/students/me/notifications/unread-count")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"
