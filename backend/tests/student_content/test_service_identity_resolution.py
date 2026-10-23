from .support import (
    STUDENT_ID,
    TENANT_A,
    TENANT_B,
    _clear_dependency_overrides,
    _db_for_student,
    _notice_row,
    _student_user,
    dashboard_repo,
    notices_service,
    patch,
    pytest,
    resources_service,
)


class TestServiceIdentityResolution:
    def test_notices_use_the_authenticated_students_own_institution(self):
        db = _db_for_student(institution_id=TENANT_A)
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with patch.object(
                dashboard_repo, "list_published_notices", return_value=[_notice_row()]
            ) as repo:
                result = notices_service.get_own_notices(_student_user(), client=db)
        assert repo.call_args[0][1] == TENANT_A
        assert result.total == 1

    def test_resources_use_the_authenticated_students_own_institution(self):
        db = _db_for_student(institution_id=TENANT_B)
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with patch.object(
                dashboard_repo, "list_published_resources", return_value=[]
            ) as repo:
                result = resources_service.get_own_resources(
                    _student_user(tenant=TENANT_B), client=db
                )
        assert repo.call_args[0][1] == TENANT_B
        assert result.total == 0

    def test_services_expose_no_identity_parameter(self):
        """A client cannot pass an institution/student id at all."""
        with pytest.raises(TypeError):
            notices_service.get_own_notices(_student_user(), institution_id=TENANT_B)
        with pytest.raises(TypeError):
            resources_service.get_own_resources(_student_user(), student_id=STUDENT_ID)
