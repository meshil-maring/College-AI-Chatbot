"""Stage 2 source safeguards, not claims of executed RPC or RLS behavior."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "supabase/migration_sources/academic_structure"


def sql(name):
    return (SOURCE / f"{name}.sql").read_text(encoding="utf-8")


def test_permission_seed_adds_only_four_exact_institution_permissions_to_admin():
    source = sql("permissions")
    assert "r.name = 'admin'" in source
    assert "'institution', true" in source
    assert "CROSS JOIN (VALUES ('read'), ('manage'))" in source
    codes = set(re.findall(r"'(\w+\.(?:read|manage))'", source))
    assert codes == {f"{entity}.{action}" for entity in ("semesters", "subjects") for action in ("read", "manage")}
    assert "user_permission_grants" not in source
    assert "'*'" not in source


def test_writer_reuses_same_scoped_active_admin_actor_guard_before_any_lookup_or_write():
    source = sql("write")
    authority = "PERFORM public.assert_academic_foundation_actor(p_actor_user_id, p_institution_id, p_entity)"
    assert authority in source
    assert source.index(authority) < source.index("IF p_record_id IS NOT NULL THEN")
    existing = (ROOT / "supabase/migration_sources/academic_foundations/authorization.sql").read_text()
    for invariant in (
        "auth.role(), '') <> 'service_role'",
        "u.id = p_actor_user_id AND u.status = 'active'",
        "r.name = 'admin' AND r.is_active",
        "ur.scope_type = 'institution' AND ur.scope_id = p_institution_id",
        "ur.scope_organization_id = i.organization_id",
        "permission.is_active AND permission.scope = 'institution'",
        "i.is_active AND i.status = 'active' AND o.status = 'active'",
    ):
        assert invariant in existing


def test_rpc_maps_only_approved_api_entities_to_physical_tables():
    source = sql("write")
    assert "WHEN 'semesters' THEN\n        relation_name := 'study_semesters'" in source
    assert "WHEN 'subjects' THEN\n        relation_name := 'subjects'" in source
    assert re.findall(r"WHEN '(\w+)' THEN", source) == ["semesters", "subjects"]
    assert "ELSE RAISE EXCEPTION 'Unknown academic structure entity'" in source
    assert "SECURITY DEFINER SET search_path = ''" in source


def test_payload_rejects_injected_actor_tenant_identity_and_immutable_parent_fields():
    source = sql("write")
    assert "NOT key = ANY(allowed)" in source
    assert "p_record_id IS NOT NULL AND key = ANY(immutable)" in source
    assert "immutable := ARRAY['program_id', 'academic_year_id', 'study_semester_number']" in source
    assert "immutable := ARRAY['department_id']" in source
    allowed_declarations = re.findall(r"allowed := ([^;]+);", source)
    assert len(allowed_declarations) == 2
    for declaration in allowed_declarations:
        assert not re.search(r"actor|institution|created_at|updated_at|subject_id|study_semester_id", declaration)
    assert "jsonb_build_object(id_column, item_id, 'institution_id', p_institution_id)" in source


def test_payload_requires_fields_and_strict_json_boolean_numeric_integer_types():
    source = sql("write")
    assert "p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' OR p_payload = '{}'::jsonb" in source
    assert "p_record_id IS NULL AND NOT p_payload ?& required" in source
    assert "required := required || immutable" in source
    assert "required := required || ARRAY['department_id', 'credits']" in source
    assert "kind = 'null' AND key <> 'description'" in source
    assert "key = 'is_active' AND kind <> 'boolean'" in source
    assert "key IN ('credits', 'study_semester_number') AND kind <> 'number'" in source
    assert "key = 'study_semester_number' AND NOT (p_payload ->> key) ~ '^[0-9]+$'" in source


def test_update_scope_lookup_and_atomic_audit_preserve_true_activation_transitions():
    source = sql("write")
    assert "AND institution_id = $2 FOR UPDATE" in source
    assert "AND institution_id = $3 RETURNING" in source
    assert "'Academic record not found' USING ERRCODE = 'P0002'" in source
    assert "INSERT INTO public.admin_audit_log" in source
    assert "jsonb_build_object('before', before_row, 'after', after_row)" in source
    assert "before_row ->> 'is_active' = 'true' AND after_row ->> 'is_active' = 'false'" in source
    assert "before_row ->> 'is_active' = 'false' AND after_row ->> 'is_active' = 'true'" in source
    assert "relation_name, item_id::text" in source
    assert "DELETE FROM" not in source


def test_security_denies_browser_access_and_direct_service_mutations():
    source = sql("security")
    assert "ARRAY['study_semesters', 'subjects']" in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role" in source
    assert "GRANT SELECT ON TABLE public.%I TO service_role" in source
    assert "CREATE TRIGGER academic_structure_validate BEFORE INSERT OR UPDATE" in source
    assert "FROM PUBLIC, anon, authenticated, service_role" in source
    assert re.findall(r"GRANT EXECUTE ON FUNCTION public\.(\w+)", source) == ["manage_academic_structure"]
    assert not re.search(r"GRANT (?:ALL|INSERT|UPDATE|DELETE|TRUNCATE)", source)
    for name in ("validation", "parent_guards", "write"):
        assert "SECURITY DEFINER SET search_path = ''" in sql(name)
