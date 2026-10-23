from .support import (
    NOTIFICATION_ID,
    NOTIFICATION_TYPES,
    STUDENT_ID,
    TENANT_A,
    _notification_row,
    cleanup,
)


class TestRegressionSmoke:
    """Quick smoke tests that the notification modules are coherent."""

    def test_imports_work(self):
        """All notification modules import without error."""
        from app.schemas.students.student_notifications import (
            Notification,
            NotificationListResponse,
        )  # noqa: F401
        from app.repositories.students.student_notifications import (
            get_notification,
            list_notifications,
            create_notification,
            mark_notification_read,
        )  # noqa: F401
        from app.services.students.student_notifications import (
            get_own_notifications,
            get_own_notification,
            mark_own_notification_read,
            create_notification_for_student,
            get_unread_count,
        )  # noqa: F401

        assert True

    def test_schema_validates_correct_data(self):
        """Notification schema validates correct data and rejects foreign fields."""
        from app.schemas.students.student_notifications import (
            Notification,
            NotificationCreate,
        )

        row = _notification_row()
        notification = Notification(**row)
        assert str(notification.notification_id) == NOTIFICATION_ID
        assert str(notification.student_id) == STUDENT_ID
        assert notification.notification_type == "academic_admin"

        payload = NotificationCreate(
            student_id=STUDENT_ID,
            institution_id=TENANT_A,
            notification_type="academic_admin",
            title="Test",
            message="Test",
        )
        assert payload.notification_type == "academic_admin"

        import pytest as _pytest

        with _pytest.raises(Exception):
            NotificationCreate(
                student_id=STUDENT_ID,
                institution_id=TENANT_A,
                notification_type="arbitrary_free_text",
                title="Test",
                message="Test",
            )

    def test_notification_types_controlled_vocabulary(self):
        """Notification types stay a controlled, closed vocabulary."""
        expected = {
            "attendance_alert",
            "result_published",
            "academic_status",
            "academic_admin",
        }
        assert set(NOTIFICATION_TYPES) == expected
        assert len(NOTIFICATION_TYPES) == 4
