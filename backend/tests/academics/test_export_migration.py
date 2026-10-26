"""Keep the adopted table schema aligned with the supplied immutable snapshot."""

import importlib.util
from pathlib import Path
import re

from app.schemas.academics.academic_setup import AcademicEntity

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "supabase/migration_sources/academic_export"


def test_every_setup_table_definition_matches_the_supplied_export():
    pattern = r'CREATE TABLE (?:IF NOT EXISTS )?"public"\."([^"]+)" \((.*?)\n\);'
    exported = dict(re.findall(pattern, (ROOT / "academic_state_check_latest.sql").read_text(encoding="utf-8-sig"), re.S))
    maintained = dict(re.findall(pattern, (SOURCE / "tables.sql").read_text(encoding="utf-8"), re.S))
    assert set(maintained) == set(AcademicEntity)
    for name, definition in maintained.items():
        assert definition == exported[name]
    assert "institution_id" not in maintained["programs"]
    assert "semester_number" not in maintained["program_courses"]


def test_keys_relationships_and_indexes_match_the_supplied_export():
    exported = (ROOT / "academic_state_check_latest.sql").read_text(encoding="utf-8-sig")
    patterns = {
        "constraints.sql": r'ALTER TABLE ONLY "public"\."([^"]+)"\s+ADD CONSTRAINT[\s\S]*?;',
        "indexes.sql": r'CREATE (?:UNIQUE )?INDEX "[^"]+" ON "public"\."([^"]+)"[^;]+;',
    }
    for filename, pattern in patterns.items():
        expected = {
            match.group(0) for match in re.finditer(pattern, exported)
            if match.group(1) in set(AcademicEntity)
        }
        maintained = {
            match.group(0) for match in re.finditer(
                pattern, (SOURCE / filename).read_text(encoding="utf-8")
            )
        }
        assert maintained == expected


def test_generator_has_exact_parity_with_the_checked_in_forward_migration():
    path = ROOT / "scripts/maintenance/migrations/build_academic_export.py"
    spec = importlib.util.spec_from_file_location("build_academic_export", path)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    target, rendered = generator.render()
    assert target.read_text(encoding="utf-8") == rendered


def test_transition_preserves_previous_tables_and_disables_old_writers():
    transition = (SOURCE / "transition.sql").read_text(encoding="utf-8")
    assert "SET SCHEMA academic_setup_previous" in transition
    assert "DROP TABLE" not in transition
    assert "CASCADE" not in transition
    assert "manage_academic_sections" in transition
    assert "FROM PUBLIC, anon, authenticated, service_role" in transition


def test_table_and_routine_access_stays_backend_only():
    security = (SOURCE / "security.sql").read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in security
    assert "GRANT SELECT ON TABLE" in security
    assert "GRANT INSERT" not in security
    assert "GRANT EXECUTE ON FUNCTION public.manage_academic_master_record" in security
    writer = (SOURCE / "write.sql").read_text(encoding="utf-8")
    assert "assert_academic_foundation_actor" in writer
    assert "INSERT INTO public.admin_audit_log" in writer
