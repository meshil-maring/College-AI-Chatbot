from .support import (
    AsyncMock,
    AuthApiError,
    CONVERSATION_ID,
    INST_A1,
    LOGIN_URL,
    MESSAGE_ID,
    MagicMock,
    SESSION_ID,
    USER_PLATFORM,
    UUID,
    client,
    patch,
)


class _CapturingProvider:
    """GenerationProvider that records the AIContext it receives."""

    def __init__(self):
        self.contexts = []

    def generate(self, context, *, answer_model=None):
        from app.services.ai.generation_provider import GenerationResult

        self.contexts.append(context)
        return GenerationResult(
            answer="Public answer",
            model_used="test-model",
            status="success",
            metadata={"usage": {"prompt_tokens": 1, "completion_tokens": 1}},
        )


def _chat_request(
    query="What are the college fees?",
    institution_id=INST_A1,
    knowledge_source_id=None,
    retrieved_chunks=None,
):
    from app.schemas.ai.chat import ChatRequest

    return ChatRequest(
        user_query=query,
        institution_id=institution_id,
        session_id=SESSION_ID,
        knowledge_source_id=knowledge_source_id,
        retrieved_chunks=retrieved_chunks or [],
    )


def _retrieved_chunk(chunk_id, run_id, text):
    from app.schemas.ai.generation import RetrievedChunk

    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        similarity_score=0.9,
        metadata={"processing_run_id": run_id},
    )


def _run_public_chat(fake, request):
    """Run the real public chat pipeline against the fake client.

    Only the persistence seams (conversation/message reads/writes and the
    background writer) are stubbed; tenant validation and the public-only
    retrieval filter run for real against ``fake``.
    """
    from app.schemas.ai.session import SessionContext
    from app.services.ai import public_chat

    provider = _CapturingProvider()
    with (
        patch.object(public_chat, "get_admin_client", return_value=fake),
        patch.object(
            public_chat,
            "get_conversation",
            return_value={"conversation_id": CONVERSATION_ID},
        ),
        patch.object(public_chat, "get_conversation_messages", return_value=[]),
        patch.object(public_chat, "get_next_message_sequence", return_value=1),
        patch.object(
            public_chat, "create_message", return_value={"message_id": MESSAGE_ID}
        ),
        patch.object(public_chat, "_start_background_persistence", return_value=None),
    ):
        response = public_chat.process_chat_request(
            request, SessionContext(session_id=UUID(SESSION_ID)), provider
        )
    return response, provider


def _gos_true_client(success=True, email="user@example.com"):
    auth = MagicMock()
    if not success:
        auth.auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid login credentials", 400, "invalid_grant"
        )
        return auth
    session = MagicMock()
    session.access_token = "mock-access-token"
    user = MagicMock()
    user.id = USER_PLATFORM
    user.email = email
    auth.auth.sign_in_with_password.return_value = MagicMock(session=session, user=user)
    return auth


def _sign_in_account(**overrides):
    account = {
        "user_id": USER_PLATFORM,
        "status": "active",
        "institution_id": None,
        "approval_status": None,
        "student_is_active": None,
    }
    account.update(overrides)
    return account


def _login(account, auth=None, email="user@example.com", db=None):
    auth = auth or _gos_true_client(email=email)
    db = db if db is not None else MagicMock()
    with (
        patch("app.api.auth.common.create_supabase_client", return_value=auth),
        patch(
            "app.api.auth.common.get_sign_in_context",
            new=AsyncMock(return_value=account),
        ),
        patch("app.api.auth.common.get_admin_client", return_value=db),
        patch("app.api.auth.common.record_auth_security_event"),
    ):
        return client.post(LOGIN_URL, json={"email": email, "password": "secret123"})


def _institution_db(is_active=True):
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
    ) = {
        "institution_id": INST_A1,
        "name": "Campus",
        "code": "IMPHAL",
        "status": "active" if is_active else "suspended",
        "is_active": is_active,
    }
    return db
