from .support import (
    _db_with_notifications,
    _db_with_student_profile,
    _student_user,
    app,
    cleanup,
    client,
    get_current_user,
    patch,
)


class TestPaginationEdgeCases:
    """Pagination validation follows the existing conventions."""

    def test_invalid_page_rejected(self):
        """Page < 1 is rejected by FastAPI validation (422)."""
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
                response = client.get("/api/v1/students/me/notifications?page=0")
        assert response.status_code == 422

    def test_invalid_page_size_rejected(self):
        """Page size > 100 is rejected by FastAPI validation (422)."""
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
                response = client.get("/api/v1/students/me/notifications?page_size=101")
        assert response.status_code == 422
