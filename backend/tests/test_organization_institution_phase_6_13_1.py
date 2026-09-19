"""Phase 6.13.1 — Organization & Institution FOUNDATION tests.

Scope of this file is strictly the foundation:

    Organization 1 ──── N Institutions
            │                    │
            └──── Users ─────── Roles + Scope ──── Institution-specific data

Covered:
  * schema contract of the Phase 6.13 migration (organizations table,
    institutions.organization_id NOT NULL + FK, legacy backfill,
    status -> is_active single source of truth, ADDITIVE role scope columns,
    non-destructive / idempotent DDL)
  * organization -> institution relationship (repository + authorization)
  * organization isolation (org A admin can never touch org B)
  * institution isolation (institution A1 can never touch institution A2)
  * server-side scope resolution — a client-supplied scope id is never trusted
  * compatibility of EXISTING authentication, RBAC, student authentication,
    PUBLIC_USER_ID and public chat (nothing in this phase replaces them)

NOT covered here (deliberately out of scope for 6.13.1): organization
registration, institution registration, join/membership approval workflows
(Phase 6.13.2+).

Physical (live database) verification lives in a skip-by-default class at the
bottom of this file, mirroring the project's existing
``test_physical_validation_phase_4_4.py`` opt-in convention. No credentials are
hardcoded — the app's own service-role configuration is reused, and every check
in that class is READ-ONLY.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.core.security import (
    PUBLIC_USER_ID,
    get_current_user,
    require_roles,
    scope_tenant,
)
from app.repositories import tenancy as tenancy_repo
from app.services import authorization as authz
from app.services import public_chat
from app.services.student_auth import SafeAuthFailure, _assert_institution_active

_ROOT = Path(__file__).resolve().parents[2]
PHASE_6_13_MIGRATION = (
    _ROOT
    / "supabase"
    / "migrations"
    / "20260915000000_phase_6_13_organization_institution_tenancy.sql"
)

# ---------------------------------------------------------------------------
# Stable identifiers used across the tests
# ---------------------------------------------------------------------------

ORG_A = "a0000000-0000-0000-0000-00000000000a"
ORG_B = "a0000000-0000-0000-0000-00000000000b"
INST_A1 = "b0000000-0000-0000-0000-0000000000a1"
INST_A2 = "b0000000-0000-0000-0000-0000000000a2"
INST_B1 = "b0000000-0000-0000-0000-0000000000b1"
USER_ID = "c0000000-0000-0000-0000-000000000001"
JOIN_REQUEST_ID = "d0000000-0000-0000-0000-000000000001"


def _sql() -> str:
    return PHASE_6_13_MIGRATION.read_text(encoding="utf-8")


def _context(
    *,
    role: str = "admin",
    scope_type: str,
    organization_id: str | None = None,
    institution_id: str | None = None,
    scope_id: str | None = None,
) -> dict:
    """Build a resolved authorization context (as ``resolve_authorization_context``
    would return it server-side)."""
    return {
        "user_id": USER_ID,
        "email": "user@example.com",
        "roles": [role],
        "scope_type": scope_type,
        "scope_id": scope_id or organization_id or institution_id,
        "organization_id": organization_id,
        "institution_id": institution_id,
    }


# ============================================================================
# 1. SCHEMA CONTRACT — organization -> institution foundation
# ============================================================================


def test_migration_declares_the_organization_foundation() -> None:
    sql = _sql()
    assert 'CREATE TABLE IF NOT EXISTS "public"."organizations"' in sql
    for column in (
        '"organization_id"',
        '"name"',
        '"organization_code"',
        '"official_email"',
        '"contact_information"',
        '"status"',
        '"created_at"',
        '"updated_at"',
    ):
        assert column in sql, f"organizations.{column} missing from the migration"
    assert 'ADD CONSTRAINT "organizations_pkey" PRIMARY KEY ("organization_id")' in sql
    assert (
        'ADD CONSTRAINT "organizations_organization_code_key" UNIQUE ("organization_code")'
        in sql
    )


def test_migration_extends_the_existing_institution_table_only() -> None:
    """The institution table is EXTENDED — never recreated (existing ids/data kept)."""
    sql = _sql()
    assert 'CREATE TABLE IF NOT EXISTS "public"."institutions"' not in sql
    assert 'ADD COLUMN IF NOT EXISTS "organization_id" uuid' in sql
    assert 'ADD COLUMN IF NOT EXISTS "status" text' in sql


def test_every_institution_belongs_to_exactly_one_organization() -> None:
    sql = _sql()
    assert "institutions_organization_id_fkey" in sql
    assert 'REFERENCES "public"."organizations" ("organization_id")' in sql
    assert 'ALTER COLUMN "organization_id" SET NOT NULL' in sql


def test_migration_backfills_legacy_institutions_without_rewriting_ids() -> None:
    sql = _sql()
    # One placeholder organization groups pre-existing institutions ...
    assert "LEGACY-INSTITUTIONS" in sql
    assert 'UPDATE "public"."institutions"' in sql
    assert 'WHERE "organization_id" IS NULL' in sql
    # ... and the backfill is idempotent / does not delete anything.
    assert "orphan_count = 0 THEN" in sql
    assert "DROP TABLE" not in sql
    assert "DELETE FROM" not in sql
    assert "TRUNCATE" not in sql


def test_migration_keeps_is_active_as_the_locked_compatibility_flag() -> None:
    """status is authoritative; is_active stays for the locked 6.2/6.3/6.5 paths."""
    sql = _sql()
    assert "trg_phase613_institutions_status" in sql
    assert "phase613_sync_institution_status" in sql
    assert 'NEW."is_active" := true' in sql
    assert 'NEW."is_active" := false' in sql
    assert "institutions_status_check" in sql
    for status_value in (
        "'pending'::text",
        "'active'::text",
        "'suspended'::text",
        "'rejected'::text",
    ):
        assert status_value in sql


def test_migration_adds_role_scope_additively_without_new_roles() -> None:
    sql = _sql()
    assert 'ADD COLUMN IF NOT EXISTS "scope_type" text' in sql
    assert 'ADD COLUMN IF NOT EXISTS "scope_id" uuid' in sql
    assert 'ADD COLUMN IF NOT EXISTS "scope_organization_id" uuid' in sql
    assert "user_roles_scope_check" in sql
    assert "trg_phase613_user_roles_scope" in sql
    # No new role vocabulary is introduced by this phase.
    assert 'INSERT INTO "public"."roles"' not in sql


def test_migration_enforces_span_integrity_guards() -> None:
    sql = _sql()
    assert "phase613_assert_child_organization" in sql
    assert "phase613_assert_role_scope" in sql
    assert "trg_phase613_join_request_organization" in sql
    assert "trg_phase613_membership_request_organization" in sql


def test_institution_id_remains_the_only_tenant_key() -> None:
    sql = _sql()
    assert 'ADD COLUMN IF NOT EXISTS "tenant_id"' not in sql
    assert 'ADD COLUMN IF NOT EXISTS "organization_id"' in sql


def test_migration_plpgsql_never_double_quotes_trigger_records() -> None:
    """`"NEW"."col"` is rejected by Postgres (42601) — the same defect class as
    the documented Phase 6.8 migration fix. This test keeps the migration
    applicable to a real database."""
    sql = _sql()
    assert '"NEW"' not in sql
    assert '"OLD"' not in sql
    assert 'NEW."institution_id"' in sql
    assert 'NEW."scope_type"' in sql


def test_migration_is_re_runnable() -> None:
    """Every ADD CONSTRAINT must be guarded, otherwise a second run fails with
    'multiple primary keys for table ... are not allowed' (42P16)."""
    sql = _sql()
    names = re.findall(r'ADD CONSTRAINT "(?P<name>\w+)"', sql)
    assert names, "expected constraint definitions"
    for name in names:
        guard = re.search(
            r"IF NOT EXISTS \(\s*SELECT 1 FROM \"pg_constraint\"\s*"
            r"WHERE \"conname\" = '" + re.escape(name) + r"'",
            sql,
        )
        assert guard is not None, f"{name} is not guarded (not re-runnable)"


# ============================================================================
# 2. ORGANIZATION -> INSTITUTION RELATIONSHIP (repository + resolution)
# ============================================================================


def test_organization_lookup_is_by_public_code_and_case_insensitive() -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value.ilike.return_value
    query.maybe_single.return_value.execute.return_value.data = {
        "organization_id": ORG_A
    }
    assert tenancy_repo.organization_code_exists(client, "nielit") is True
    client.table.assert_called_with("organizations")
    assert (
        client.table.return_value.select.return_value.ilike.call_args.args[0]
        == "organization_code"
    )


def test_list_institutions_for_organization_is_organization_scoped() -> None:
    client = MagicMock()
    rows = [{"institution_id": INST_A1, "organization_id": ORG_A}]
    query = client.table.return_value.select.return_value.eq.return_value
    query.order.return_value.execute.return_value.data = rows
    assert tenancy_repo.list_institutions_for_organization(client, ORG_A) == rows
    client.table.assert_called_with("institutions")
    assert client.table.return_value.select.return_value.eq.call_args.args == (
        "organization_id",
        ORG_A,
    )


def test_get_institution_organization_returns_the_owning_organization() -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value.eq.return_value
    query.maybe_single.return_value.execute.return_value.data = {
        "organization_id": ORG_A
    }
    assert tenancy_repo.get_institution_organization(client, INST_A1) == UUID(ORG_A)


def test_get_institution_organization_absent_row_resolves_to_none() -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value.eq.return_value
    query.maybe_single.return_value.execute.return_value.data = None
    assert tenancy_repo.get_institution_organization(client, INST_A1) is None


def test_insert_institution_carries_exactly_one_owning_organization() -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"institution_id": INST_A1, "organization_id": ORG_A}
    ]
    tenancy_repo.insert_institution(
        client,
        organization_id=ORG_A,
        name="NIELIT Imphal",
        code="nielit-imphal",
        email="imphal@nielit.example",
        address="Imphal, Manipur",
    )
    payload = client.table.return_value.insert.call_args.args[0]
    assert payload["organization_id"] == ORG_A
    assert payload["code"] == "NIELIT-IMPHAL"  # normalised; still globally unique
    # A new institution starts unavailable until its organization admits it.
    assert payload["status"] == "pending"
    assert payload["is_active"] is False


def test_remove_membership_on_reject_uses_the_existing_scope_columns() -> None:
    """Regression: user_roles stores scope_type/scope_id — never institution_id."""
    client = MagicMock()
    tenancy_repo.remove_membership_on_reject(
        client, user_id=USER_ID, institution_id=INST_A1
    )
    client.table.assert_called_once_with("user_roles")
    node = client.table.return_value.delete.return_value.eq
    filters = []
    for _ in range(3):
        filters.extend(args for args, _kwargs in node.call_args_list)
        node = node.return_value.eq
    assert filters == [
        ("user_id", USER_ID),
        ("scope_type", "institution"),
        ("scope_id", INST_A1),
    ]


def test_resolve_authorization_context_links_user_to_organization_and_institution() -> None:
    """JWT sub -> users.user_id -> user_roles(+scope) -> institution -> organization."""
    rows = [
        {
            "role_id": "e0000000-0000-0000-0000-000000000001",
            "role_name": "admin",
            "is_active": True,
            "scope_type": "institution",
            "scope_id": INST_A1,
            "scope_organization_id": ORG_A,
        }
    ]
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ) as resolver,
    ):
        context = authz.resolve_authorization_context(
            {"user_id": USER_ID, "institution_id": None}
        )

    assert context["roles"] == ["admin"]
    assert context["scope_type"] == "institution"
    assert context["scope_id"] == INST_A1
    assert context["institution_id"] == INST_A1
    assert context["organization_id"] == ORG_A
    resolver.assert_called_once()


def test_resolve_authorization_context_prefers_the_widest_privilege_scope() -> None:
    rows = [
        {
            "role_name": "faculty",
            "is_active": True,
            "scope_type": "institution",
            "scope_id": INST_A1,
            "scope_organization_id": ORG_A,
        },
        {
            "role_name": "admin",
            "is_active": True,
            "scope_type": "organization",
            "scope_id": ORG_A,
            "scope_organization_id": ORG_A,
        },
    ]
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
    ):
        context = authz.resolve_authorization_context(
            {"user_id": USER_ID, "institution_id": INST_A1}
        )

    assert context["scope_type"] == "organization"
    assert context["scope_id"] == ORG_A
    assert context["organization_id"] == ORG_A
    assert set(context["roles"]) == {"admin", "faculty"}


def test_organization_scope_is_taken_from_the_database_not_the_request() -> None:
    """A client-injected organization/scope id is never trusted."""
    rows = [
        {
            "role_name": "student",
            "is_active": True,
            "scope_type": None,
            "scope_id": None,
            "scope_organization_id": None,
        }
    ]
    client_supplied = {
        "user_id": USER_ID,
        "institution_id": INST_A1,
        # Attacker-controlled fields that must be ignored:
        "scope_type": "organization",
        "scope_id": ORG_B,
        "organization_id": ORG_B,
    }
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        context = authz.resolve_authorization_context(client_supplied)

    # Resolved server-side: the student's own institution (A1) inside org A.
    assert context["scope_id"] == INST_A1
    assert context["organization_id"] == ORG_A
    assert context["scope_id"] != ORG_B
    assert context["organization_id"] != ORG_B


def test_institution_scope_organization_comes_from_the_institution_row() -> None:
    """A stale/hostile denormalised scope_organization_id cannot widen the scope."""
    rows = [
        {
            "role_name": "admin",
            "is_active": True,
            "scope_type": "institution",
            "scope_id": INST_A1,
            "scope_organization_id": ORG_B,
        }
    ]
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        context = authz.resolve_authorization_context(
            {"user_id": USER_ID, "institution_id": None}
        )

    assert context["organization_id"] == ORG_A
    assert context["scope_id"] == INST_A1


# ============================================================================
# 3. ISOLATION — organization A never reaches organization B, and
#    institution A1 never reaches institution A2
# ============================================================================


def _expect(error_code: str, func, *args, **kwargs) -> None:
    with pytest.raises(AppError) as excinfo:
        func(*args, **kwargs)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == error_code


def test_org_admin_can_manage_its_own_organization() -> None:
    authz.assert_can_manage_organization(
        {"user_id": USER_ID},
        _context(scope_type=authz.ORGANIZATION, organization_id=ORG_A),
        ORG_A,
    )


def test_org_admin_cannot_manage_another_organization() -> None:
    _expect(
        "ORGANIZATION_MISMATCH",
        authz.assert_can_manage_organization,
        {"user_id": USER_ID},
        _context(scope_type=authz.ORGANIZATION, organization_id=ORG_A),
        ORG_B,
    )


def test_institution_admin_cannot_manage_its_own_organization() -> None:
    """Institution admins manage THEIR institution, never the organization."""
    _expect(
        "FORBIDDEN",
        authz.assert_can_manage_organization,
        {"user_id": USER_ID},
        _context(
            scope_type=authz.INSTITUTION,
            organization_id=ORG_A,
            institution_id=INST_A1,
        ),
        ORG_A,
    )


def test_non_admins_can_manage_neither_organization_nor_institution() -> None:
    staff = _context(
        role="staff",
        scope_type=authz.INSTITUTION,
        organization_id=ORG_A,
        institution_id=INST_A1,
    )
    _expect(
        "FORBIDDEN",
        authz.assert_can_manage_organization,
        {"user_id": USER_ID},
        staff,
        ORG_A,
    )
    _expect(
        "FORBIDDEN",
        authz.assert_can_manage_institution,
        {"user_id": USER_ID},
        staff,
        INST_A1,
    )


def test_platform_scope_keeps_its_unrestricted_authority() -> None:
    platform = _context(scope_type=authz.PLATFORM)
    authz.assert_can_manage_organization({"user_id": USER_ID}, platform, ORG_B)
    authz.assert_can_manage_institution({"user_id": USER_ID}, platform, INST_B1)


def test_org_admin_manages_only_institutions_of_its_own_organization() -> None:
    context = _context(scope_type=authz.ORGANIZATION, organization_id=ORG_A)
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        authz.assert_can_manage_institution({"user_id": USER_ID}, context, INST_A1)

    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_B)
        ),
    ):
        _expect(
            "ORGANIZATION_MISMATCH",
            authz.assert_can_manage_institution,
            {"user_id": USER_ID},
            context,
            INST_B1,
        )


def test_institution_admin_manages_only_its_own_institution() -> None:
    context = _context(
        scope_type=authz.INSTITUTION,
        organization_id=ORG_A,
        institution_id=INST_A1,
    )
    authz.assert_can_manage_institution({"user_id": USER_ID}, context, INST_A1)
    _expect(
        "TENANT_MISMATCH",
        authz.assert_can_manage_institution,
        {"user_id": USER_ID},
        context,
        INST_A2,
    )
    _expect(
        "TENANT_MISMATCH",
        authz.assert_can_manage_institution,
        {"user_id": USER_ID},
        context,
        INST_B1,
    )


def test_org_b_admin_cannot_manage_org_a_institutions() -> None:
    context = _context(scope_type=authz.ORGANIZATION, organization_id=ORG_B)
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        _expect(
            "ORGANIZATION_MISMATCH",
            authz.assert_can_manage_institution,
            {"user_id": USER_ID},
            context,
            INST_A1,
        )


def test_institution_scoped_account_can_never_decide_join_requests() -> None:
    """Approving an institution join is the EXCLUSIVE right of the org admin."""
    context = _context(
        scope_type=authz.INSTITUTION,
        organization_id=ORG_A,
        institution_id=INST_A1,
    )
    _expect(
        "ORGANIZATION_MISMATCH",
        authz.assert_can_decide_join_request,
        context,
        {"organization_id": ORG_A, "institution_id": INST_A1},
    )


def test_join_request_decisions_are_limited_to_the_owning_organization() -> None:
    context = _context(scope_type=authz.ORGANIZATION, organization_id=ORG_A)
    authz.assert_can_decide_join_request(context, {"organization_id": ORG_A})
    _expect(
        "ORGANIZATION_MISMATCH",
        authz.assert_can_decide_join_request,
        context,
        {"organization_id": ORG_B},
    )


def test_join_request_decision_requires_the_admin_role() -> None:
    _expect(
        "FORBIDDEN",
        authz.assert_can_decide_join_request,
        _context(role="faculty", scope_type=authz.ORGANIZATION, organization_id=ORG_A),
        {"organization_id": ORG_A},
    )


def test_platform_admin_can_decide_any_join_request() -> None:
    authz.assert_can_decide_join_request(
        _context(scope_type=authz.PLATFORM), {"organization_id": ORG_A}
    )


def test_assert_institution_in_organization_rejects_cross_organization() -> None:
    authz.assert_institution_in_organization(ORG_A, ORG_A)
    _expect(
        "ORGANIZATION_MISMATCH", authz.assert_institution_in_organization, ORG_A, ORG_B
    )
    _expect(
        "ORGANIZATION_MISMATCH", authz.assert_institution_in_organization, None, ORG_A
    )
    _expect(
        "ORGANIZATION_MISMATCH", authz.assert_institution_in_organization, ORG_A, None
    )


# ============================================================================
# 4. COMPATIBILITY — the locked 6.2-6.11 layers are extended, not replaced
# ============================================================================


def test_public_user_id_constant_is_unchanged() -> None:
    assert PUBLIC_USER_ID == UUID("00000000-0000-0000-0000-000000000001")


def test_get_user_by_auth_id_projection_never_needs_the_scope_columns() -> None:
    """Authentication must keep working before AND after the 6.13 migration."""
    from app.db import supabase as supabase_db

    client = MagicMock()
    response = MagicMock()
    response.data = {
        "user_id": USER_ID,
        "auth_user_id": "auth-1",
        "email": "student@example.com",
        "user_roles": [{"roles": {"name": "student", "is_active": True}}],
        # PostgREST embeds a one-to-one relation as an object ...
        "students": {"institution_id": INST_A1},
    }
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = response

    with patch.object(supabase_db, "get_admin_client", return_value=client):
        result = asyncio.run(supabase_db.get_user_by_auth_id("auth-1"))

    projection = client.table.return_value.select.call_args.args[0]
    assert "user_roles(roles(name, is_active))" in projection
    assert "students(institution_id)" in projection
    assert "scope_type" not in projection
    assert result == {
        "user_id": USER_ID,
        "auth_user_id": "auth-1",
        "email": "student@example.com",
        "roles": ["student"],
        "institution_id": INST_A1,
    }


def test_get_user_by_auth_id_handles_list_embeds_and_tenantless_accounts() -> None:
    from app.db import supabase as supabase_db

    client = MagicMock()
    response = MagicMock()
    response.data = {
        "user_id": USER_ID,
        "auth_user_id": "auth-2",
        "email": "admin@example.com",
        # ... and as a list when PostgREST cannot infer the cardinality.
        "students": [{"institution_id": INST_B1}],
        "user_roles": [
            {"roles": {"name": "admin", "is_active": True}},
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
        "students": None,
        "user_roles": [],
    }
    with patch.object(supabase_db, "get_admin_client", return_value=client):
        tenantless = asyncio.run(supabase_db.get_user_by_auth_id("auth-3"))

    # Platform-level accounts keep the locked "no tenant" behaviour.
    assert tenantless["institution_id"] is None
    assert tenantless["roles"] == []


def test_get_current_user_contract_is_unchanged() -> None:
    with pytest.raises(AppError) as excinfo:
        asyncio.run(get_current_user(None))
    assert (excinfo.value.status_code, excinfo.value.code) == (401, "AUTH_REQUIRED")

    with (
        patch(
            "app.core.security.verify_jwt",
            return_value={"sub": "auth-1", "email": "user@example.com"},
        ),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(
                return_value={
                    "user_id": USER_ID,
                    "auth_user_id": "auth-1",
                    "email": "user@example.com",
                    "roles": ["admin"],
                    "institution_id": INST_A1,
                }
            ),
        ),
    ):
        current_user = asyncio.run(get_current_user("Bearer test.token"))

    # The 6.13 scope layer is resolved separately — auth itself stays scope-free.
    assert current_user == {
        "user_id": USER_ID,
        "auth_user_id": "auth-1",
        "email": "user@example.com",
        "roles": ["admin"],
        "institution_id": INST_A1,
    }


def test_require_roles_is_unchanged_by_the_scope_extension() -> None:
    dependency = require_roles("admin")
    institution_admin = {
        "user_id": USER_ID,
        "roles": ["admin"],
        "institution_id": INST_A1,
    }
    # An institution-scoped admin still passes role-based RBAC; narrowing is
    # enforced by the Phase 6.13 authorization layer, not by require_roles().
    assert asyncio.run(dependency(institution_admin)) is institution_admin

    with pytest.raises(AppError) as excinfo:
        asyncio.run(dependency({"user_id": USER_ID, "roles": ["student"]}))
    assert (excinfo.value.status_code, excinfo.value.code) == (403, "FORBIDDEN")


def test_locked_tenant_helpers_still_reject_cross_institution() -> None:
    tenant_a = {"user_id": USER_ID, "roles": ["student"], "institution_id": INST_A1}
    assert scope_tenant(tenant_a, INST_A1) == UUID(INST_A1)
    _expect("TENANT_MISMATCH", scope_tenant, tenant_a, INST_A2)


def test_student_authentication_still_gated_by_institution_is_active() -> None:
    with patch(
        "app.services.student_auth._get_institution",
        return_value={"is_active": True},
    ):
        _assert_institution_active(MagicMock(), UUID(INST_A1))

    for inactive in ({"is_active": False}, None):
        with patch("app.services.student_auth._get_institution", return_value=inactive):
            with pytest.raises(SafeAuthFailure):
                _assert_institution_active(MagicMock(), UUID(INST_A1))


def test_public_chat_requires_no_authentication() -> None:
    source = inspect.getsource(public_chat)
    assert "PUBLIC_USER_ID" in source
    assert "get_current_user" not in source
    assert "verify_jwt" not in source
    assert list(inspect.signature(public_chat.process_chat_request).parameters) == [
        "request",
        "context",
        "provider",
    ]


def test_public_chat_owns_every_public_turn_with_public_user_id() -> None:
    source = inspect.getsource(public_chat.process_chat_request)
    assert "user_id = PUBLIC_USER_ID" in source


def test_public_chat_institution_id_is_now_validated_server_side() -> None:
    """Phase 6.13.8: the public path now validates institution_id before use.

    The prior known limitation (public chat accepted institution_id but did not
    enforce institution-specific RAG filtering) is closed in this phase:

    * the client-supplied institution_id is validated server-side by
      ``_validate_public_institution`` (exists, ACTIVE, belongs to a valid org),
    * the validated institution is used as the retrieval scope,
    * retrieved chunks are post-filtered at the data-access boundary to
      public knowledge sources only (``_filter_to_public_chunks``), so
      private / student / cross-institution documents can never enter the LLM
      context,
    * client-supplied scope overrides (``knowledge_source_id`` that belongs to
      another institution or is non-public) are rejected at the validation
      boundary.

    The public path still owns every turn with ``PUBLIC_USER_ID`` (unchanged
    invariant) — the additions are additive guards around the existing pipeline,
    not a redesign.
    """
    source = inspect.getsource(public_chat.process_chat_request)
    assert "institution_id=request.institution_id" in source
    # The public path now validates the institution before use.
    assert "_validate_public_institution" in source
    # The public path now filters retrieved chunks by public source_type.
    assert "_filter_to_public_chunks" in source
    # The public path rejects personal-data questions.
    assert "_reject_personal_query_if_needed" in source


def test_public_chat_is_now_exposed_as_an_http_route() -> None:
    """Phase 6.13.8: public chat is exposed at POST /api/v1/chat/public.

    The public chat service (``app.services.public_chat.process_chat_request``)
    was already wired in Phase 6.13.1; this phase adds the unauthenticated
    HTTP route so public AI is reachable without a login, while the protected
    endpoint remains ``POST /api/v1/generation/chat`` (authenticated).
    """
    from app.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    # FastAPI 0.141+ uses lazy _IncludedRouter expansion; the public route
    # may not appear in app.routes until the OpenAPI schema is built.
    if not any("public" in p for p in paths):
        schema = app.openapi()
        paths.update(schema.get("paths", {}).keys())
    public_paths = {path for path in paths if "public" in path}
    assert public_paths, (
        "Phase 6.13.8 must expose the public chat route. "
        "The project convention is POST /api/v1/chat/public."
    )
    # The route must be present; verify it is a chat-style path rather than an
    # unrelated admin/internal path.
    assert any("/chat" in path for path in public_paths), (
        public_paths
    )


# ============================================================================
# 5. PHYSICAL (LIVE DATABASE) VALIDATION — opt-in, mirrors project convention
# ============================================================================
# These checks verify the Phase 6.13 foundation against the REAL remote schema:
# the organizations table, institutions.organization_id NOT NULL + FK, the
# legacy backfill, the scope columns, and that pre-existing data survived.
# They are skipped in the default suite and run only when a reviewer opts in,
# matching the existing ``test_attendance_phase_6_7.py`` pattern. No credentials
# are hardcoded — the app's ``.env`` service-role config is reused. Every check
# is READ-ONLY: it never inserts, updates or deletes anything.


@pytest.mark.skip(reason="Live-database validation requires explicit manual opt-in")
class TestOrganizationInstitutionPhysicalValidationPhase6131:
    """Live-database verification of the Phase 6.13.1 tenancy foundation."""

    def test_live_organizations_table_exists(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        rows = db.table("organizations").select(
            "organization_id, name, organization_code, official_email, "
            "contact_information, status, created_at, updated_at"
        ).execute().data
        assert rows is not None
        for row in rows:
            assert row["organization_id"]
            assert row["organization_code"]
            assert row["status"]

    def test_live_every_institution_has_exactly_one_organization(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        institutions = db.table("institutions").select(
            "institution_id, code, organization_id, status, is_active"
        ).execute().data
        assert institutions, "the live database must still hold its institutions"
        organizations = {
            row["organization_id"]
            for row in db.table("organizations").select("organization_id").execute().data
        }
        for institution in institutions:
            # NOT NULL + FK: an orphan institution must be impossible.
            assert institution["organization_id"] in organizations
            assert institution["status"] in {"pending", "active", "suspended", "rejected"}
            # status -> is_active single source of truth (trigger-derived).
            assert institution["is_active"] is (institution["status"] == "active")

    def test_live_role_scope_columns_exist_and_are_consistent(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        rows = db.table("user_roles").select(
            "user_id, role_id, scope_type, scope_id, scope_organization_id"
        ).execute().data
        assert rows is not None
        for row in rows:
            scope_type = row["scope_type"]
            if scope_type == "platform":
                assert row["scope_id"] is None
                assert row["scope_organization_id"] is None
            elif scope_type == "organization":
                assert row["scope_id"] == row["scope_organization_id"]
            elif scope_type == "institution":
                institution = (
                    db.table("institutions")
                    .select("organization_id")
                    .eq("institution_id", row["scope_id"])
                    .maybe_single()
                    .execute()
                    .data
                )
                assert institution["organization_id"] == row["scope_organization_id"]

    def test_live_existing_data_survived_the_migration(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        for table in (
            "users",
            "students",
            "documents",
            "knowledge_chunks",
            "conversations",
        ):
            count = db.table(table).select("*", count="exact").limit(1).execute().count
            assert count is not None and count > 0, f"{table} lost its data"
