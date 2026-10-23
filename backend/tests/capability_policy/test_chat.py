"""Test chat."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

from .principals import (
    AUTH_HEADERS,
    INST_A,
    STAFF_A_USER,
    client,
)

from .support import (
    _as,
    _clean_dependencies,
)


def test_staff_reaches_the_approval_queue_within_its_own_institution() -> None:
    """The ONE staff-specific operational capability is proven reachable."""
    with (
        _as(STAFF_A_USER),
        patch(
            "app.services.admin.admin_academics.academics_repo.list_pending_students",
            return_value=[],
        ) as repo,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200, response.text
    repo.assert_called_once()
    # The queue is pinned to the server-resolved institution, never a
    # client-supplied one.
    assert repo.call_args.args[1] == UUID(INST_A)
