from .support import (
    AppError,
    MagicMock,
    _clear_dependency_overrides,
    _db_for_student,
    _student_user,
    dashboard_repo,
    notices_service,
    patch,
    pytest,
    resources_service,
)


class TestServiceEligibilityAndEdges:
    def test_missing_user_id_is_rejected(self):
        with pytest.raises(AppError) as exc:
            notices_service.get_own_notices({}, client=MagicMock())
        assert exc.value.status_code == 400
        assert exc.value.code == "INVALID_USER_CONTEXT"

    def test_student_without_profile_is_404(self):
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value
        chain.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with pytest.raises(AppError) as exc:
                resources_service.get_own_resources(_student_user(), client=db)
        assert exc.value.status_code == 404
        assert exc.value.code == "STUDENT_PROFILE_NOT_FOUND"

    def test_unapproved_student_is_rejected(self):
        db = _db_for_student(approval_status="pending")
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with pytest.raises(AppError) as exc:
                notices_service.get_own_notices(_student_user(), client=db)
        assert exc.value.status_code == 403
        assert exc.value.code == "STUDENT_NOT_APPROVED"

    def test_inactive_student_is_rejected(self):
        db = _db_for_student(is_active=False)
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with pytest.raises(AppError) as exc:
                resources_service.get_own_resources(_student_user(), client=db)
        assert exc.value.status_code == 403
        assert exc.value.code == "STUDENT_INACTIVE"

    def test_student_without_a_tenant_fails_closed(self):
        db = _db_for_student(institution_id=None)
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with pytest.raises(AppError) as exc:
                notices_service.get_own_notices(_student_user(tenant=None), client=db)
        assert exc.value.status_code == 403
        assert exc.value.code == "TENANT_MISMATCH"

    def test_empty_data_is_an_empty_list_not_an_error(self):
        db = _db_for_student()
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with patch.object(
                dashboard_repo, "list_published_notices", return_value=[]
            ):
                notices = notices_service.get_own_notices(_student_user(), client=db)
            with patch.object(
                dashboard_repo, "list_published_resources", return_value=[]
            ):
                resources = resources_service.get_own_resources(
                    _student_user(), client=db
                )
        assert notices.items == [] and notices.total == 0
        assert resources.items == [] and resources.total == 0

    @pytest.mark.parametrize("limit", [0, -1, 21])
    def test_notice_limit_out_of_range_is_422(self, limit):
        with pytest.raises(AppError) as exc:
            notices_service.get_own_notices(
                _student_user(), limit=limit, client=MagicMock()
            )
        assert exc.value.status_code == 422
        assert exc.value.code == "INVALID_FILTER"

    @pytest.mark.parametrize("limit", [0, 51])
    def test_resource_limit_out_of_range_is_422(self, limit):
        with pytest.raises(AppError) as exc:
            resources_service.get_own_resources(
                _student_user(), limit=limit, client=MagicMock()
            )
        assert exc.value.status_code == 422
        assert exc.value.code == "INVALID_FILTER"
