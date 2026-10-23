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
    _inst_row,
    _org_row,
)
from .support import (
    AppError,
    CHUNK_FAQ_A1,
    CHUNK_PRIVATE_A1,
    INST_A1,
    KS_PRIVATE_A1,
    ORG_A,
    ORG_B,
    RUN_FAQ_A1,
    RUN_PRIVATE_A1,
    _active_institution_authorization,
    get_current_user,
    inspect,
    pytest,
    uuid4,
)


class TestPublicAISecurity:
    def test_public_chat_requires_no_authentication(self):
        from app.main import public_chat as public_chat_endpoint
        from app.services.ai import public_chat

        source = inspect.getsource(public_chat.process_chat_request)
        assert "get_current_user" not in source
        # The public endpoint itself declares no auth dependency.
        signature = inspect.signature(public_chat_endpoint)
        for param in signature.parameters.values():
            default = param.default
            assert getattr(default, "dependency", None) is not get_current_user

    def test_public_institution_is_resolved_server_side(self):
        from app.services.ai import public_chat

        source = inspect.getsource(public_chat._validate_public_institution)
        assert "get_institution_by_id" in source
        assert "get_organization_by_id" in source

    def test_inactive_institution_cannot_use_public_ai(self):
        for status in ("pending", "rejected", "suspended"):
            state = _base_state()
            state["institutions"] = [_inst_row(INST_A1, ORG_A, status)]
            fake = _FakeClient(state)
            with pytest.raises(AppError) as exc:
                _run_public_chat(fake, _chat_request())
            assert exc.value.status_code == 403
            assert exc.value.code == "INSTITUTION_NOT_ACTIVE"

    def test_inactive_organization_blocks_public_ai(self):
        state = _base_state()
        state["organizations"] = [
            _org_row(ORG_A, "suspended"),
            _org_row(ORG_B, "active"),
        ]
        fake = _FakeClient(state)
        with pytest.raises(AppError) as exc:
            _run_public_chat(fake, _chat_request())
        assert exc.value.status_code == 403
        assert exc.value.code == "ORGANIZATION_NOT_ACTIVE"

    def test_unknown_institution_denied(self):
        fake = _FakeClient(_base_state())
        with pytest.raises(AppError) as exc:
            _run_public_chat(fake, _chat_request(institution_id=uuid4()))
        assert exc.value.status_code == 404
        assert exc.value.code == "INSTITUTION_NOT_FOUND"

    def test_private_document_chunk_never_reaches_llm(self):
        fake = _FakeClient(_base_state())
        request = _chat_request(
            retrieved_chunks=[
                _retrieved_chunk(CHUNK_FAQ_A1, RUN_FAQ_A1, "Public handbook fact"),
                _retrieved_chunk(
                    CHUNK_PRIVATE_A1, RUN_PRIVATE_A1, "CONFIDENTIAL private doc"
                ),
            ]
        )
        _, provider = _run_public_chat(fake, request)
        texts = [c.text for c in provider.contexts[0].retrieved_knowledge]
        assert "Org A public fact" in texts
        assert "CONFIDENTIAL private doc" not in texts

    def test_explicit_private_knowledge_source_denied(self):
        fake = _FakeClient(_base_state())
        with pytest.raises(AppError) as exc:
            _run_public_chat(fake, _chat_request(knowledge_source_id=KS_PRIVATE_A1))
        assert exc.value.status_code == 403
        assert exc.value.code == "KNOWLEDGE_SOURCE_NOT_PUBLIC"

    def test_student_records_never_read_by_public_ai(self):
        """The public path never touches student/academic tables at all."""
        fake = _FakeClient(_base_state())
        request = _chat_request(
            retrieved_chunks=[
                _retrieved_chunk(CHUNK_FAQ_A1, RUN_FAQ_A1, "Public handbook fact")
            ]
        )
        _run_public_chat(fake, request)
        accesses = set(fake.state["accesses"])
        forbidden = {
            "students",
            "student_attendance",
            "attendance",
            "student_test_results",
            "test_results",
            "student_results",
            "results",
            "users",
        }
        assert not (accesses & forbidden), accesses

    def test_personalized_queries_require_protected_access(self):
        for question in (
            "What is my attendance?",
            "What are my test results?",
            "What was my CGPA?",
        ):
            fake = _FakeClient(_base_state())
            with pytest.raises(AppError) as exc:
                _run_public_chat(fake, _chat_request(query=question))
            assert exc.value.status_code == 401
            assert exc.value.code == "AUTH_REQUIRED"

    def test_general_policy_question_remains_public(self):
        """A policy question that merely mentions attendance stays public."""
        fake = _FakeClient(_base_state())
        request = _chat_request(
            query="What attendance percentage is required?",
            retrieved_chunks=[
                _retrieved_chunk(CHUNK_FAQ_A1, RUN_FAQ_A1, "Attendance policy fact")
            ],
        )
        response, _ = _run_public_chat(fake, request)
        assert response.status == "success"
