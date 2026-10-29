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

from app.schemas.ai.chat import PublicChatRequest

from app.schemas.ai.generation import RetrievedChunk

from app.schemas.knowledge.retrieval import RetrievalResponse, RetrievalResult

from app.services.ai.public_chat import _build_allowed_public_knowledge_source_ids

from app.services.knowledge.public_knowledge_policy import (
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
