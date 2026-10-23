"""Test tenant scope."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .principals import (
    AUTH_HEADERS,
    INST_A,
    INST_B,
    KNOWLEDGE_SOURCE_B,
    STAFF_AND_FACULTY_USERS,
    STAFF_OR_FACULTY,
    _principal,
    client,
)

from .support import (
    _as,
    _clean_dependencies,
    _error_code,
    _source_row,
    _tenantless_principal,
)


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_cannot_ingest_into_another_institution(
    principal: dict, label: str
) -> None:
    """Institution A staff/faculty -> Institution B knowledge source is denied."""
    with (
        _as(principal),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch(
            "app.api.knowledge.ingestion.get_knowledge_source",
            return_value=_source_row(INST_B),
        ),
        patch("app.api.knowledge.ingestion.ingest_document", new=AsyncMock()) as ingest,
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_B},
        )
    assert response.status_code == 403, label
    assert _error_code(response) == "TENANT_MISMATCH", label
    ingest.assert_not_called()


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_cannot_chat_as_another_institution(
    principal: dict, label: str
) -> None:
    """AI Assistant tenant isolation: a client-supplied institution cannot win."""
    with (
        _as(principal),
        patch("app.main.process_chat_request", return_value=None) as process,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "hello", "institution_id": INST_B},
        )
    assert response.status_code == 403, label
    assert _error_code(response) == "TENANT_MISMATCH", label
    process.assert_not_called()


@pytest.mark.parametrize("role", STAFF_OR_FACULTY)
def test_platform_scoped_principal_is_not_unrestricted_authority(role: str) -> None:
    """A tenant-less staff/faculty grant fails closed; it is never platform power.

    The role exists but its platform scope is not an institution scope, so the
    request is refused BEFORE any queue is read.
    """
    with (
        _as(_tenantless_principal(role)),
        patch(
            "app.services.admin.admin_academics.academics_repo.list_pending_students",
            return_value=[],
        ) as repo,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _error_code(response) in {"FORBIDDEN", "SCOPE_MISSING"}
    repo.assert_not_called()


@pytest.mark.parametrize("role", STAFF_OR_FACULTY)
def test_suspended_institution_fails_closed_for_staff_and_faculty(role: str) -> None:
    """An inactive institution revokes staff/faculty capability immediately."""
    principal = _principal(f"72900000-0000-0000-0000-00000000000{role}", role, INST_A)
    with (
        _as(principal, institution_active=False),
        patch(
            "app.services.admin.admin_academics.academics_repo.list_pending_students",
            return_value=[],
        ) as repo,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _error_code(response) in {"FORBIDDEN", "TENANT_INACTIVE"}
    repo.assert_not_called()
