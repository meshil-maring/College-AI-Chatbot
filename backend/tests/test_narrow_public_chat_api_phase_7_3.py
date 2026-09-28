"""Phase 7.3 narrow, stateless public chat API tests."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chat import PublicChatResponse
from app.schemas.retrieval import RetrievalResponse, RetrievalResult


INST_A = "10000000-0000-0000-0000-000000000001"
INST_B = "10000000-0000-0000-0000-000000000002"
ORG_A = "20000000-0000-0000-0000-000000000001"
KS_A = "30000000-0000-0000-0000-000000000001"
KS_B = "30000000-0000-0000-0000-000000000002"
DOC_A = "40000000-0000-0000-0000-000000000001"
VERSION_A = "50000000-0000-0000-0000-000000000001"
RUN_A = "60000000-0000-0000-0000-000000000001"
RUN_B = "60000000-0000-0000-0000-000000000002"
CHUNK_A = "70000000-0000-0000-0000-000000000001"
CHUNK_B = "70000000-0000-0000-0000-000000000002"


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.filters = []
        self.in_filter = None
        self.single = False

    def select(self, *_args):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def in_(self, key, values):
        self.in_filter = (key, {str(value) for value in values})
        return self

    def maybe_single(self):
        self.single = True
        return self

    def execute(self):
        rows = deepcopy(self.client.tables.get(self.table, []))
        for key, value in self.filters:
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        if self.in_filter:
            key, values = self.in_filter
            rows = [row for row in rows if str(row.get(key)) in values]
        return SimpleNamespace(data=(rows[0] if rows else None) if self.single else rows)


class FakeClient:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self, name)


def _source(*, institution_id=INST_A, source_id=KS_A, visibility="public"):
    return {
        "knowledge_source_id": source_id,
        "institution_id": institution_id,
        "source_type": "handbook",
        "title": "Academic Handbook",
        "visibility": visibility,
        "lifecycle_status": "published",
        "effective_from": None,
        "effective_until": None,
    }


def _run(source, *, run_id=RUN_A):
    return {
        "processing_run_id": run_id,
        "status": "ready",
        "embedding_status": "embedded",
        "completed_at": "2026-09-28T00:00:00Z",
        "document_versions": {
            "document_version_id": VERSION_A,
            "document_id": DOC_A,
            "lifecycle_status": "published",
            "effective_from": None,
            "effective_until": None,
            "documents": {
                "document_id": DOC_A,
                "knowledge_source_id": source["knowledge_source_id"],
                "knowledge_sources": source,
            },
        },
    }


def _client_with_public_and_cross_tenant_chunks():
    source_a = _source()
    source_b = _source(institution_id=INST_B, source_id=KS_B)
    return FakeClient(
        {
            "institutions": [
                {
                    "institution_id": INST_A,
                    "organization_id": ORG_A,
                    "code": "COLLEGE001",
                    "status": "active",
                    "is_active": True,
                }
            ],
            "organizations": [{"organization_id": ORG_A, "status": "active"}],
            "knowledge_sources": [source_a, source_b],
            "knowledge_chunks": [
                {
                    "chunk_id": CHUNK_A,
                    "content_text": "Institution A offers public engineering courses.",
                    "chunk_sequence": 1,
                    "section_title": "Courses",
                    "processing_run_id": RUN_A,
                    "document_processing_runs": _run(source_a),
                },
                {
                    "chunk_id": CHUNK_B,
                    "content_text": "INSTITUTION B PRIVATE-TO-A CONTENT",
                    "chunk_sequence": 1,
                    "processing_run_id": RUN_B,
                    "document_processing_runs": _run(source_b, run_id=RUN_B),
                },
            ],
        }
    )


def _retrieval_results():
    return RetrievalResponse(
        results=[
            RetrievalResult(
                chunk_id=CHUNK_A,
                document_id=DOC_A,
                document_version_id=VERSION_A,
                text="Institution A offers public engineering courses.",
                similarity_score=0.91,
                metadata={
                    "processing_run_id": RUN_A,
                    "source_title": "Academic Handbook",
                    "section_title": "Courses",
                },
            ),
            RetrievalResult(
                chunk_id=CHUNK_B,
                document_id=DOC_A,
                document_version_id=VERSION_A,
                text="INSTITUTION B PRIVATE-TO-A CONTENT",
                similarity_score=0.99,
                metadata={"processing_run_id": RUN_B},
            ),
        ]
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"institution_code": "COLLEGE001", "message": ""},
        {"institution_code": "COLLEGE001", "message": "   \n\t"},
        {"institution_code": "COLLEGE001", "message": "x" * 4001},
        {"institution_code": "COLLEGE001"},
        {"message": "Hello"},
        {"institution_code": "", "message": "Hello"},
        {"institution_code": "COLLEGE001", "message": "Hello", "unknown": 1},
        {"institution_code": "COLLEGE001", "message": "Hello", "knowledge_source_id": KS_A},
        {"institution_code": "COLLEGE001", "message": "Hello", "document_id": DOC_A},
        {"institution_code": "COLLEGE001", "message": "Hello", "document_version_id": VERSION_A},
        {"institution_code": "COLLEGE001", "message": "Hello", "processing_run_id": RUN_A},
        {"institution_code": "COLLEGE001", "message": "Hello", "chunk_limit": 100},
        {"institution_code": "COLLEGE001", "message": "Hello", "similarity_threshold": 0},
        {"institution_code": "COLLEGE001", "message": "Hello", "embedding_model": "attacker"},
        {"institution_code": "COLLEGE001", "message": "Hello", "model": "attacker/model"},
        {"institution_code": "COLLEGE001", "message": "Hello", "temperature": 2},
        {"institution_code": "COLLEGE001", "message": "Hello", "token_limit": 999999},
        {"institution_code": "COLLEGE001", "message": "Hello", "provider": "attacker"},
        {"institution_code": "COLLEGE001", "message": "Hello", "debug": True},
    ],
)
def test_strict_request_validation_rejects_invalid_or_internal_input(payload):
    with patch("app.main.process_public_request") as process:
        response = TestClient(app).post("/api/v1/chat/public", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    process.assert_not_called()


def test_malformed_json_is_rejected_before_public_service():
    with patch("app.main.process_public_request") as process:
        response = TestClient(app).post(
            "/api/v1/chat/public",
            content=b'{"institution_code": "COLLEGE001",',
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    process.assert_not_called()


def test_valid_request_needs_no_credentials_and_normalizes_input():
    captured = {}

    def process(request, _context, _provider):
        captured["request"] = request
        return PublicChatResponse(answer=None, status="insufficient_context")

    with patch("app.main.process_public_request", side_effect=process):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": " college001 ", "message": "  What   courses? "},
        )
    assert response.status_code == 200
    assert captured["request"].institution_code == "COLLEGE001"
    assert captured["request"].message == "What courses?"


def test_unknown_institution_fails_before_retrieval():
    fake = FakeClient({"institutions": []})
    with (
        patch("app.services.public_chat.get_admin_client", return_value=fake),
        patch("app.services.public_chat.retrieve") as retrieve,
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
        patch("app.services.public_chat.get_admin_client", return_value=fake),
        patch("app.services.public_chat.retrieve", return_value=_retrieval_results()) as retrieve,
        patch("app.services.public_chat.AIGenerationService.generate", new=generate),
        patch("app.services.public_chat.create_conversation", persistence_sentinel),
        patch("app.services.public_chat.get_conversation", persistence_sentinel),
        patch("app.services.public_chat.create_message", persistence_sentinel),
        patch("app.services.public_chat.get_conversation_messages", persistence_sentinel),
        patch("app.services.public_chat._start_background_persistence", persistence_sentinel),
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
        patch("app.services.public_chat.get_admin_client", return_value=fake),
        patch(
            "app.services.public_chat.retrieve",
            return_value=RetrievalResponse(results=results),
        ),
        patch("app.services.public_chat.AIGenerationService.generate", new=generate),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "Public facts?"},
        )

    assert response.status_code == 200
    assert captured["texts"] == ["eligible content"]


def test_no_public_information_returns_safe_insufficient_context_response():
    fake = _client_with_public_and_cross_tenant_chunks()
    provider = MagicMock()
    with (
        patch("app.services.public_chat.get_admin_client", return_value=fake),
        patch(
            "app.services.public_chat.retrieve",
            return_value=RetrievalResponse(results=[]),
        ),
        patch("app.main.OpenRouterGenerationProvider", return_value=provider),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "Unknown topic"},
        )
    assert response.status_code == 200
    assert response.json() == {
        "answer": None,
        "status": "insufficient_context",
        "sources": [],
    }
    provider.generate.assert_not_called()


def test_generation_failure_returns_only_safe_provider_error():
    fake = _client_with_public_and_cross_tenant_chunks()
    provider = MagicMock()
    provider.generate.side_effect = RuntimeError("SECRET_API_KEY provider traceback")
    with (
        patch("app.services.public_chat.get_admin_client", return_value=fake),
        patch("app.services.public_chat.retrieve", return_value=_retrieval_results()),
        patch("app.main.OpenRouterGenerationProvider", return_value=provider),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "What courses?"},
        )
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "GENERATION_FAILED", "message": "AI generation failed"}
    }
    assert "SECRET_API_KEY" not in response.text


def test_unhandled_retrieval_failure_uses_generic_error_envelope():
    fake = _client_with_public_and_cross_tenant_chunks()
    with (
        patch("app.services.public_chat.get_admin_client", return_value=fake),
        patch(
            "app.services.public_chat.retrieve",
            side_effect=RuntimeError("SELECT secret FROM internal_table"),
        ),
    ):
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "What courses?"},
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "SELECT" not in response.text
    assert "internal_table" not in response.text


def test_openapi_documents_narrow_unauthenticated_contract():
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/chat/public"]["post"]
    request_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert request_ref.endswith("/PublicChatRequest")
    assert response_ref.endswith("/PublicChatResponse")
    assert not operation.get("security")
    assert "Authentication: Not required" in operation["description"]
    assert {"401", "403", "404", "422", "500"}.issubset(operation["responses"])

    request_schema = schema["components"]["schemas"]["PublicChatRequest"]
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["properties"]) == {"institution_code", "message"}
    forbidden = {
        "knowledge_source_id",
        "document_id",
        "document_version_id",
        "processing_run_id",
        "model",
        "provider",
        "temperature",
        "token_limit",
        "debug",
    }
    assert forbidden.isdisjoint(request_schema["properties"])


def test_public_response_model_rejects_internal_metadata():
    with pytest.raises(Exception):
        PublicChatResponse(
            answer="Safe",
            status="success",
            sources=[],
            model_used="internal-model",
        )
