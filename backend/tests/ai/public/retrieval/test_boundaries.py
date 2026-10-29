from .support import (
    ExitStack,
    Path,
    TestClient,
    _CapturingProvider,
    _Client,
    _post,
    app,
    patch,
    pytest,
)

@pytest.mark.parametrize(
    "dependency, expected_code",
    [
        ("embedding", "EMBEDDING_FAILED"),
        ("rpc", "INTERNAL_ERROR"),
        ("provenance", "INTERNAL_ERROR"),
        ("context", "INTERNAL_ERROR"),
    ],
)
def test_public_dependency_failures_return_sanitized_errors(dependency, expected_code):
    client = _Client()
    provider = _CapturingProvider()
    secret = "SELECT api_key FROM private_table at C:\\secret\\app.py"
    patches = [
        patch("app.services.ai.public_chat.get_admin_client", return_value=client),
        patch("app.services.knowledge.retrieval.get_admin_client", return_value=client),
        patch("app.main.OpenRouterGenerationProvider", return_value=provider),
    ]
    if dependency == "embedding":
        patches.append(patch("app.services.knowledge.retrieval.embed_query", side_effect=RuntimeError(secret)))
    else:
        patches.append(patch("app.services.knowledge.retrieval.embed_query", return_value=[0.25] * 1536))
    if dependency == "rpc":
        client.rpc_error = RuntimeError(secret)
    elif dependency == "provenance":
        patches.append(
            patch(
                "app.repositories.knowledge.public_knowledge.get_chunk_provenance",
                side_effect=RuntimeError(secret),
            )
        )
    elif dependency == "context":
        patches.append(patch("app.services.ai.public_chat.assemble_context", side_effect=RuntimeError(secret)))

    with ExitStack() as stack:
        for dependency_patch in patches:
            stack.enter_context(dependency_patch)
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE-A", "message": "Programs?"},
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == expected_code
    assert "private_table" not in response.text
    assert "secret" not in response.text

def test_public_rpc_has_complete_filter_dimension_limit_and_hnsw_index():
    repo_root = Path(__file__).parents[5]
    sql = (
        repo_root
        / "supabase/migrations/20260928010000_phase_7_4_public_rag_hardening.sql"
    ).read_text(encoding="utf-8")
    index_sql = (
        repo_root
        / "supabase/migrations/20260905000000_phase_3_7_1_vector_search_index.sql"
    ).read_text(encoding="utf-8")
    for predicate in (
        "ks.institution_id = filter_institution_id",
        "ks.visibility = 'public'",
        "ks.lifecycle_status = 'published'",
        "CURRENT_DATE",
        "dv.lifecycle_status = 'published'",
        "dpr.status = 'ready'",
        "dpr.embedding_status = 'embedded'",
        "dpr.completed_at IS NOT NULL",
        "ce.embedding_dimensions = 1536",
        "ce.model_name = filter_model_name",
        "ORDER BY ce.embedding <=> query_embedding ASC",
        "LIMIT LEAST(match_count, 20)",
    ):
        assert predicate in sql
    assert "USING hnsw" in index_sql
    assert "vector_cosine_ops" in index_sql

def test_public_request_cannot_select_retrieval_or_embedding_configuration():
    response = TestClient(app).post(
        "/api/v1/chat/public",
        json={
            "institution_code": "COLLEGE-A",
            "message": "Programs?",
            "top_k": 20,
            "embedding_model": "attacker/model",
            "retrieval_strategy": "global",
            "index": "private_index",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

def test_public_path_never_calls_generic_authenticated_vector_search():
    client = _Client()
    provider = _CapturingProvider()
    with patch(
        "app.services.knowledge.retrieval.search_chunks",
        side_effect=AssertionError("generic authenticated retrieval used"),
    ) as generic:
        response, _ = _post(client, provider)
    assert response.status_code == 200
    generic.assert_not_called()
