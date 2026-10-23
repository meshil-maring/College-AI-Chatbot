def test_phase_8_1_migration_has_rls_atomic_audit_and_scoped_constraints() -> None:
    from pathlib import Path

    migration = (
        Path(__file__).resolve().parents[3]
        / "supabase"
        / "migrations"
        / "20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql"
    ).read_text(encoding="utf-8")
    assert 'CREATE TABLE IF NOT EXISTS "public"."user_permission_grants"' in migration
    assert (
        'CREATE TABLE IF NOT EXISTS "public"."faculty_section_assignments"' in migration
    )
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert '"phase81_manage_staff_permission_grants"' in migration
    assert '"phase81_manage_faculty_section_assignment"' in migration
    assert '"phase81_assign_institution_role_audited"' in migration
    assert "'permission.grant'" in migration
    assert "'permission.revoke'" in migration
    assert "'faculty.assignment.assign'" in migration
    assert "'faculty.assignment.revoke'" in migration
    assert "phase81_admin_audit_append_only" in migration
