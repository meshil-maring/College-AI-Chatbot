from .support import (
    MagicMock,
    NOTIFICATION_ID,
    SOURCE_RECORD_ID,
    STUDENT_ID,
    TENANT_A,
    _db_with_notification_row,
    _db_with_notifications,
    _db_with_student_profile,
    _notification_row,
    _student_user,
    app,
    cleanup,
    client,
    get_current_user,
    patch,
)


class TestNotificationListing:
    """1. Student can list own notifications."""

    def test_lists_own_notifications(self):
        """1. Authenticated student can list their own notifications."""
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
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert body["has_more"] is False
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["notification_id"] == NOTIFICATION_ID
        assert item["student_id"] == STUDENT_ID
        assert item["institution_id"] == TENANT_A
        assert item["notification_type"] == "academic_admin"
        assert item["title"] == "Test notification"
        assert item["message"] == "Test message"
        assert item["is_read"] is False
        assert item["source_type"] == "academic_event"

    def test_pagination_is_deterministic(self):
        """11. Pagination/order is deterministic (newest first)."""
        rows = [
            _notification_row(
                notification_id="50000000-0000-0000-0000-000000000011",
                created_at="2026-09-14T12:00:00+00:00",
            ),
            _notification_row(
                notification_id="50000000-0000-0000-0000-000000000010",
                created_at="2026-09-14T11:00:00+00:00",
            ),
            _notification_row(
                notification_id="50000000-0000-0000-0000-000000000009",
                created_at="2026-09-14T10:00:00+00:00",
            ),
        ]
        captured = {}

        def fake_list(client, student_id, limit=50, offset=0):
            captured["student_id"] = str(student_id)
            captured["limit"] = limit
            captured["offset"] = offset
            return rows[offset : offset + limit]

        def fake_count(client, student_id):
            return len(rows)

        db = MagicMock()
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch(
            "app.services.students.student_context.get_admin_client",
            return_value=_db_with_student_profile(),
        ):
            with patch(
                "app.services.students.student_notifications.get_admin_client",
                return_value=db,
            ):
                with patch(
                    "app.repositories.students.student_notifications.list_notifications",
                    side_effect=fake_list,
                ):
                    with patch(
                        "app.repositories.students.student_notifications.count_notifications_by_student",
                        side_effect=fake_count,
                    ):
                        response = client.get(
                            "/api/v1/students/me/notifications?page=1&page_size=2"
                        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert body["has_more"] is True
        assert len(body["items"]) == 2
        assert captured["student_id"] == STUDENT_ID
        assert captured["limit"] == 2
        assert captured["offset"] == 0
        assert (
            body["items"][0]["notification_id"]
            == "50000000-0000-0000-0000-000000000011"
        )
        assert (
            body["items"][1]["notification_id"]
            == "50000000-0000-0000-0000-000000000010"
        )

    def test_read_unread_state_is_correct(self):
        """12. Read/unread state is correct."""
        db = _db_with_notification_row(
            _notification_row(is_read=True, read_at="2026-09-14T11:00:00+00:00")
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
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["is_read"] is True
        assert item["read_at"] is not None

    def test_notification_type_category_present(self):
        """Notification type/category is present in the response."""
        db = _db_with_notification_row(
            _notification_row(notification_type="attendance_alert")
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
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["notification_type"] == "attendance_alert"

    def test_source_reference_is_optional_and_supported(self):
        """Optional reference to the authoritative source record is exposed."""
        db = _db_with_notification_row(
            _notification_row(source_record_id=SOURCE_RECORD_ID)
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
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["source_record_id"] == SOURCE_RECORD_ID

    def test_empty_notification_list(self):
        """Student with no notifications gets a deterministic empty page."""
        db = _db_with_notifications([])
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
        assert body["total"] == 0
        assert body["items"] == []
        assert body["has_more"] is False
