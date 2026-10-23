"""Test approval."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .principals import (
    AUTH_HEADERS,
    FACULTY_A_USER,
    INST_B,
    KNOWLEDGE_SOURCE_A,
    STAFF_AND_FACULTY_USERS,
    STAFF_A_USER,
    STUDENT_A_ROW,
    STUDENT_A_USER,
    STUDENT_B_ROW,
    client,
)

from .support import (
    ADMIN_ONLY_ROUTES,
    _as,
    _clean_dependencies,
    _error_code,
)


@pytest.mark.parametrize("method,path", ADMIN_ONLY_ROUTES)
@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_are_denied_every_admin_only_route(
    method: str, path: str, principal: dict, label: str
) -> None:
    """Neither Staff nor Faculty reaches any admin-only capability."""
    with _as(principal):
        response = client.request(method, path, headers=AUTH_HEADERS)
    assert response.status_code == 403, (label, path, response.status_code)
    assert _error_code(response) == "FORBIDDEN", (label, path)


def test_student_is_denied_the_staff_approval_capability() -> None:
    """Student -> staff/faculty capability is denied."""
    with _as(STUDENT_A_USER):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"


def test_student_is_denied_the_faculty_ingestion_capability() -> None:
    """The shared staff/faculty ingestion capability is not student-reachable."""
    with (
        _as(STUDENT_A_USER),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=None),
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_A},
        )
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/admin/students/pending"),
        ("POST", f"/api/v1/admin/students/{STUDENT_A_ROW}/approve"),
        ("POST", f"/api/v1/admin/students/{STUDENT_A_ROW}/reject"),
    ],
)
def test_faculty_is_denied_the_staff_only_approval_capability(
    method: str, path: str
) -> None:
    """Faculty is NOT part of the admin/staff approval boundary.

    This is the ONE capability that distinguishes Staff from Faculty today.
    """
    with _as(FACULTY_A_USER):
        response = client.request(method, path, headers=AUTH_HEADERS)
    assert response.status_code == 403, (path, response.status_code)
    assert _error_code(response) == "FORBIDDEN"


def test_staff_cannot_redirect_the_approval_queue_to_another_institution() -> None:
    """Staff A -> Institution B is denied at the query parameter."""
    with (
        _as(STAFF_A_USER),
        patch(
            "app.services.admin.admin_academics.academics_repo.list_pending_students",
            return_value=[],
        ) as repo,
    ):
        response = client.get(
            "/api/v1/admin/students/pending",
            headers=AUTH_HEADERS,
            params={"institution_id": INST_B},
        )
    assert response.status_code == 403
    assert _error_code(response) == "TENANT_MISMATCH"
    repo.assert_not_called()


def test_staff_cannot_approve_a_student_from_another_institution() -> None:
    """Staff A -> Institution B student row is denied.

    The real service runs (only the data layer is doubled) so the tenant check
    inside ``_resolve_approval_target`` is genuinely exercised.
    """
    with (
        _as(STAFF_A_USER),
        patch(
            "app.services.admin.admin_academics.get_admin_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.admin.admin_academics.academics_repo.get_student_for_approval",
            return_value={
                "student_id": STUDENT_B_ROW,
                "institution_id": INST_B,
                "approval_status": "pending",
                "user_id": "u-1",
            },
        ) as target,
        patch(
            "app.services.admin.admin_academics.academics_repo.set_student_approval_status",
            return_value=None,
        ) as write,
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B_ROW}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert _error_code(response) == "TENANT_MISMATCH"
    target.assert_called_once()
    write.assert_not_called()
