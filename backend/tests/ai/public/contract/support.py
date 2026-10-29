from __future__ import annotations

from copy import deepcopy

from types import SimpleNamespace

from unittest.mock import MagicMock, patch

from uuid import UUID

import httpx

import pytest

from fastapi.testclient import TestClient

from app.main import app

from app.schemas.ai.chat import PublicChatResponse

from app.schemas.knowledge.retrieval import RetrievalResponse, RetrievalResult

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
