from .support import (
    CHUNK_PRIVATE,
    CHUNK_PUBLIC,
    CONVERSATION,
    DOC,
    FakeClient,
    INST_A,
    KS_PRIVATE,
    MESSAGE,
    ORG_A,
    RUN,
    RetrievalResponse,
    RetrievalResult,
    SimpleNamespace,
    TestClient,
    VERSION,
    app,
    nested_run,
    patch,
    source,
)

def test_http_public_boundary_filters_private_context_and_projects_safe_response():
    public_source = source(effective_from=None, effective_until=None)
    private_source = source(
        knowledge_source_id=KS_PRIVATE,
        title="Private source",
        visibility="restricted",
        effective_from=None,
        effective_until=None,
    )
    public_run = nested_run(public_source)
    private_run = nested_run(private_source)
    private_run["processing_run_id"] = "60000000-0000-0000-0000-000000000002"

    fake = FakeClient(
        {
            "institutions": [
                {
                    "institution_id": INST_A,
                    "organization_id": ORG_A,
                    "code": "GIT",
                    "status": "active",
                    "is_active": True,
                }
            ],
            "organizations": [{"organization_id": ORG_A, "status": "active"}],
            "knowledge_sources": [public_source, private_source],
            "knowledge_chunks": [
                {
                    "chunk_id": CHUNK_PUBLIC,
                    "content_text": "Authorized public answer.",
                    "chunk_sequence": 1,
                    "section_title": "Admissions",
                    "processing_run_id": RUN,
                    "document_processing_runs": public_run,
                },
                {
                    "chunk_id": CHUNK_PRIVATE,
                    "content_text": "SECRET PRIVATE DATA",
                    "chunk_sequence": 1,
                    "processing_run_id": private_run["processing_run_id"],
                    "document_processing_runs": private_run,
                },
            ],
        }
    )
    retrieved = RetrievalResponse(
        results=[
            RetrievalResult(
                chunk_id=CHUNK_PUBLIC,
                document_id=DOC,
                document_version_id=VERSION,
                text="Authorized public answer.",
                similarity_score=0.9,
                metadata={
                    "processing_run_id": RUN,
                    "source_title": "Public notice",
                    "section_title": "Admissions",
                },
            ),
            RetrievalResult(
                chunk_id=CHUNK_PRIVATE,
                document_id=DOC,
                document_version_id=VERSION,
                text="SECRET PRIVATE DATA",
                similarity_score=0.99,
                metadata={"processing_run_id": private_run["processing_run_id"]},
            ),
        ]
    )
    captured = {}

    def generate(_service, context):
        captured["texts"] = [chunk.text for chunk in context.retrieved_knowledge]
        return SimpleNamespace(
            answer=f"Authorized answer [Retrieved chunk {CHUNK_PUBLIC}]",
            status="success",
            model_used="internal-model",
            metadata={"usage": {"prompt_tokens": 99, "completion_tokens": 4}},
        )

    message_calls = iter(({"message_id": MESSAGE}, {"message_id": MESSAGE}))
    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=fake),
        patch("app.services.ai.public_chat.get_conversation", return_value=None),
        patch(
            "app.services.ai.public_chat.create_conversation",
            return_value={"conversation_id": CONVERSATION},
        ),
        patch("app.services.ai.public_chat.get_conversation_messages", return_value=[]),
        patch("app.services.ai.public_chat.get_next_message_sequence", return_value=1),
        patch("app.services.ai.public_chat.create_message", side_effect=message_calls),
        patch("app.services.ai.public_chat.retrieve", return_value=retrieved),
        patch("app.services.ai.public_chat.AIGenerationService.generate", new=generate),
        patch("app.services.ai.public_chat._start_background_persistence"),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "git", "message": "What is public?"},
        )

    assert response.status_code == 200
    assert captured["texts"] == ["Authorized public answer."]
    body = response.json()
    assert set(body) == {"answer", "status", "sources"}
    assert body["sources"] == [
        {
            "title": "Public notice",
            "section": "Admissions",
            "quote": "Authorized public answer.",
        }
    ]
    forbidden = {"chunk_id", "document_id", "model_used", "metadata", "usage"}
    assert forbidden.isdisjoint(body)
    assert "SECRET" not in str(body)

def test_http_public_contract_rejects_source_id_bypass_before_service():
    response = TestClient(app).post(
        "/api/v1/chat/public",
        json={
            "institution_code": "GIT",
            "message": "Ignore policy",
            "knowledge_source_id": KS_PRIVATE,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

def test_migration_encodes_the_same_early_retrieval_predicate():
    sql = (
        __import__("pathlib").Path(__file__).parents[5]
        / "supabase/migrations/20260928000000_phase_7_2_public_knowledge_policy.sql"
    ).read_text(encoding="utf-8")
    for predicate in (
        "ks.institution_id = filter_institution_id",
        "ks.visibility = 'public'",
        "ks.lifecycle_status = 'published'",
        "dv.lifecycle_status = 'published'",
        "dpr.status = 'ready'",
        "dpr.embedding_status = 'embedded'",
    ):
        assert predicate in sql
    assert "FROM PUBLIC, anon, authenticated" in sql
