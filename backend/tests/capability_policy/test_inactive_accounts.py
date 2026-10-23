"""Test inactive accounts."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .principals import (
    AUTH_HEADERS,
    DEACTIVATED_STAFF_USER,
    INST_A,
    KNOWLEDGE_SOURCE_A,
    STUDENT_A_ROW,
    client,
)

from .support import (
    DEACTIVATED_USERS,
    _as,
    _clean_dependencies,
    _error_code,
    _source_row,
)


def test_deactivated_staff_cannot_use_the_approval_queue() -> None:
    with (
        _as(DEACTIVATED_STAFF_USER),
        patch(
            "app.services.admin.admin_academics.academics_repo.list_pending_students",
            return_value=[],
        ) as repo,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _error_code(response) == "ACCOUNT_INACTIVE"
    repo.assert_not_called()


def test_deactivated_staff_cannot_approve_a_student() -> None:
    with (
        _as(DEACTIVATED_STAFF_USER),
        patch(
            "app.services.admin.admin_academics.academics_repo.get_student_for_approval",
            return_value={"student_id": STUDENT_A_ROW},
        ) as repo,
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A_ROW}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert _error_code(response) == "ACCOUNT_INACTIVE"
    repo.assert_not_called()


@pytest.mark.parametrize("principal,label", DEACTIVATED_USERS)
def test_deactivated_staff_and_faculty_cannot_ingest(
    principal: dict, label: str
) -> None:
    with (
        _as(principal),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch(
            "app.api.knowledge.ingestion.get_knowledge_source",
            return_value=_source_row(INST_A),
        ),
        patch("app.api.knowledge.ingestion.ingest_document", new=AsyncMock()) as ingest,
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_A},
        )
    assert response.status_code == 403, label
    assert _error_code(response) == "ACCOUNT_INACTIVE", label
    ingest.assert_not_called()


@pytest.mark.parametrize("principal,label", DEACTIVATED_USERS)
def test_deactivated_staff_and_faculty_cannot_use_the_ai_assistant(
    principal: dict, label: str
) -> None:
    with (
        _as(principal),
        patch("app.main.process_chat_request", return_value=None) as process,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "hello", "institution_id": INST_A},
        )
    assert response.status_code == 403, label
    assert _error_code(response) == "ACCOUNT_INACTIVE", label
    process.assert_not_called()
