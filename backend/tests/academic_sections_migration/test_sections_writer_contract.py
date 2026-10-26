"""Offline Stage 3 RPC, permission and privilege contracts; no live database claims."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "supabase/migration_sources/academic_sections"


def sql(name):
    return (SOURCE / f"{name}.sql").read_text(encoding="utf-8")


def test_permission_seed_adds_only_four_exact_institution_permissions_to_admin():
    source = sql("permissions")
    assert "r.name = 'admin'" in source
    assert "'institution', true" in source
    assert "CROSS JOIN (VALUES ('read'), ('manage'))" in source
    codes = set(re.findall(r"'(\w+\.(?:read|manage))'", source))
    assert codes == {
        f"{entity}.{action}" for entity in ("sections", "section_subjects") for action in ("read", "manage")
    }
    assert "user_permission_grants" not in source
    assert "'*'" not in source


def test_actor_authorization_precedes_tenant_scoped_record_lookup_and_write():
    source = sql("write")
    authority = "PERFORM public.assert_academic_foundation_actor(p_actor_user_id, p_institution_id, p_entity)"
    assert authority in source
    assert source.index(authority) < source.index("IF p_record_id IS NOT NULL THEN")
    existing = (SOURCE.parent / "academic_foundations/authorization.sql").read_text(encoding="utf-8")
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


def test_rpc_has_only_sections_and_subject_assignment_entity_mappings():
    source = sql("write")
    assert "CREATE FUNCTION public.manage_academic_sections(" in source
    assert "WHEN 'sections' THEN\n        relation_name := 'class_sections'" in source
    assert "WHEN 'section_subjects' THEN\n        relation_name := 'section_subject_assignments'" in source
    assert re.findall(r"WHEN '(\w+)' THEN", source) == ["sections", "section_subjects"]
    assert "ELSE RAISE EXCEPTION 'Unknown academic sections entity'" in source


def test_payload_whitelists_keep_parent_identity_immutable_and_assignment_create_active():
    source = sql("write")
    assert "NOT key = ANY(allowed)" in source
    assert "p_record_id IS NOT NULL AND key = ANY(immutable)" in source
    assert "immutable := ARRAY['study_semester_id']" in source
    assert "immutable := ARRAY['section_id', 'subject_id']" in source
    assert "required := ARRAY['name', 'code', 'study_semester_id']" in source
    assert "allowed := CASE WHEN p_record_id IS NULL THEN immutable ELSE ARRAY['is_active'] END" in source
    for declaration in re.findall(r"allowed := ([^;]+);", source):
        assert not re.search(r"actor|institution|created_at|updated_at|assignment_id", declaration)
    assert "jsonb_build_object(id_column, item_id, 'institution_id', p_institution_id)" in source


def test_payload_rejects_empty_missing_null_fields_and_nonboolean_activation():
    source = sql("write")
    assert "p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' OR p_payload = '{}'::jsonb" in source
    assert "p_record_id IS NULL AND NOT p_payload ?& required" in source
    assert "kind = 'null' AND key <> 'description'" in source
    assert "key = 'is_active' AND kind <> 'boolean'" in source
    assert "key <> 'is_active' AND kind <> 'string'" in source


def test_record_lookup_and_update_are_tenant_filtered_and_payload_values_are_bound():
    source = sql("write")
    assert "AND institution_id = $2 FOR UPDATE" in source
    assert "AND institution_id = $3 RETURNING" in source
    assert "'Academic record not found' USING ERRCODE = 'P0002'" in source
    assert "INTO before_row USING p_record_id, p_institution_id" in source
    assert "INTO after_row USING effective" in source
    assert "INTO after_row USING effective, p_record_id, p_institution_id" in source


def test_atomic_audit_uses_actual_activation_transitions_and_before_after_records():
    source = sql("write")
    assert "INSERT INTO public.admin_audit_log" in source
    assert "jsonb_build_object('before', before_row, 'after', after_row)" in source
    assert "before_row ->> 'is_active' = 'true' AND after_row ->> 'is_active' = 'false'" in source
    assert "before_row ->> 'is_active' = 'false' AND after_row ->> 'is_active' = 'true'" in source
    assert "relation_name, item_id::text" in source
    assert "EXCEPTION WHEN" not in source


def test_rls_and_acl_deny_browser_and_direct_service_writes_or_hard_deletes():
    source = sql("security")
    assert "ARRAY['class_sections', 'section_subject_assignments']" in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role" in source
    assert "GRANT SELECT ON TABLE public.%I TO service_role" in source
    assert "CREATE TRIGGER academic_sections_validate BEFORE INSERT OR UPDATE" in source
    assert "FROM PUBLIC, anon, authenticated, service_role" in source
    assert re.findall(r"GRANT EXECUTE ON FUNCTION public\.(\w+)", source) == ["manage_academic_sections"]
    assert not re.search(r"GRANT (?:ALL|INSERT|UPDATE|DELETE|TRUNCATE)", source)
    for name in ("validation", "parent_guards", "write"):
        assert "SECURITY DEFINER SET search_path = ''" in sql(name)
