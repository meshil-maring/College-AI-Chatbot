from .support import (
    STUDENT_ID,
    STUDENT_USER_ID,
    TENANT_A,
    TENANT_B,
    _clear_dependency_overrides,
    _db_for_student,
    _notice_row,
    _resource_row,
    _student_user,
    app,
    client,
    dashboard_repo,
    get_current_user,
    patch,
)


class TestStudentDashboardEndpoints:
    def test_notices_require_authentication(self):
        response = client.get("/api/v1/students/me/notices")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_resources_require_authentication(self):
        response = client.get("/api/v1/students/me/resources")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_notices_return_only_the_authenticated_students_institution(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student(institution_id=TENANT_A)
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with patch.object(
                dashboard_repo,
                "list_published_notices",
                return_value=[_notice_row(institution_id=TENANT_A)],
            ):
                response = client.get("/api/v1/students/me/notices")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Exam schedule update"

    def test_resources_return_only_the_authenticated_students_institution(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student(institution_id=TENANT_A)
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with patch.object(
                dashboard_repo,
                "list_published_resources",
                return_value=[_resource_row(institution_id=TENANT_A)],
            ):
                response = client.get("/api/v1/students/me/resources")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Student Handbook"

    def test_client_supplied_institution_cannot_widen_the_scope(self):
        """A smuggled institution_id query value is ignored, not honoured."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student(institution_id=TENANT_A)
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with patch.object(
                dashboard_repo, "list_published_notices", return_value=[]
            ) as repo:
                response = client.get(
                    f"/api/v1/students/me/notices?institution_id={TENANT_B}"
                    f"&student_id={STUDENT_ID}&user_id={STUDENT_USER_ID}"
                )
        assert response.status_code == 200
        # The ONLY tenant ever queried is the authenticated student's own.
        assert repo.call_args[0][1] == TENANT_A

    def test_out_of_range_limit_is_rejected_by_the_api(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        assert client.get("/api/v1/students/me/notices?limit=1000").status_code == 422
        assert client.get("/api/v1/students/me/resources?limit=0").status_code == 422

    def test_empty_institution_returns_an_empty_list_not_an_error(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student()
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with patch.object(
                dashboard_repo, "list_published_notices", return_value=[]
            ):
                with patch.object(
                    dashboard_repo, "list_published_resources", return_value=[]
                ):
                    notices = client.get("/api/v1/students/me/notices")
                    resources = client.get("/api/v1/students/me/resources")
        assert notices.status_code == 200
        assert notices.json() == {"items": [], "total": 0}
        assert resources.status_code == 200
        assert resources.json() == {"items": [], "total": 0}

    def test_responses_never_leak_storage_keys_tokens_or_internal_ids(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student()
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            with patch.object(
                dashboard_repo,
                "list_published_resources",
                return_value=[_resource_row()],
            ):
                payload = client.get("/api/v1/students/me/resources").text
        for forbidden in (
            "storage_object_key",
            "storage_bucket",
            "file_checksum",
            "created_by_user_id",
            "institution_id",
            "student_id",
            "Bearer",
        ):
            assert forbidden not in payload

    def test_unapproved_student_gets_403_not_data(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student(approval_status="pending")
        with patch(
            "app.services.students.student_context.get_admin_client", return_value=db
        ):
            response = client.get("/api/v1/students/me/notices")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "STUDENT_NOT_APPROVED"
