"""Offline Stage 3 schema contracts; these tests never connect to PostgreSQL."""
from pathlib import Path
import re
import runpy


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "supabase/migration_sources/academic_sections"
BUILDER = ROOT / "scripts/maintenance/migrations/build_academic_sections.py"


def sql(name):
    return (SOURCE / f"{name}.sql").read_text(encoding="utf-8")


def test_stage_three_forward_migration_matches_bounded_sources_in_one_transaction():
    target, expected = runpy.run_path(str(BUILDER))["render"]()
    assert target.name == "20261024010000_academic_sections.sql"
    assert target.read_text(encoding="utf-8") == expected
    assert len(re.findall(r"^BEGIN;$", expected, re.MULTILINE)) == 1
    assert len(re.findall(r"^COMMIT;$", expected, re.MULTILINE)) == 1
    assert sum(path.is_file() for path in SOURCE.iterdir()) <= 15
    assert all(len(path.read_text(encoding="utf-8").splitlines()) <= 250 for path in SOURCE.iterdir())


def test_sections_have_one_immutable_study_semester_parent_and_no_subject_parent():
    source = sql("tables")
    assert re.findall(r"CREATE TABLE public\.(\w+)", source) == [
        "class_sections", "section_subject_assignments",
    ]
    section, assignment = source.split("CREATE TABLE public.section_subject_assignments")
    assert "study_semester_id uuid NOT NULL" in section
    assert not re.search(r"\b(?:subject_id|program_id|academic_year_id)\b", section)
    assert "subject_id uuid NOT NULL" in assignment
    assert "program and academic year derive from their immutable study semester" in source


def test_every_foreign_key_carries_institution_and_restricts_deletion():
    source = sql("tables")
    for entity, key in (
        ("study_semesters", "study_semester_id"),
        ("class_sections", "section_id"),
        ("subjects", "subject_id"),
    ):
        assert f"FOREIGN KEY ({key}, institution_id)" in source
        assert f"REFERENCES public.{entity} ({key}, institution_id) ON DELETE RESTRICT" in source
    assert source.count("institution_id uuid NOT NULL REFERENCES public.institutions") == 2
    assert "UNIQUE (section_id, institution_id)" in source


def test_section_name_code_and_assignment_pair_reserve_uniqueness_when_inactive():
    source = sql("tables")
    assert "(institution_id, study_semester_id, lower(btrim(code)))" in source
    assert "(institution_id, study_semester_id, lower(btrim(name)))" in source
    assert "UNIQUE (institution_id, section_id, subject_id)" in source
    assert "WHERE" not in source
    assert source.count("is_active boolean NOT NULL DEFAULT true") == 2


def test_section_metadata_matches_existing_setup_validation_limits():
    source = sql("tables")
    assert "length(btrim(name)) BETWEEN 1 AND 160" in source
    assert "length(btrim(code)) BETWEEN 1 AND 32" in source
    assert "code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'" in source
    assert "length(description) <= 2000" in source


def test_stage_three_never_replaces_or_drops_existing_release_objects():
    source = "\n".join(path.read_text(encoding="utf-8") for path in SOURCE.glob("*.sql"))
    assert "CREATE OR REPLACE" not in source
    assert not re.search(r"\bDROP\b", source)
    assert "CREATE FUNCTION public.assert_academic_foundation_actor" not in source
    assert "CREATE FUNCTION public.validate_academic_structure" not in source
    assert "CREATE FUNCTION public.manage_academic_structure" not in source
    assert not re.search(r"\b(?:enrollments|attendance|examinations|student_rejection)\b", source)
