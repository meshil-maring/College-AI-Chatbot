from __future__ import annotations

from contextlib import ExitStack

from copy import deepcopy

from pathlib import Path

from types import SimpleNamespace

from unittest.mock import patch

from uuid import UUID

import pytest

from fastapi.testclient import TestClient

from app.config import settings

from app.main import app

from app.schemas.ai.generation import RetrievedChunk

from app.services.ai.generation_provider import GenerationResult

from app.services.ai.public_chat import _bound_public_context

from app.services.knowledge.public_knowledge_policy import PublicKnowledgePolicy

INST_A = "11000000-0000-0000-0000-000000000001"

INST_B = "11000000-0000-0000-0000-000000000002"

ORG_A = "12000000-0000-0000-0000-000000000001"

KS_A = "13000000-0000-0000-0000-000000000001"

KS_PRIVATE_A = "13000000-0000-0000-0000-000000000002"

KS_B = "13000000-0000-0000-0000-000000000003"

DOC_A = "14000000-0000-0000-0000-000000000001"

DOC_B = "14000000-0000-0000-0000-000000000002"

VERSION_A = "15000000-0000-0000-0000-000000000001"

VERSION_B = "15000000-0000-0000-0000-000000000002"

RUN_A = "16000000-0000-0000-0000-000000000001"

RUN_PRIVATE_A = "16000000-0000-0000-0000-000000000002"

RUN_B = "16000000-0000-0000-0000-000000000003"

CHUNK_A = "17000000-0000-0000-0000-000000000001"

CHUNK_PRIVATE_A = "17000000-0000-0000-0000-000000000002"

CHUNK_B = "17000000-0000-0000-0000-000000000003"

def _source(source_id: str, institution_id: str, visibility: str = "public") -> dict:
    return {
        "knowledge_source_id": source_id,
        "institution_id": institution_id,
        "source_type": "handbook",
        "title": "Official handbook" if source_id == KS_A else "Not authorized",
        "visibility": visibility,
        "lifecycle_status": "published",
        "effective_from": None,
        "effective_until": None,
    }

def _run(run_id: str, source: dict, document_id: str, version_id: str) -> dict:
    return {
        "processing_run_id": run_id,
        "status": "ready",
        "embedding_status": "embedded",
        "completed_at": "2026-09-28T00:00:00Z",
        "document_versions": {
            "document_version_id": version_id,
            "document_id": document_id,
            "lifecycle_status": "published",
            "effective_from": None,
            "effective_until": None,
            "documents": {
                "document_id": document_id,
                "knowledge_source_id": source["knowledge_source_id"],
                "knowledge_sources": source,
            },
        },
    }

class _Query:
    def __init__(self, client: _Client, table: str):
        self.client = client
        self.table = table
        self.filters: list[tuple[str, object]] = []
        self.in_filter: tuple[str, set[str]] | None = None
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

class _RPC:
    def __init__(self, client: _Client, name: str, params: dict):
        self.client = client
        self.name = name
        self.params = params

    def execute(self):
        self.client.rpc_calls.append((self.name, self.params))
        if self.client.rpc_error:
            raise self.client.rpc_error
        return SimpleNamespace(data=deepcopy(self.client.rpc_rows))

class _Client:
    def __init__(self):
        public_a = _source(KS_A, INST_A)
        private_a = _source(KS_PRIVATE_A, INST_A, "restricted")
        public_b = _source(KS_B, INST_B)
        self.tables = {
            "institutions": [
                {
                    "institution_id": INST_A,
                    "organization_id": ORG_A,
                    "code": "COLLEGE-A",
                    "status": "active",
                    "is_active": True,
                }
            ],
            "organizations": [{"organization_id": ORG_A, "status": "active"}],
            "knowledge_sources": [public_a, private_a, public_b],
            "knowledge_chunks": [
                {
                    "chunk_id": CHUNK_A,
                    "content_text": "Institution A officially offers engineering.",
                    "chunk_sequence": 1,
                    "section_title": "Programs",
                    "processing_run_id": RUN_A,
                    "document_processing_runs": _run(RUN_A, public_a, DOC_A, VERSION_A),
                },
                {
                    "chunk_id": CHUNK_PRIVATE_A,
                    "content_text": "PRIVATE A RECORD",
                    "chunk_sequence": 1,
                    "processing_run_id": RUN_PRIVATE_A,
                    "document_processing_runs": _run(
                        RUN_PRIVATE_A, private_a, DOC_A, VERSION_A
                    ),
                },
                {
                    "chunk_id": CHUNK_B,
                    "content_text": "INSTITUTION B RECORD",
                    "chunk_sequence": 1,
                    "processing_run_id": RUN_B,
                    "document_processing_runs": _run(RUN_B, public_b, DOC_B, VERSION_B),
                },
            ],
        }
        # Deliberately hostile candidate payloads prove that the application
        # boundary does not trust vector-result text or cross-tenant rows.
        self.rpc_rows = [
            {
                "chunk_id": CHUNK_A,
                "document_id": DOC_A,
                "document_version_id": VERSION_A,
                "content_text": "FORGED VECTOR RESULT TEXT",
                "processing_run_id": RUN_A,
                "chunk_sequence": 1,
                "section_title": "Forged section",
                "source_title": "Forged title",
                "source_type": "handbook",
                "model_name": settings.embedding_model,
                "distance": 0.05,
            },
            {
                "chunk_id": CHUNK_PRIVATE_A,
                "document_id": DOC_A,
                "document_version_id": VERSION_A,
                "content_text": "PRIVATE A RECORD",
                "processing_run_id": RUN_PRIVATE_A,
                "model_name": settings.embedding_model,
                "distance": 0.01,
            },
            {
                "chunk_id": CHUNK_B,
                "document_id": DOC_B,
                "document_version_id": VERSION_B,
                "content_text": "INSTITUTION B RECORD",
                "processing_run_id": RUN_B,
                "model_name": settings.embedding_model,
                "distance": 0.001,
            },
        ]
        self.rpc_calls: list[tuple[str, dict]] = []
        self.rpc_error: Exception | None = None

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params):
        return _RPC(self, name, params)
