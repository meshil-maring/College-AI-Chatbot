import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "supabase/migration_sources/student_transfers"


def generator():
    path = ROOT / "scripts/maintenance/student_transfers/build_migration.py"
    spec = importlib.util.spec_from_file_location("student_transfer_migration_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rendered():
    return generator().render()[0]


def test_generated_migrations_match_sources_and_own_their_versions():
    migrations = generator().render()
    assert [target.name for target, _ in migrations] == [
        "20261121000000_student_transfer_workflow.sql",
        "20261122000000_student_transfer_direct.sql",
    ]
    for target, sql in migrations:
        assert target.read_text(encoding="utf-8") == sql
        assert list(target.parent.glob(f"{target.name.split('_', 1)[0]}_*.sql")) == [target]


def test_sources_stay_within_maintenance_limits():
    for folder in (SOURCE, SOURCE / "direct"):
        files = [path for path in folder.iterdir() if path.is_file()]
        assert len(files) <= 15
        for path in files:
            assert len(path.read_text(encoding="utf-8").splitlines()) <= 250, path.name


def test_direct_transfer_commands_are_backend_only_and_scoped():
    _, sql = generator().render()[1]
    security = (SOURCE / "direct/security.sql").read_text(encoding="utf-8")
    revoke, grant = security.split("GRANT EXECUTE", 1)
    assert set(re.findall(r"CREATE FUNCTION public\.(\w+)", sql)) <= set(re.findall(r"public\.(\w+)\(", revoke))
    assert set(re.findall(r"public\.(\w+)\(", grant)) == {
        "read_direct_transfer_students", "read_direct_transfer_options", "direct_transfer_student",
    }
    direct = sql.split("CREATE FUNCTION public.direct_transfer_student(", 1)[1].split("$$;", 1)[0]
    for guard in ("assert_transfer_backend()", "transfer_direct_role(", "transfer_apply(",
                  "'P1111'", "Head of Department can transfer only within their department"):
        assert guard in direct
    assert direct.index("'P1111'") < direct.index("INSERT INTO public.student_transfer_requests")


def test_every_function_is_revoked_and_only_commands_reach_service_role():
    _, sql = rendered()
    created = set(re.findall(r"CREATE FUNCTION public\.(\w+)", sql))
    security = (SOURCE / "security.sql").read_text(encoding="utf-8")
    revoke, grant = security.split("GRANT EXECUTE", 1)
    assert created <= set(re.findall(r"public\.(\w+)\(", revoke))
    assert set(re.findall(r"public\.(\w+)\(", grant)) == {
        "read_student_transfers", "submit_student_transfer", "cancel_student_transfer",
        "read_transfer_reviews", "decide_student_transfer",
        "read_department_heads", "assign_department_head",
    }
    assert "authenticated" not in grant and "anon" not in grant


def test_every_command_requires_the_trusted_backend():
    _, sql = rendered()
    commands = ("read_transfer_reviews", "decide_student_transfer",
                "read_department_heads", "assign_department_head")
    for name in commands:
        body = sql.split(f"CREATE FUNCTION public.{name}(", 1)[1].split("$$;", 1)[0]
        assert "assert_transfer_backend()" in body, name
    for name in ("read_student_transfers", "submit_student_transfer", "cancel_student_transfer"):
        body = sql.split(f"CREATE FUNCTION public.{name}(", 1)[1].split("$$;", 1)[0]
        assert "assert_transfer_student(" in body, name


def test_draft_tables_are_dropped_only_when_empty():
    replace = (SOURCE / "replace_draft.sql").read_text(encoding="utf-8")
    assert "SELECT EXISTS (SELECT 1 FROM public.%I)" in replace
    assert replace.index("RAISE EXCEPTION") < replace.index("DROP TABLE")


def test_assignment_guard_only_changes_the_batch_check():
    original = (ROOT / "supabase/migrations/20261030000000_semester_registration.sql").read_text(encoding="utf-8")
    start = original.index("CREATE FUNCTION public.assign_student_semester(")
    before = original[start:original.index("$$;", start)].replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION")
    guard = (SOURCE / "assignment_guard.sql").read_text(encoding="utf-8")
    after = guard[guard.index("CREATE OR REPLACE FUNCTION"):guard.index("$$;")]
    removed = "WHERE reg.student_id=p_student AND sec.admission_cohort_id"
    added = "WHERE reg.semester_registration_id=public.transfer_current_registration(p_student,p_tenant)"
    assert removed in before and added in after
    normalized_before = before.replace(
        removed, added + "\n          AND sec.admission_cohort_id")
    assert normalized_before == after
