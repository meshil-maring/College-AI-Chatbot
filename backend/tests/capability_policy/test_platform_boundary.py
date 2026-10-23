"""Test platform boundary."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .principals import (
    AUTH_HEADERS,
    INST_A,
    KNOWLEDGE_SOURCE_A,
    STAFF_AND_FACULTY_USERS,
    SUPER_ADMIN_USER,
    client,
)

from .support import (
    SUPER_ADMIN_MUST_NOT_REACH,
    _as,
    _clean_dependencies,
    _error_code,
)


@pytest.mark.parametrize("method,path", SUPER_ADMIN_MUST_NOT_REACH)
def test_super_admin_does_not_inherit_institution_staff_faculty_permissions(
    method: str, path: str
) -> None:
    """Platform authority does NOT imply institution staff/faculty capability."""
    with _as(SUPER_ADMIN_USER):
        response = client.request(method, path, headers=AUTH_HEADERS)
    assert response.status_code == 403, (path, response.status_code, response.text)
    assert _error_code(response) == "FORBIDDEN"


def test_super_admin_does_not_inherit_the_staff_faculty_ingestion_capability() -> None:
    with (
        _as(SUPER_ADMIN_USER),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.ingest_document", new=AsyncMock()) as ingest,
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_A},
        )
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"
    ingest.assert_not_called()


def test_super_admin_does_not_inherit_the_institution_chat_capability() -> None:
    with (
        _as(SUPER_ADMIN_USER),
        patch("app.main.process_chat_request", return_value=None) as process,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "hello", "institution_id": INST_A},
        )
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"
    process.assert_not_called()


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_are_still_denied_the_platform_surface(
    principal: dict, label: str
) -> None:
    """The boundary is symmetric: neither direction leaks."""
    with _as(principal):
        response = client.get("/api/v1/platform/institutions", headers=AUTH_HEADERS)
    assert response.status_code == 403, label
    assert _error_code(response) == "FORBIDDEN", label
