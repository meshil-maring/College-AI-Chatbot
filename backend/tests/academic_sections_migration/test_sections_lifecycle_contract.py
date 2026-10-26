"""Source checks for tenant ancestry and safe assignment lifecycle, without SQL execution."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "supabase/migration_sources/academic_sections"


def sql(name):
    return (SOURCE / f"{name}.sql").read_text(encoding="utf-8")


def test_create_and_reactivate_require_active_tenant_and_organization():
    source = sql("validation")
    assert "check_parent boolean := TG_OP = 'INSERT'" in source
    assert "check_parent := NEW.is_active AND NOT OLD.is_active" in source
    assert "IF check_parent THEN" in source
    assert "i.is_active AND i.status = 'active' AND o.status = 'active'" in source
    assert "FOR SHARE OF i, o" in source
    assert "IF check_parent AND NOT parent_active" in source


def test_section_create_and_reactivate_require_full_same_tenant_active_hierarchy():
    source = sql("validation")
    assert "s.is_active AND p.is_active AND d.is_active AND y.is_active" in source
    assert "s.study_semester_id = NEW.study_semester_id AND s.institution_id = NEW.institution_id" in source
    assert "p.program_id = s.program_id AND p.institution_id = s.institution_id" in source
    assert "d.department_id = p.department_id" in source
    assert "d.institution_id = p.institution_id" in source
    assert "y.academic_year_id = s.academic_year_id" in source
    assert "y.institution_id = s.institution_id" in source
    assert "FOR SHARE OF s, p, d, y" in source
    assert "'Study semester not found in institution' USING ERRCODE = '23503'" in source


def test_assignment_create_and_reactivate_require_active_section_and_subject_owners():
    source = sql("validation")
    assert "c.is_active AND s.is_active AND p.is_active AND d.is_active AND y.is_active" in source
    assert "c.section_id = NEW.section_id AND c.institution_id = NEW.institution_id" in source
    assert "s.institution_id = c.institution_id" in source
    assert "FOR SHARE OF c, s, p, d, y" in source
    assert "subject.is_active AND d.is_active INTO subject_active" in source
    assert "d.department_id = subject.department_id" in source
    assert "d.institution_id = subject.institution_id" in source
    assert "subject.subject_id = NEW.subject_id AND subject.institution_id = NEW.institution_id" in source
    assert "FOR SHARE OF subject, d" in source
    assert "parent_active := parent_active AND subject_active" in source
    assert "'Section not found in institution' USING ERRCODE = '23503'" in source
    assert "'Subject not found in institution' USING ERRCODE = '23503'" in source


def test_subjects_from_other_departments_are_reusable_within_the_same_institution():
    source = sql("validation")
    assert "A subject from another department is reusable within this institution" in source
    assert "subject.department_id = p.department_id" not in source
    assert "subject.institution_id = NEW.institution_id" in source


def test_all_identity_and_parent_ids_remain_immutable_and_section_metadata_is_trimmed():
    source = sql("validation")
    assert "key LIKE '%\\_id' ESCAPE '\\' OR key = 'created_at'" in source
    assert "item -> key IS DISTINCT FROM previous -> key" in source
    assert "NEW.name := btrim(NEW.name)" in source
    assert "NEW.code := btrim(NEW.code)" in source
    assert "IF TG_OP = 'INSERT' THEN NEW.created_at := now()" in source
    assert "NEW.updated_at := now()" in source


def test_section_and_subject_deactivation_require_removing_active_assignments_first():
    source = sql("validation")
    assert "IF NOT NEW.is_active AND EXISTS" in source
    assert "a.section_id = NEW.section_id AND a.institution_id = NEW.institution_id AND a.is_active" in source
    assert "'Remove active subject assignments first' USING ERRCODE = '23514'" in source
    guard = sql("parent_guards")
    assert "TG_TABLE_NAME = 'subjects'" in guard
    assert "a.subject_id = NEW.subject_id" in guard
    assert "a.institution_id = NEW.institution_id AND a.is_active" in guard
    assert "'Remove active subject assignments first' USING ERRCODE = '23514'" in guard


def test_study_semester_deactivation_requires_deactivating_its_active_sections():
    source = sql("parent_guards")
    assert "IF NEW.is_active THEN RETURN NEW" in source
    assert "TG_TABLE_NAME = 'study_semesters'" in source
    assert "c.study_semester_id = NEW.study_semester_id" in source
    assert "c.institution_id = NEW.institution_id AND c.is_active" in source
    assert "'Deactivate dependent sections first' USING ERRCODE = '23514'" in source
    assert "ARRAY['study_semesters', 'subjects']" in source
    assert "CREATE TRIGGER academic_sections_parent_guard BEFORE UPDATE" in source


def test_every_stage_three_write_path_shares_earlier_stages_tenant_advisory_lock():
    for name in ("validation", "parent_guards", "write"):
        source = sql(name)
        assert "pg_catalog.pg_advisory_xact_lock" in source
        assert "pg_catalog.hashtextextended('academic-foundations:' ||" in source
    for feature in ("academic_foundations", "academic_structure"):
        for name in ("validation", "write"):
            source = (SOURCE.parent / feature / f"{name}.sql").read_text(encoding="utf-8")
            assert "'academic-foundations:' ||" in source


def test_assignment_removal_reuses_the_link_and_preserves_catalogue_subjects():
    source = sql("write")
    assert "allowed := CASE WHEN p_record_id IS NULL THEN immutable ELSE ARRAY['is_active'] END" in source
    assert "before_row -> 'is_active' = p_payload -> 'is_active'" in source
    assert "RETURN before_row" in source
    assert source.index("RETURN before_row") < source.index("INSERT INTO public.admin_audit_log")
    assert "DELETE FROM" not in source
    assert "UPDATE public.subjects" not in source
