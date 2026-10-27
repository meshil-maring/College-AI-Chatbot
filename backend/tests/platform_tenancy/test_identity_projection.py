"""Organization and institution foundation regressions: identity projection."""

from __future__ import annotations

from .support import (
    INST_A1,
    INST_B1,
    MagicMock,
    ORG_A,
    ORG_B,
    PUBLIC_USER_ID,
    USER_ID,
    UUID,
    asyncio,
    patch,
)


# ============================================================================
# 4. COMPATIBILITY — the locked 6.2-6.11 layers are extended, not replaced
# ============================================================================


def test_public_user_id_constant_is_unchanged() -> None:
    assert PUBLIC_USER_ID == UUID("00000000-0000-0000-0000-000000000001")


def test_get_user_by_auth_id_projection_includes_authoritative_scope_columns() -> None:
    """Phase 7.20 projects scoped grants for downstream authorization."""
    from app.db import supabase as supabase_db

    client = MagicMock()
    response = MagicMock()
    response.data = {
        "user_id": USER_ID,
        "auth_user_id": "auth-1",
        "email": "student@example.com",
        "status": "active",
        "user_roles": [{
            "scope_type": "institution",
            "scope_id": INST_A1,
            "scope_organization_id": ORG_A,
            "roles": {"name": "student", "is_active": True},
        }],
        # PostgREST embeds a one-to-one relation as an object ...
        "students": {"institution_id": INST_A1},
    }
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = response

    with patch.object(supabase_db, "get_admin_client", return_value=client):
        result = asyncio.run(supabase_db.get_user_by_auth_id("auth-1"))

    projection = client.table.return_value.select.call_args.args[0]
    assert "scope_type" in projection
    assert "scope_id" in projection
    assert "students(institution_id)" in projection
    assert result["status"] == "active"
    assert result["roles"] == ["student"]
    assert result["institution_id"] == INST_A1
    assert result["role_assignments"][0]["scope_id"] == INST_A1


def test_get_user_by_auth_id_handles_list_embeds_and_tenantless_accounts() -> None:
    from app.db import supabase as supabase_db

    client = MagicMock()
    response = MagicMock()
    response.data = {
        "user_id": USER_ID,
        "auth_user_id": "auth-2",
        "email": "admin@example.com",
        "status": "active",
        # ... and as a list when PostgREST cannot infer the cardinality.
        "students": [{"institution_id": INST_B1}],
        "user_roles": [
            {
                "scope_type": "institution",
                "scope_id": INST_B1,
                "scope_organization_id": ORG_B,
                "roles": {"name": "admin", "is_active": True},
            },
            {"roles": {"name": "disabled", "is_active": False}},
        ],
    }
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = response

    with patch.object(supabase_db, "get_admin_client", return_value=client):
        result = asyncio.run(supabase_db.get_user_by_auth_id("auth-2"))

    assert result["roles"] == ["admin"]
    assert result["institution_id"] == INST_B1

    response.data = {
        "user_id": USER_ID,
        "auth_user_id": "auth-3",
        "email": "platform@example.com",
        "status": "active",
        "students": None,
        "user_roles": [],
    }
    with patch.object(supabase_db, "get_admin_client", return_value=client):
        tenantless = asyncio.run(supabase_db.get_user_by_auth_id("auth-3"))

    # Platform-level accounts keep the locked "no tenant" behaviour.
    assert tenantless["institution_id"] is None
    assert tenantless["roles"] == []
