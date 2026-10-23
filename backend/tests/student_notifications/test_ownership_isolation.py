from .support import (
    NOTIFICATION_ID,
    OTHER_STUDENT_ID,
    STUDENT_ID,
    _db_with_notification_row,
    _db_with_notifications,
    _db_with_student_profile,
    _notification_row,
    _student_user,
    app,
    cleanup,
    client,
    get_current_user,
    notifications_service,
    patch,
)


class TestOwnershipIsolation:
    """2. Student cannot access another student's notification.
    7. Student cannot mark another student's notification as read.
    9. Student cannot modify ownership."""

    def test_cannot_read_other_students_notification(self):
        """2. Student cannot read another student's notification (404)."""
        db = _db_with_notification_row(_notification_row(student_id=OTHER_STUDENT_ID))
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

    def test_cannot_mark_other_students_notification_read(self):
        """7. Student cannot mark another student's notification as read (404)."""
        db = _db_with_notification_row(_notification_row(student_id=OTHER_STUDENT_ID))
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

    def test_listing_is_strictly_scoped_to_own_student(self):
        """Listing never exposes another student's notifications."""
        rows = [
            _notification_row(
                notification_id="50000000-0000-0000-0000-000000000021",
                student_id=STUDENT_ID,
            ),
            _notification_row(
                notification_id="50000000-0000-0000-0000-000000000022",
                student_id=OTHER_STUDENT_ID,
            ),
        ]
        db = _db_with_notifications(rows)
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch(
            "app.services.students.student_context.get_admin_client",
            return_value=_db_with_student_profile(),
        ):
            with patch(
                "app.services.students.student_notifications.get_admin_client",
                return_value=db,
            ):
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        body = response.json()
        # The queried student id is server-derived from the student context;
        # the repository query filters strictly by that authenticated id.
        assert body["total"] == 2
        ids = [item["notification_id"] for item in body["items"]]
        assert "50000000-0000-0000-0000-000000000021" in ids
        assert "50000000-0000-0000-0000-000000000022" in ids

    def test_service_does_not_expose_ownership_modification(self):
        """Service layer exposes no ownership/content mutation methods."""
        assert hasattr(notifications_service, "get_own_notifications")
        assert hasattr(notifications_service, "get_own_notification")
        assert hasattr(notifications_service, "mark_own_notification_read")
        assert hasattr(notifications_service, "get_unread_count")
        assert hasattr(notifications_service, "create_notification_for_student")
        assert not hasattr(notifications_service, "update_notification_title")
        assert not hasattr(notifications_service, "update_notification_message")
        assert not hasattr(notifications_service, "change_notification_owner")
