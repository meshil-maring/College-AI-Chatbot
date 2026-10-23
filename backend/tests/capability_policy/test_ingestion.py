"""Test ingestion."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import inspect

import pytest

import re

from .principals import (
    AUTH_HEADERS,
    INST_A,
    KNOWLEDGE_SOURCE_A,
    STAFF_AND_FACULTY_USERS,
    client,
)

from .support import (
    _as,
    _clean_dependencies,
    _source_row,
)


def test_the_ingestion_dependency_allows_exactly_the_three_operational_roles() -> None:
    """`/documents/*` is the sole non-chat capability shared by staff + faculty."""
    from app.api.knowledge import ingestion

    source = inspect.getsource(ingestion)
    match = re.search(r"_INGEST_ALLOWED = require_institution_roles\(([^)]*)\)", source)
    assert match is not None
    assert re.findall(r'"([a-z_]+)"', match.group(1)) == [
        "admin",
        "staff",
        "faculty",
    ]


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_reach_ingestion_within_their_own_institution(
    principal: dict, label: str
) -> None:
    """The shared knowledge capability IS implemented, not merely denied."""
    with (
        _as(principal),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch(
            "app.api.knowledge.ingestion.get_knowledge_source",
            return_value=_source_row(INST_A),
        ),
        patch(
            "app.api.knowledge.ingestion.ingest_document",
            new=AsyncMock(
                return_value={
                    "knowledge_source_id": KNOWLEDGE_SOURCE_A,
                    "document_id": "00000000-0000-0000-0000-0000000000d1",
                    "document_version_id": "00000000-0000-0000-0000-0000000000d2",
                    "processing_run_id": "00000000-0000-0000-0000-0000000000d3",
                    "storage_object_key": "institution-a/doc.txt",
                    "status": "queued",
                }
            ),
        ) as ingest,
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_A},
        )
    assert response.status_code == 201, (label, response.text)
    ingest.assert_awaited_once()


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_ai_assistant_is_reachable_in_tenant_for_staff_and_faculty(
    principal: dict, label: str
) -> None:
    """The AI Assistant capability IS implemented and tenant-pinned."""
    from app.schemas.ai.chat import ChatResponse

    answer = ChatResponse(
        user_query="hello",
        session_id="00000000-0000-0000-0000-0000000000cc",
        conversation_id="00000000-0000-0000-0000-0000000000aa",
        message_id="00000000-0000-0000-0000-0000000000bb",
        answer="ok",
        status="success",
    )
    with (
        _as(principal),
        patch("app.main.resolve_session_context", return_value={"sources": []}),
        patch("app.main.process_chat_request", return_value=answer) as process,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "hello", "institution_id": INST_A},
        )
    assert response.status_code == 200, (label, response.text)
    pinned = process.call_args.kwargs["current_user"]
    assert pinned["institution_id"] == INST_A, label
