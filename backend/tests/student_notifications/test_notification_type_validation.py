from .support import (
    AppError,
    MagicMock,
    NOTIFICATION_TYPES,
    STUDENT_ID,
    TENANT_A,
    cleanup,
    notifications_service,
    pytest,
)


class TestNotificationTypeValidation:
    """10. Invalid notification type is rejected."""

    def test_create_rejects_invalid_notification_type(self):
        """10. Invalid notification type is rejected (422)."""
        with pytest.raises(AppError) as exc_info:
            notifications_service.create_notification_for_student(
                student_id=STUDENT_ID,
                institution_id=TENANT_A,
                notification_type="invalid_type",
                title="Test",
                message="Test",
                client=MagicMock(),
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "INVALID_NOTIFICATION_TYPE"

    def test_create_accepts_only_controlled_vocabulary(self):
        """Only the controlled vocabulary of notification types is accepted."""
        expected = {
            "attendance_alert",
            "result_published",
            "academic_status",
            "academic_admin",
        }
        assert set(NOTIFICATION_TYPES) == expected
        assert len(NOTIFICATION_TYPES) == 4
