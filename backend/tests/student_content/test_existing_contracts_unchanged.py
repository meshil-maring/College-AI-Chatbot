from .support import (
    AppError,
    _clear_dependency_overrides,
    _student_user,
    pytest,
)


class TestExistingContractsUnchanged:
    def test_the_admin_notice_boundary_still_rejects_students(self):
        import asyncio

        from app.core.security import require_roles

        with pytest.raises(AppError) as exc:
            asyncio.run(require_roles("admin")(current_user=_student_user()))
        assert exc.value.status_code == 403

    def test_the_admin_notice_boundary_still_admits_admins(self):
        import asyncio

        from app.core.security import require_roles

        admin = {
            "user_id": "1",
            "auth_user_id": "2",
            "email": None,
            "roles": ["admin"],
            "institution_id": None,
        }
        assert asyncio.run(require_roles("admin")(current_user=admin)) is admin
