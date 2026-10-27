"""Guard the least-privilege behavior of resolved authentication fixtures."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.errors import AppError
from app.core.security.identity import get_current_user
from .principals import institution_grant, resolved_principal


def test_explicit_empty_grants_remain_empty():
    principal = resolved_principal({
        "roles": ["admin"], "effective_permissions": [],
        "role_assignments": [institution_grant("admin", "tenant", [])],
    })
    assert principal["effective_permissions"] == []
    assert principal["role_assignments"][0]["permissions"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["permissions_resolved", "scoped_permissions_resolved"])
async def test_explicit_unresolved_permissions_still_fail_authentication(field):
    principal = resolved_principal({"roles": ["admin"], "user_id": "user", field: False})
    with (
        patch("app.core.security.tokens.verify_jwt", return_value={"sub": "auth-user"}),
        patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=principal)),
        pytest.raises(AppError) as failure,
    ):
        await get_current_user("Bearer token")
    assert failure.value.status_code == 403
