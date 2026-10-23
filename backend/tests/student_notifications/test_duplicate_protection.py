from .support import (
    AppError,
    MagicMock,
    NOTIFICATION_ID,
    SOURCE_RECORD_ID,
    STUDENT_ID,
    TENANT_A,
    _db_with_notification_row,
    cleanup,
    notifications_service,
)


class TestDuplicateProtection:
    """13. Duplicate academic event notification is prevented."""

    def test_duplicate_source_record_maps_to_conflict(self):
        """13. Duplicate event notification maps to 409 NOTIFICATION_DUPLICATE."""
        db = MagicMock()
        db.table.return_value.insert.return_value.select.return_value.single.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
        result = notifications_service.create_notification_for_student(
            student_id=STUDENT_ID,
            institution_id=TENANT_A,
            notification_type="result_published",
            title="Test",
            message="Test",
            source_record_id=SOURCE_RECORD_ID,
            client=db,
        )
        assert isinstance(result, AppError)
        assert result.status_code == 409
        assert result.code == "NOTIFICATION_DUPLICATE"

    def test_create_without_source_record_is_allowed(self):
        """Notifications without a source record can be created (no dup key)."""
        db = _db_with_notification_row()
        result = notifications_service.create_notification_for_student(
            student_id=STUDENT_ID,
            institution_id=TENANT_A,
            notification_type="academic_admin",
            title="Test",
            message="Test",
            source_record_id=None,
            client=db,
        )
        assert result["notification_id"] == NOTIFICATION_ID
        assert result["student_id"] == STUDENT_ID
        assert result["institution_id"] == TENANT_A
