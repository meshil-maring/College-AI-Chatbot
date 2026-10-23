from .support import (
    AppError,
    NOTIFICATION_ID,
    OTHER_STUDENT_ID,
    STUDENT_ID,
    TENANT_A,
    _db_with_notification_row,
    _notification_row,
    cleanup,
    notifications_service,
    pytest,
)


class TestServiceLayerOwnership:
    """Service-layer ownership checks enforced independently of the API."""

    def test_get_own_notification_requires_ownership(self):
        """Service get_own_notification raises 404 for another student's row."""
        db = _db_with_notification_row(_notification_row(student_id=OTHER_STUDENT_ID))
        with pytest.raises(AppError) as exc_info:
            notifications_service.get_own_notification(
                current_student_id=STUDENT_ID,
                notification_id=NOTIFICATION_ID,
                client=db,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "NOTIFICATION_NOT_FOUND"

    def test_mark_read_service_requires_ownership(self):
        """Service mark_own_notification_read raises 404 for another student."""
        db = _db_with_notification_row(_notification_row(student_id=OTHER_STUDENT_ID))
        with pytest.raises(AppError) as exc_info:
            notifications_service.mark_own_notification_read(
                current_student_id=STUDENT_ID,
                notification_id=NOTIFICATION_ID,
                client=db,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "NOTIFICATION_NOT_FOUND"

    def test_create_notification_carries_server_derived_ownership(self):
        """create_notification_for_student persists the provider-supplied ownership."""
        db = _db_with_notification_row()
        result = notifications_service.create_notification_for_student(
            student_id=STUDENT_ID,
            institution_id=TENANT_A,
            notification_type="academic_admin",
            title="Test",
            message="Test",
            client=db,
        )
        assert result["student_id"] == STUDENT_ID
        assert result["institution_id"] == TENANT_A
