"""Offline release contracts for the unapplied Stage 2 migration, without PostgreSQL."""
from pathlib import Path
import re
import runpy


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "supabase/migration_sources/academic_structure"
BUILDER = ROOT / "scripts/maintenance/migrations/build_academic_structure.py"


def sql(name):
    return (SOURCE / f"{name}.sql").read_text(encoding="utf-8")


def test_generated_forward_migration_matches_bounded_ordered_sources():
    target, expected = runpy.run_path(str(BUILDER))["render"]()
    assert target.name == "20261024000000_academic_structure.sql"
    assert target.read_text(encoding="utf-8") == expected
    assert len(re.findall(r"^BEGIN;$", expected, re.MULTILINE)) == 1
    assert len(re.findall(r"^COMMIT;$", expected, re.MULTILINE)) == 1
    assert sum(path.is_file() for path in SOURCE.iterdir()) <= 15
    assert all(len(path.read_text(encoding="utf-8").splitlines()) <= 250 for path in SOURCE.iterdir())


def test_schema_has_only_study_progress_and_reusable_subject_tables():
    source = sql("tables")
    assert re.findall(r"CREATE TABLE public\.(\w+)", source) == ["study_semesters", "subjects"]
    semester, subject = source.split("CREATE TABLE public.subjects")
    assert "study_semester_number integer NOT NULL" in semester
    assert "study_semester_number BETWEEN 1 AND 30" in semester
    assert not re.search(r"\b(?:start_date|end_date|is_current)\b", semester)
    assert not re.search(r"\b(?:program_id|academic_year_id|study_semester_id|section_id)\b", subject)
    assert "not a dated calendar term" in source
    assert "distinct from degree programs" in source


def test_parent_foreign_keys_cannot_cross_institutions_or_delete_referenced_records():
    source = sql("tables")
    for entity, key in (
        ("programs", "program_id"),
        ("academic_years", "academic_year_id"),
        ("departments", "department_id"),
    ):
        assert f"FOREIGN KEY ({key}, institution_id)" in source
        assert f"REFERENCES public.{entity} ({key}, institution_id) ON DELETE RESTRICT" in source
    assert source.count("institution_id uuid NOT NULL REFERENCES public.institutions") == 2
    assert "UNIQUE (study_semester_id, institution_id)" in source
    assert "UNIQUE (subject_id, institution_id)" in source


def test_duplicate_codes_and_study_numbers_remain_reserved_when_inactive():
    source = sql("tables")
    assert "UNIQUE (institution_id, program_id, academic_year_id, study_semester_number)" in source
    assert "(institution_id, program_id, academic_year_id, lower(btrim(code)))" in source
    assert "(institution_id, department_id, lower(btrim(code)))" in source
    assert "WHERE" not in source


def test_subject_credit_and_text_constraints_cover_invalid_and_nonfinite_values():
    source = sql("tables")
    assert "credits numeric NOT NULL CHECK (credits > 0 AND credits <= 100" in source
    assert "credits::text NOT IN ('NaN', 'Infinity', '-Infinity')" in source
    assert source.count("BETWEEN 1 AND 160") == 2
    assert source.count("BETWEEN 1 AND 32") == 2
    assert source.count("length(description) <= 2000") == 2
    assert source.count("code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'") == 2


def test_new_trigger_requires_active_tenant_and_every_parent_on_create_or_reactivate():
    source = sql("validation")
    assert "check_parent boolean := TG_OP = 'INSERT'" in source
    assert "check_parent := NEW.is_active AND NOT OLD.is_active" in source
    assert "IF check_parent THEN" in source
    assert "i.is_active AND i.status = 'active' AND o.status = 'active'" in source
    assert "FOR SHARE OF i, o" in source
    assert "p.is_active AND d.is_active AND y.is_active" in source
    assert "d.department_id = p.department_id AND d.institution_id = p.institution_id" in source
    assert "y.institution_id = NEW.institution_id" in source
    assert "p.program_id = NEW.program_id AND p.institution_id = NEW.institution_id" in source
    assert "FOR SHARE OF p, d, y" in source
    assert "d.department_id = NEW.department_id AND d.institution_id = NEW.institution_id" in source
    assert "FOR SHARE OF d" in source
    assert "IF check_parent AND NOT parent_active" in source
    assert source.count("USING ERRCODE = '23503'") == 2


def test_new_trigger_keeps_ancestry_and_study_number_immutable_and_normalizes_metadata():
    source = sql("validation")
    assert "key LIKE '%\\_id' ESCAPE '\\' OR key IN ('created_at', 'study_semester_number')" in source
    assert "item -> key IS DISTINCT FROM previous -> key" in source
    assert "NEW.name := btrim(NEW.name)" in source
    assert "NEW.code := btrim(NEW.code)" in source
    assert "IF TG_OP = 'INSERT' THEN NEW.created_at := now()" in source
    assert "NEW.updated_at := now()" in source


def test_new_parent_guards_extend_stage_one_without_replacing_its_functions():
    source = sql("parent_guards")
    assert "TG_TABLE_NAME = 'departments'" in source
    assert "s.department_id = NEW.department_id" in source
    assert "TG_TABLE_NAME = 'programs'" in source
    assert "s.program_id = NEW.program_id" in source
    assert "TG_TABLE_NAME = 'academic_years'" in source
    assert "s.academic_year_id = NEW.academic_year_id" in source
    assert source.count("s.institution_id = NEW.institution_id AND s.is_active") == 3
    assert "CREATE TRIGGER academic_structure_parent_guard BEFORE UPDATE" in source
    all_sources = "\n".join(path.read_text() for path in SOURCE.glob("*.sql"))
    assert "CREATE OR REPLACE" not in all_sources
    assert "CREATE FUNCTION public.validate_academic_foundation" not in all_sources
    assert "CREATE FUNCTION public.assert_academic_foundation_actor" not in all_sources


def test_both_stages_share_one_advisory_tenant_lock_for_mutations_and_parent_guards():
    for name in ("validation", "parent_guards", "write"):
        assert "pg_catalog.pg_advisory_xact_lock" in sql(name)
        assert "pg_catalog.hashtextextended('academic-foundations:' ||" in sql(name)
    stage_one = ROOT / "supabase/migration_sources/academic_foundations"
    for name in ("validation", "write"):
        assert "'academic-foundations:' ||" in (stage_one / f"{name}.sql").read_text()
