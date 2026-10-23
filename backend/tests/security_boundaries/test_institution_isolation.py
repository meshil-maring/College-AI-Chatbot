from .database import (
    _FakeClient,
)
from .state import (
    _base_state,
)
from .support import (
    AppError,
    INST_A1,
    INST_A2,
    INST_B1,
    JR_A,
    KS_FAQ_B1,
    MagicMock,
    ORG_A,
    STUDENT_ID_A1,
    USER_FACULTY_A1,
    USER_INST_A1,
    USER_ORG_A,
    USER_STAFF_A1,
    USER_STUDENT_A1,
    UUID,
    _active_institution_authorization,
    _as,
    _clear,
    _resolve,
    _role_row,
    _user,
    authz,
    client,
    patch,
    pytest,
    tenancy_repo,
    tenancy_svc,
)


class TestInstitutionIsolation:
    def test_student_a_cannot_read_institution_b_profile_row(self):
        student = _user(INST_A1, roles=("student",), user_id=USER_STUDENT_A1)
        foreign_profile = {
            "student_id": STUDENT_ID_A1,
            "user_id": student["user_id"],
            "institution_id": INST_B1,
        }
        db = MagicMock()
        (
            db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
        ).return_value = MagicMock(data=foreign_profile)
        _as(student)
        try:
            with patch(
                "app.services.students.student_data.get_admin_client", return_value=db
            ):
                resp = client.get("/api/v1/students/me/profile")
        finally:
            _clear()
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"

    def test_student_a_reads_own_institution_a_profile(self):
        student = _user(INST_A1, roles=("student",), user_id=USER_STUDENT_A1)
        own_profile = {
            "student_id": STUDENT_ID_A1,
            "user_id": student["user_id"],
            "institution_id": INST_A1,
        }
        db = MagicMock()
        (
            db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
        ).return_value = MagicMock(data=own_profile)
        _as(student)
        try:
            with patch(
                "app.services.students.student_data.get_admin_client", return_value=db
            ):
                resp = client.get("/api/v1/students/me/profile")
        finally:
            _clear()
        assert resp.status_code == 200
        assert "institution_id" not in resp.json()

    def test_faculty_a_cannot_ingest_for_institution_b(self):
        faculty = _user(INST_A1, roles=("faculty",), user_id=USER_FACULTY_A1)
        _as(faculty)
        try:
            with (
                patch(
                    "app.api.knowledge.ingestion.get_admin_client",
                    return_value=MagicMock(),
                ),
                patch(
                    "app.api.knowledge.ingestion.get_knowledge_source",
                    return_value={
                        "knowledge_source_id": KS_FAQ_B1,
                        "institution_id": INST_B1,
                    },
                ),
                patch("app.api.knowledge.ingestion.ingest_document") as ingest,
            ):
                resp = client.post(
                    "/api/v1/documents/ingest",
                    files={"file": ("doc.txt", b"hello", "text/plain")},
                    data={"knowledge_source_id": KS_FAQ_B1},
                )
        finally:
            _clear()
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        ingest.assert_not_called()

    def test_staff_a_cannot_read_institution_b_approval_queue(self):
        staff = _user(INST_A1, roles=("staff",), user_id=USER_STAFF_A1)
        _as(staff)
        try:
            with patch(
                "app.services.admin.admin_academics.list_pending_approvals"
            ) as svc:
                resp = client.get(
                    f"/api/v1/admin/students/pending?institution_id={INST_B1}"
                )
        finally:
            _clear()
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        svc.assert_not_called()

    def test_institution_admin_a_cannot_manage_institution_b(self):
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_institution(
                _user(user_id=USER_INST_A1), ctx, INST_B1
            )
        assert exc.value.status_code == 403
        assert exc.value.code == "TENANT_MISMATCH"

    def test_institution_admin_a_cannot_manage_its_organization(self):
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_organization(
                _user(user_id=USER_INST_A1), ctx, ORG_A
            )
        assert exc.value.code == "FORBIDDEN"

    def test_institution_admin_a_cannot_decide_org_b_join_request(self):
        from app.schemas.platform.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["institution_join_requests"] = [
            {
                "join_request_id": JR_A,
                "organization_id": ORG_A,
                "institution_id": INST_A1,
                "status": "pending",
            }
        ]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_join_request(
                    _user(INST_A1, user_id=USER_INST_A1),
                    ctx,
                    JR_A,
                    ApprovalDecisionRequest(decision="approve"),
                )
        # An institution-scoped user can never decide a join request.
        assert exc.value.status_code == 403
        assert state["institution_join_requests"][0]["status"] == "pending"

    def test_org_admin_scope_reaches_both_institutions_of_org_a(self):
        """Organization-scoped admin manages all of its own institutions."""
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ):
            authz.assert_can_manage_institution(_user(user_id=USER_ORG_A), ctx, INST_A1)
            authz.assert_can_manage_institution(_user(user_id=USER_ORG_A), ctx, INST_A2)
