"""Organization and institution foundation regressions: physical."""

from __future__ import annotations

from .support import (
    pytest,
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
