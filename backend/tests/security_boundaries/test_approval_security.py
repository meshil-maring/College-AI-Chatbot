from .database import (
    _FakeClient,
)
from .state import (
    _base_state,
    _org_row,
)
from .support import (
    AppError,
    INST_A1,
    JR_A,
    ORG_A,
    ORG_B,
    USER_INST_A1,
    USER_ORG_A,
    USER_PLATFORM,
    _active_institution_authorization,
    _resolve,
    _role_row,
    _user,
    authz,
    patch,
    pytest,
    tenancy_repo,
    tenancy_svc,
)


class TestApprovalSecurity:
    def test_only_platform_authority_can_approve_organization(self):
        for scope_type, scope_id in (
            (authz.ORGANIZATION, ORG_A),
            (authz.INSTITUTION, INST_A1),
        ):
            ctx = _resolve([_role_row(scope_type, scope_id, ORG_A)])
            with pytest.raises(AppError) as exc:
                authz._assert_platform_authority(ctx)
            assert exc.value.status_code == 403
            assert exc.value.code == "FORBIDDEN"
        # Platform scope is the only accepted authority.
        authz._assert_platform_authority(
            _resolve([_role_row(authz.PLATFORM, None, None)])
        )

    def test_organization_admin_cannot_self_approve_own_organization(self):
        from app.schemas.platform.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["organizations"] = [_org_row(ORG_A, "pending")]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_organization(
                    _user(user_id=USER_ORG_A),
                    ctx,
                    ORG_A,
                    ApprovalDecisionRequest(decision="approve"),
                )
        assert exc.value.status_code == 403
        assert exc.value.code == "FORBIDDEN"
        # The organization is still pending — no self-activation happened.
        assert state["organizations"][0]["status"] == "pending"

    def test_platform_admin_can_approve_pending_organization(self):
        from app.schemas.platform.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["organizations"] = [_org_row(ORG_A, "pending")]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.PLATFORM, None, None)])
        with (
            patch.object(tenancy_svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo, "update_join_requests_for_organization", return_value=[]
            ),
        ):
            response = tenancy_svc.decide_organization(
                _user(user_id=USER_PLATFORM),
                ctx,
                ORG_A,
                ApprovalDecisionRequest(decision="approve"),
            )
        assert response.status == "approve"
        assert state["organizations"][0]["status"] == "active"

    def test_institution_admin_cannot_approve_join_request(self):
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
        assert exc.value.status_code == 403
        assert state["institution_join_requests"][0]["status"] == "pending"

    def test_org_admin_can_decide_own_join_request(self):
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
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            response = tenancy_svc.decide_join_request(
                _user(user_id=USER_ORG_A),
                ctx,
                JR_A,
                ApprovalDecisionRequest(decision="approve"),
            )
        assert response.status == "approve"
        assert state["institution_join_requests"][0]["status"] == "approved"
        institution = state["institutions"][0]
        assert institution["institution_id"] == INST_A1
        assert institution["status"] == "active"
        assert institution["is_active"] is True

    def test_repeated_join_request_decision_is_safe(self):
        from app.schemas.platform.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["institution_join_requests"] = [
            {
                "join_request_id": JR_A,
                "organization_id": ORG_A,
                "institution_id": INST_A1,
                "status": "approved",
            }
        ]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_join_request(
                    _user(user_id=USER_ORG_A),
                    ctx,
                    JR_A,
                    ApprovalDecisionRequest(decision="approve"),
                )
        assert exc.value.status_code == 422
        assert exc.value.code == "JOIN_REQUEST_NOT_PENDING"
        assert state["institution_join_requests"][0]["status"] == "approved"

    def test_repeated_organization_decision_is_safe(self):
        from app.schemas.platform.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["organizations"] = [_org_row(ORG_A, "active")]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.PLATFORM, None, None)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_organization(
                    _user(user_id=USER_PLATFORM),
                    ctx,
                    ORG_A,
                    ApprovalDecisionRequest(decision="reject"),
                )
        assert exc.value.status_code == 422
        assert exc.value.code == "ORGANIZATION_NOT_PENDING"
        assert state["organizations"][0]["status"] == "active"

    def test_rejected_organization_cannot_accept_institution_requests(self):
        from app.schemas.platform.tenancy import InstitutionRegistrationRequest
        from app.services.platform import tenancy as svc

        payload = InstitutionRegistrationRequest(
            name="New Campus",
            institution_code="NEWCAMP",
            organization_code="BETA",
            official_email="info@newcamp.example.com",
            admin_email="admin@newcamp.example.com",
            admin_password="secret123",
            admin_first_name="Inst",
            admin_last_name="Admin",
        )
        fake = _FakeClient({})
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_organization_by_code",
                return_value=_org_row(ORG_B, "rejected"),
            ),
        ):
            with pytest.raises(AppError) as exc:
                svc.register_institution(payload)
        assert exc.value.status_code == 403
        assert exc.value.code == "ORGANIZATION_NOT_ACCEPTING_REQUESTS"

    def test_pending_organization_admin_denied_platform_only_authority(self):
        """A pending org's admin keeps management but never approval authority."""
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz._assert_platform_authority(ctx)
        assert exc.value.code == "FORBIDDEN"
