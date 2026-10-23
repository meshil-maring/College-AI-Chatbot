from .chat_helpers import (
    _chat_request,
    _retrieved_chunk,
    _run_public_chat,
)
from .database import (
    _FakeClient,
)
from .state import (
    _base_state,
)
from .support import (
    AppError,
    CHUNK_FAQ_A1,
    CHUNK_FAQ_B1,
    INST_A1,
    INST_A2,
    INST_B1,
    JR_B,
    KS_FAQ_A1,
    KS_FAQ_B1,
    ORG_A,
    ORG_B,
    RUN_FAQ_A1,
    RUN_FAQ_B1,
    USER_ORG_A,
    UUID,
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


class TestOrganizationIsolation:
    def test_org_a_admin_cannot_manage_org_b(self):
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_organization(_user(user_id=USER_ORG_A), ctx, ORG_B)
        assert exc.value.status_code == 403
        assert exc.value.code == "ORGANIZATION_MISMATCH"

    def test_org_a_admin_manages_own_org(self):
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        authz.assert_can_manage_organization(_user(user_id=USER_ORG_A), ctx, ORG_A)

    def test_org_a_admin_cannot_manage_org_b_institution(self):
        """The institution's organization is resolved server-side."""
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_B)
        ):
            with pytest.raises(AppError) as exc:
                authz.assert_can_manage_institution(
                    _user(user_id=USER_ORG_A), ctx, INST_B1
                )
        assert exc.value.code == "ORGANIZATION_MISMATCH"

    def test_org_a_admin_manages_all_institutions_of_own_org(self):
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        for inst in (INST_A1, INST_A2):
            with patch.object(
                tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
            ):
                authz.assert_can_manage_institution(
                    _user(user_id=USER_ORG_A), ctx, inst
                )

    def test_org_a_knowledge_not_visible_to_org_b_institution(self):
        from app.services.ai import public_chat

        fake = _FakeClient(_base_state())
        assert public_chat._knowledge_source_is_public(fake, KS_FAQ_A1, UUID(INST_A1))
        # The same source is NOT public for institution B1.
        assert not public_chat._knowledge_source_is_public(
            fake, KS_FAQ_A1, UUID(INST_B1)
        )

    def test_org_a_request_never_gets_org_b_knowledge(self):
        from app.services.ai import public_chat

        fake = _FakeClient(_base_state())
        allowed = public_chat._build_allowed_public_knowledge_source_ids(
            fake, UUID(INST_A1), None
        )
        assert KS_FAQ_B1 not in allowed
        assert allowed == {KS_FAQ_A1}

    def test_org_a_cannot_explicitly_select_org_b_source(self):
        from app.services.ai import public_chat

        fake = _FakeClient(_base_state())
        with pytest.raises(AppError) as exc:
            public_chat._build_allowed_public_knowledge_source_ids(
                fake, UUID(INST_A1), KS_FAQ_B1
            )
        assert exc.value.status_code == 403
        assert exc.value.code == "KNOWLEDGE_SOURCE_NOT_PUBLIC"

    def test_org_b_chunk_never_reaches_org_a_llm_context(self):
        """Full pipeline: a manipulated Org B chunk is filtered out."""
        fake = _FakeClient(_base_state())
        request = _chat_request(
            retrieved_chunks=[
                _retrieved_chunk(CHUNK_FAQ_A1, RUN_FAQ_A1, "Org A public fact"),
                _retrieved_chunk(CHUNK_FAQ_B1, RUN_FAQ_B1, "Org B secret fact"),
            ]
        )
        _, provider = _run_public_chat(fake, request)
        texts = [c.text for c in provider.contexts[0].retrieved_knowledge]
        assert "Org A public fact" in texts
        assert "Org B secret fact" not in texts

    def test_org_a_admin_decision_on_org_b_join_request_denied(self):
        from app.schemas.platform.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["institution_join_requests"] = [
            {
                "join_request_id": JR_B,
                "organization_id": ORG_B,
                "institution_id": INST_B1,
                "status": "pending",
            }
        ]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_join_request(
                    _user(user_id=USER_ORG_A),
                    ctx,
                    JR_B,
                    ApprovalDecisionRequest(decision="approve"),
                )
        assert exc.value.code == "ORGANIZATION_MISMATCH"
        assert state["institution_join_requests"][0]["status"] == "pending"
