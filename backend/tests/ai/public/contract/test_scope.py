from .support import (
    CHUNK_A,
    DOC_A,
    FakeClient,
    INST_A,
    MagicMock,
    RetrievalResponse,
    RetrievalResult,
    SimpleNamespace,
    TestClient,
    UUID,
    VERSION_A,
    _client_with_public_and_cross_tenant_chunks,
    _retrieval_results,
    _run,
    _source,
    app,
    patch,
)

def test_unknown_institution_fails_before_retrieval():
    fake = FakeClient({"institutions": []})
    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=fake),
        patch("app.services.ai.public_chat.retrieve") as retrieve,
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "UNKNOWN", "message": "Hello"},
        )
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "INSTITUTION_NOT_FOUND", "message": "Institution not found"}
    }
    retrieve.assert_not_called()

def test_tenant_isolation_and_stateless_generation_context():
    fake = _client_with_public_and_cross_tenant_chunks()
    captured = {}

    def generate(_service, context):
        captured["texts"] = [chunk.text for chunk in context.retrieved_knowledge]
        captured["history"] = context.conversation_history
        return SimpleNamespace(
            answer=f"Engineering courses are offered. [Retrieved chunk {CHUNK_A}]",
            status="success",
            model_used="internal-model",
            metadata={"usage": {"prompt_tokens": 100}},
        )

    persistence_sentinel = MagicMock(side_effect=AssertionError("public persistence called"))
    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=fake),
        patch("app.services.ai.public_chat.retrieve", return_value=_retrieval_results()) as retrieve,
        patch("app.services.ai.public_chat.AIGenerationService.generate", new=generate),
        patch("app.services.ai.public_chat.create_conversation", persistence_sentinel),
        patch("app.services.ai.public_chat.get_conversation", persistence_sentinel),
        patch("app.services.ai.public_chat.create_message", persistence_sentinel),
        patch("app.services.ai.public_chat.get_conversation_messages", persistence_sentinel),
        patch("app.services.ai.public_chat._start_background_persistence", persistence_sentinel),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "What courses?"},
        )

    assert response.status_code == 200
    assert captured["texts"] == ["Institution A offers public engineering courses."]
    assert captured["history"] == []
    retrieval_request = retrieve.call_args.args[0]
    assert str(retrieval_request.institution_id) == INST_A
    assert retrieval_request.public_only is True
    assert "INSTITUTION B" not in str(response.json())
    assert CHUNK_A not in response.text
    assert response.json()["answer"] == "Engineering courses are offered."
    assert response.json()["sources"] == [
        {
            "title": "Academic Handbook",
            "section": "Courses",
            "quote": "Institution A offers public engineering courses.",
        }
    ]
    persistence_sentinel.assert_not_called()

def test_generation_receives_only_fully_eligible_public_data():
    eligible = _source()
    variants = [
        ("authenticated", _source(source_id=str(UUID(int=301)), visibility="authenticated"), {}),
        ("restricted", _source(source_id=str(UUID(int=302)), visibility="restricted"), {}),
        ("unpublished", {**_source(source_id=str(UUID(int=303))), "lifecycle_status": "draft"}, {}),
        ("archived", {**_source(source_id=str(UUID(int=304))), "lifecycle_status": "archived"}, {}),
        ("future", {**_source(source_id=str(UUID(int=305))), "effective_from": "2999-01-01"}, {}),
        ("expired", {**_source(source_id=str(UUID(int=306))), "effective_until": "2000-01-01"}, {}),
        ("invalid-version", _source(source_id=str(UUID(int=307))), {"version_status": "draft"}),
        ("failed-processing", _source(source_id=str(UUID(int=308))), {"status": "failed"}),
        ("unembedded", _source(source_id=str(UUID(int=309))), {"embedding_status": "processing"}),
    ]
    sources = [eligible, *(source for _, source, _ in variants)]
    chunks = []
    results = []
    for index, (label, source, run_overrides) in enumerate(
        [("eligible", eligible, {}), *variants], start=1
    ):
        chunk_id = str(UUID(int=700 + index))
        run_id = str(UUID(int=600 + index))
        nested = _run(source, run_id=run_id)
        nested["status"] = run_overrides.get("status", "ready")
        nested["embedding_status"] = run_overrides.get(
            "embedding_status", "embedded"
        )
        nested["document_versions"]["lifecycle_status"] = run_overrides.get(
            "version_status", "published"
        )
        chunks.append(
            {
                "chunk_id": chunk_id,
                "content_text": f"{label} content",
                "chunk_sequence": index,
                "processing_run_id": run_id,
                "document_processing_runs": nested,
            }
        )
        results.append(
            RetrievalResult(
                chunk_id=chunk_id,
                document_id=DOC_A,
                document_version_id=VERSION_A,
                text=f"{label} content",
                similarity_score=0.9,
                metadata={"processing_run_id": run_id},
            )
        )

    fake = _client_with_public_and_cross_tenant_chunks()
    fake.tables["knowledge_sources"] = sources
    fake.tables["knowledge_chunks"] = chunks
    captured = {}

    def generate(_service, context):
        captured["texts"] = [chunk.text for chunk in context.retrieved_knowledge]
        return SimpleNamespace(
            answer="Only eligible content was used.",
            status="success",
            model_used="internal-model",
            metadata={},
        )

    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=fake),
        patch(
            "app.services.ai.public_chat.retrieve",
            return_value=RetrievalResponse(results=results),
        ),
        patch("app.services.ai.public_chat.AIGenerationService.generate", new=generate),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "Public facts?"},
        )

    assert response.status_code == 200
    assert captured["texts"] == ["eligible content"]
