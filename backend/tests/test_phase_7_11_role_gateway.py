"""Focused server-side contract checks for the Phase 7.11 role gateway."""

import pytest

from app.core.errors import AppError
from app.core.security import SUPPORTED_ROLES, require_roles, resolve_primary_role


def test_super_admin_is_a_server_resolved_platform_role() -> None:
    assert SUPPORTED_ROLES[0] == "super_admin"
    assert resolve_primary_role(["super_admin"]) == "super_admin"
    assert resolve_primary_role(["student", "admin", "super_admin"]) == "super_admin"


def test_existing_role_resolution_is_unchanged_without_super_admin() -> None:
    assert resolve_primary_role(["student", "admin"]) == "admin"
    assert resolve_primary_role(["faculty", "staff"]) == "staff"
    assert resolve_primary_role(["student"]) == "student"


@pytest.mark.asyncio
async def test_super_admin_is_not_implicitly_granted_tenant_admin_access() -> None:
    admin_guard = require_roles("admin")

    with pytest.raises(AppError) as exc_info:
        await admin_guard({"roles": ["super_admin"], "institution_id": None})

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"

