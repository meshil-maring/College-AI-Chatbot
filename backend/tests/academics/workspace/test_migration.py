import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "supabase/migration_sources/academic_workspace"


def test_generated_migration_is_current_and_sources_respect_limits():
    generator = ROOT / "scripts/maintenance/migrations/build_academic_workspace.py"
    spec = importlib.util.spec_from_file_location("academic_workspace_generator", generator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target, expected = module.render()
    assert target.read_text(encoding="utf-8") == expected
    assert len(list(SOURCE.iterdir())) <= 15
    for name in json.loads((SOURCE / "manifest.json").read_text())["files"]:
        assert len((SOURCE / name).read_text().splitlines()) <= 250


def test_forward_extension_keeps_existing_tables_and_writer():
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    sql = "\n".join((SOURCE / name).read_text() for name in manifest["files"])
    assert "DROP TABLE" not in sql
    assert "ALTER TABLE public.programs ADD" not in sql
    assert "CREATE OR REPLACE FUNCTION" not in sql
    assert "academic-setup:" in sql
    assert "assert_academic_foundation_actor" in sql
    assert "INSERT INTO public.admin_audit_log" in sql
    assert "GRANT SELECT" in sql
    assert "GRANT EXECUTE" in sql
    assert "FOREIGN KEY (curriculum_version_id, institution_id)" in sql


def test_database_probe_covers_complete_dependency_chain():
    probe = (Path(__file__).parent / "contracts.sql").read_text()
    for entity in ["program_semesters", "curriculum_versions", "curriculum_subjects", "admission_cohorts", "academic_sections", "academic_offerings"]:
        assert f"'{entity}'" in probe
    assert "has_table_privilege" in probe
    assert "has_function_privilege" in probe
    assert "EXCEPTION WHEN check_violation" in probe
