"""Test audit."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

from .support import (
    ADMIN_A,
    ADMIN_B,
    INST_A,
    RESOURCE_ID,
    _clean_dependencies,
    authorized_admin_endpoint,
    client,
    conflicting_admin,
)


def test_audit_list_is_forced_to_current_actor(authorized_admin_endpoint) -> None:
    with patch("app.api.admin.audit.list_audit_entries", return_value=[]) as audit:
        response = client.get("/api/v1/admin/audit-logs")
    assert response.status_code == 200
    audit.assert_called_once()
    assert audit.call_args.args == (authorized_admin_endpoint,)
    assert audit.call_args.kwargs["actor_user_id"] == ADMIN_A
    assert audit.call_args.kwargs["institution_id"] == UUID(INST_A)


def test_cross_actor_audit_detail_and_filter_are_denied(authorized_admin_endpoint) -> None:
    with (
        patch(
            "app.api.admin.audit.get_audit_entry",
            return_value={
                "audit_id": RESOURCE_ID,
                "actor_user_id": ADMIN_B,
                "institution_id": INST_A,
            },
        ) as get_entry,
        patch("app.api.admin.audit.list_audit_entries", return_value=[]) as listing,
    ):
        detail = client.get(f"/api/v1/admin/audit-logs/{RESOURCE_ID}")
        filtered = client.get(f"/api/v1/admin/audit-logs?actor_user_id={ADMIN_B}")
    assert detail.status_code == 403
    assert filtered.status_code == 403
    get_entry.assert_called_once_with(authorized_admin_endpoint, UUID(RESOURCE_ID))
    listing.assert_not_called()
