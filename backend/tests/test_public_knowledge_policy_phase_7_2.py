"""Phase 7.2 public knowledge policy and HTTP-boundary security tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app
from app.schemas.chat import PublicChatRequest
from app.schemas.generation import RetrievedChunk
from app.schemas.retrieval import RetrievalResponse, RetrievalResult
from app.services.public_chat import _build_allowed_public_knowledge_source_ids
from app.services.public_knowledge_policy import (
    PublicKnowledgePolicy,
    is_public_provenance,
    is_public_source,
)


INST_A = "10000000-0000-0000-0000-000000000001"
INST_B = "10000000-0000-0000-0000-000000000002"
ORG_A = "20000000-0000-0000-0000-000000000001"
KS_PUBLIC = "30000000-0000-0000-0000-000000000001"
KS_PRIVATE = "30000000-0000-0000-0000-000000000002"
DOC = "40000000-0000-0000-0000-000000000001"
VERSION = "50000000-0000-0000-0000-000000000001"
RUN = "60000000-0000-0000-0000-000000000001"
CHUNK_PUBLIC = "70000000-0000-0000-0000-000000000001"
CHUNK_PRIVATE = "70000000-0000-0000-0000-000000000002"
CONVERSATION = "80000000-0000-0000-0000-000000000001"
MESSAGE = "90000000-0000-0000-0000-000000000001"


def source(**overrides):
    row = {
        "knowledge_source_id": KS_PUBLIC,
        "institution_id": INST_A,
        "source_type": "notice",
        "title": "Public notice",
        "visibility": "public",
        "lifecycle_status": "published",
        "effective_from": "2026-01-01",
        "effective_until": "2026-12-31",
    }
    row.update(overrides)
    return row


def provenance(**overrides):
    row = {
        "processing_run_id": RUN,
        "processing_status": "ready",
        "embedding_status": "embedded",
        "completed_at": "2026-09-01T00:00:00Z",
        "document_version": {
            "document_version_id": VERSION,
            "document_id": DOC,
            "lifecycle_status": "published",
            "effective_from": "2026-01-01",
            "effective_until": "2026-12-31",
        },
        "document": {"document_id": DOC, "knowledge_source_id": KS_PUBLIC},
        "knowledge_source": source(),
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize("visibility", ["authenticated", "restricted", None])
def test_non_public_visibility_is_denied(visibility):
    assert not is_public_source(
        source(visibility=visibility), INST_A, on_date=date(2026, 9, 28)
    )


def test_public_source_requires_same_tenant_publication_and_effective_window():
    today = date(2026, 9, 28)
    assert is_public_source(source(), INST_A, on_date=today)
    assert not is_public_source(source(), INST_B, on_date=today)
    assert not is_public_source(
        source(lifecycle_status="draft"), INST_A, on_date=today
    )
    assert not is_public_source(
        source(effective_from="2026-09-29"), INST_A, on_date=today
    )
    assert not is_public_source(
        source(effective_until="2026-09-27"), INST_A, on_date=today
    )


@pytest.mark.parametrize("status", ["archived", "deleted", "revoked", "superseded"])
def test_invalid_source_lifecycle_is_denied(status):
    assert not is_public_source(
        source(lifecycle_status=status), INST_A, on_date=date(2026, 9, 28)
    )


def test_complete_provenance_policy_allows_only_valid_version_and_processing():
    today = date(2026, 9, 28)
    assert is_public_provenance(provenance(), INST_A, on_date=today)

    invalid_version = provenance()
    invalid_version["document_version"]["lifecycle_status"] = "draft"
    assert not is_public_provenance(invalid_version, INST_A, on_date=today)

    failed = provenance(processing_status="failed")
    assert not is_public_provenance(failed, INST_A, on_date=today)
    incomplete = provenance(embedding_status="processing")
    assert not is_public_provenance(incomplete, INST_A, on_date=today)
    no_completion = provenance(completed_at=None)
    assert not is_public_provenance(no_completion, INST_A, on_date=today)


def test_explicit_source_authorization_is_non_enumerating():
    fake = FakeClient(
        {
            "knowledge_sources": [
                source(),
                source(
                    knowledge_source_id=KS_PRIVATE,
                    visibility="restricted",
                ),
            ]
        }
    )
    assert _build_allowed_public_knowledge_source_ids(fake, UUID(INST_A), KS_PUBLIC) == {
        KS_PUBLIC
    }
    for source_id in (KS_PRIVATE, "30000000-0000-0000-0000-000000000099"):
        with pytest.raises(AppError) as exc:
            _build_allowed_public_knowledge_source_ids(fake, UUID(INST_A), source_id)
        assert exc.value.code == "KNOWLEDGE_SOURCE_NOT_PUBLIC"
        assert exc.value.status_code == 403


def test_strict_public_request_rejects_internal_controls():
    valid = PublicChatRequest(institution_code=" git ", message="  What courses? ")
    assert valid.institution_code == "GIT"
    assert valid.message == "What courses?"
    for field, value in (
        ("knowledge_source_id", KS_PUBLIC),
        ("document_id", DOC),
        ("processing_run_id", RUN),
        ("model_name", "attacker/model"),
        ("retrieved_chunks", []),
        ("debug", True),
    ):
        with pytest.raises(Exception):
            PublicChatRequest(
                institution_code="GIT", message="Question", **{field: value}
            )


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
        data = (rows[0] if rows else None) if self.single else rows
        return SimpleNamespace(data=data)


class FakeClient:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self, name)


def nested_run(knowledge_source):
    return {
        "processing_run_id": RUN,
        "status": "ready",
        "embedding_status": "embedded",
        "completed_at": "2026-09-01T00:00:00Z",
        "document_versions": {
            "document_version_id": VERSION,
            "document_id": DOC,
            "lifecycle_status": "published",
            "effective_from": "2026-01-01",
            "effective_until": "2026-12-31",
            "documents": {
                "document_id": DOC,
                "knowledge_source_id": knowledge_source["knowledge_source_id"],
                "knowledge_sources": knowledge_source,
            },
        },
    }


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
                    "processing_run_id": RUN,
                    "document_processing_runs": public_run,
                },
                {
                    "chunk_id": CHUNK_PRIVATE,
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
        patch("app.services.public_chat.get_admin_client", return_value=fake),
        patch("app.services.public_chat.get_conversation", return_value=None),
        patch(
            "app.services.public_chat.create_conversation",
            return_value={"conversation_id": CONVERSATION},
        ),
        patch("app.services.public_chat.get_conversation_messages", return_value=[]),
        patch("app.services.public_chat.get_next_message_sequence", return_value=1),
        patch("app.services.public_chat.create_message", side_effect=message_calls),
        patch("app.services.public_chat.retrieve", return_value=retrieved),
        patch("app.services.public_chat.AIGenerationService.generate", new=generate),
        patch("app.services.public_chat._start_background_persistence"),
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
        __import__("pathlib").Path(__file__).parents[2]
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
