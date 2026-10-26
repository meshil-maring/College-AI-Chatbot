"""Offline release safeguards; these tests intentionally never execute SQL."""
from pathlib import Path
import re
import runpy


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "supabase/migration_sources/academic_foundations"
BUILDER = ROOT / "scripts/maintenance/migrations/build_academic_foundations.py"


def sql(name):
    return (SOURCE / f"{name}.sql").read_text(encoding="utf-8")


def test_generated_forward_migration_matches_ordered_bounded_sources():
    builder = runpy.run_path(str(BUILDER))
    target, expected = builder["render"]()
    assert target.name == "20261023010000_academic_foundations.sql"
    assert target.read_text(encoding="utf-8") == expected
    assert len(re.findall(r"^BEGIN;$", expected, re.MULTILINE)) == 1
    assert len(re.findall(r"^COMMIT;$", expected, re.MULTILINE)) == 1
    assert sum(path.is_file() for path in SOURCE.iterdir()) <= 15
    assert all(len(path.read_text(encoding="utf-8").splitlines()) <= 250 for path in SOURCE.iterdir())


def test_schema_is_stage_one_only_and_has_composite_tenant_ownership():
    source = sql("tables")
    assert re.findall(r"CREATE TABLE public\.(\w+)", source) == [
        "departments", "programs", "academic_years"
    ]
    assert source.count("institution_id uuid NOT NULL REFERENCES public.institutions") == 3
    assert "FOREIGN KEY (department_id, institution_id)" in source
    assert "REFERENCES public.departments (department_id, institution_id) ON DELETE RESTRICT" in source
    assert source.count("UNIQUE (") == 3
    assert "(institution_id, lower(btrim(code)))" in source
    assert "(institution_id, department_id, lower(btrim(code)))" in source
    assert "CREATE OR REPLACE" not in "\n".join(sql(name) for name in ("tables", "write", "authorization"))


def test_year_and_numeric_checks_cover_nonfinite_values_and_current_uniqueness():
    source = sql("tables")
    assert "CHECK (end_date > start_date)" in source
    assert "CHECK (NOT is_current OR is_active)" in source
    assert "WHERE (is_current AND is_active)" in source
    assert "EXCLUDE USING gist" in source
    assert "daterange(start_date, end_date, '[]') WITH &&" in source
    assert ") WHERE (is_active)" in source
    assert "CHECK (isfinite(start_date))" in source
    assert "CHECK (isfinite(end_date))" in source
    # Finite positive upper bounds also exclude PostgreSQL numeric NaN/Infinity.
    assert "duration_years > 0 AND duration_years <= 20" in source
    assert "total_credits > 0 AND total_credits <= 1000" in source
    assert source.count("BETWEEN 1 AND 160") == 3
    assert source.count("BETWEEN 1 AND 32") == 3
    assert source.count("code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'") == 3


def test_mutation_authority_requires_same_exact_scoped_active_admin_assignment():
    source = sql("authorization")
    for invariant in (
        "auth.role(), '') <> 'service_role'",
        "u.id = p_actor_user_id AND u.status = 'active'",
        "r.name = 'admin' AND r.is_active",
        "ur.scope_type = 'institution' AND ur.scope_id = p_institution_id",
        "ur.scope_organization_id = i.organization_id",
        "i.is_active AND i.status = 'active' AND o.status = 'active'",
        "permission.is_active AND permission.scope = 'institution'",
        "JOIN public.role_permissions rp ON rp.role_id = r.id",
        "JOIN public.permissions permission ON permission.permission_id = rp.permission_id",
        "permission.code IN (p_resource || '.manage', p_resource || '.*', '*')",
        "FOR SHARE OF u, ur, r, rp, permission, i, o",
        "USING ERRCODE = '42501'",
    ):
        assert invariant in source
    assert "user_permission_grants" not in source
    assert "phase81_assert_institution_admin" not in source


def test_privileges_require_audited_rpc_and_never_browser_or_direct_service_writes():
    source = sql("security")
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role" in source
    assert "GRANT SELECT ON TABLE public.%I TO service_role" in source
    assert "FROM PUBLIC, anon, authenticated, service_role" in source
    assert re.findall(r"GRANT EXECUTE ON FUNCTION public\.(\w+)", source) == [
        "manage_academic_foundation"
    ]
    assert not re.search(r"GRANT (?:ALL|INSERT|UPDATE|DELETE|TRUNCATE)", source)
    assert "OWNER TO postgres" in source
    for name in ("authorization", "validation", "write"):
        assert "SECURITY DEFINER SET search_path = ''" in sql(name)


def test_writes_scope_lookup_and_update_and_keep_actor_and_identity_server_owned():
    source = sql("write")
    assert "PERFORM public.assert_academic_foundation_actor" in source
    assert source.count("AND institution_id = $2 FOR UPDATE") == 1
    assert source.count("AND institution_id = $3 RETURNING") == 1
    assert "'Academic record not found' USING ERRCODE = 'P0002'" in source
    assert "p_record_id IS NULL AND NOT p_payload ?& required" in source
    assert "kind = 'null' AND key NOT IN ('description', 'total_credits')" in source
    assert "p_record_id IS NOT NULL AND key = 'department_id'" in source
    assert "NOT key = ANY(allowed)" in source
    assert "jsonb_build_object(id_column, item_id, 'institution_id', p_institution_id)" in source
    assert "INSERT INTO public.admin_audit_log" in source
    assert "p_actor_user_id, p_institution_id," in source
    assert "jsonb_build_object('before', before_row, 'after', after_row)" in source
    assert "DELETE FROM" not in source


def test_deactivation_and_parent_checks_share_tenant_lock_and_keep_inactive_edits():
    source = sql("validation")
    assert "check_parent boolean := TG_OP = 'INSERT'" in source
    assert "check_parent := NEW.is_active AND NOT OLD.is_active" in source
    assert "d.department_id = NEW.department_id AND d.institution_id = NEW.institution_id" in source
    assert "FOR SHARE OF d" in source
    assert "IF check_parent AND NOT parent_active" in source
    assert "'Department not found in institution' USING ERRCODE = '23503'" in source
    assert "TG_TABLE_NAME = 'departments' AND NOT NEW.is_active" in source
    assert "p.institution_id = NEW.institution_id AND p.is_active" in source
    assert "'Deactivate dependent degree programs first' USING ERRCODE = '23514'" in source
    assert "key LIKE '%\\_id' ESCAPE '\\' OR key = 'created_at'" in source
    for name in ("validation", "write"):
        assert "pg_catalog.pg_advisory_xact_lock" in sql(name)
        assert "'academic-foundations:' ||" in sql(name)


def test_permission_seed_restores_only_foundations_and_only_admin_role():
    source = sql("permissions")
    assert "r.name = 'admin'" in source
    assert "'institution', true" in source
    assert "CROSS JOIN (VALUES ('read'), ('manage'))" in source
    codes = set(re.findall(r"'(\w+\.(?:read|manage))'", source))
    assert codes == {
        f"{entity}.{action}"
        for entity in ("departments", "programs", "academic_years")
        for action in ("read", "manage")
    }
    assert "user_permission_grants" not in source
