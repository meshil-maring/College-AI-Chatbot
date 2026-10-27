"""Organization and institution foundation regressions: schema."""

from __future__ import annotations

from .support import (
    _sql,
    re,
)


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
