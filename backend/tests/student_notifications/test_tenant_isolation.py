from .support import (
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


class TestTenantIsolation:
    """16. Tenant database protections work."""

    def test_notification_institution_id_is_tenant_scoped(self):
        """Notification institution_id is derived from the authoritative tenant."""
        db = _db_with_notification_row(_notification_row(institution_id=TENANT_A))
        app.dependency_overrides[get_current_user] = lambda: _student_user(
            tenant=TENANT_A
        )
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
        assert item["institution_id"] == TENANT_A
