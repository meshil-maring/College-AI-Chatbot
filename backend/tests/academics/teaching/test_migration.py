"""Static checks on the teaching assignment migrations; behaviour is covered by
tests/member_management/sql/teaching_contracts.sql against a local database."""

import re
from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[4] / "supabase/migrations"
TABLE = MIGRATIONS / "20261201000000_teaching_assignments.sql"
COMMANDS = MIGRATIONS / "20261201010000_teaching_assignment_commands.sql"


def functions(sql):
    return re.findall(r"CREATE FUNCTION public\.(\w+)\(", sql)


def test_every_function_is_definer_with_an_empty_search_path():
    for path in (TABLE, COMMANDS):
        sql = path.read_text(encoding="utf-8")
        assert sql.count("SECURITY DEFINER SET search_path = ''") == len(functions(sql)) > 0


def test_only_the_commands_and_reads_are_callable_and_only_by_the_service_role():
    table, commands = TABLE.read_text(encoding="utf-8"), COMMANDS.read_text(encoding="utf-8")
    assert "REVOKE ALL ON TABLE public.teaching_assignments FROM PUBLIC, anon, authenticated, service_role" in table
    granted = re.findall(r"GRANT EXECUTE ON FUNCTION (.*?) TO service_role", table + commands, re.S)
    names = set(re.findall(r"public\.(\w+)\(", " ".join(granted)))
    assert names == {
        "read_teaching_assignments", "read_teaching_options",
        "request_teaching_assignment", "decide_teaching_assignment", "end_teaching_assignment",
    }
    assert "GRANT" not in table.split("GRANT EXECUTE", 1)[0]


def test_every_command_rederives_the_actor_and_writes_an_audit_row():
    commands = COMMANDS.read_text(encoding="utf-8")
    bodies = re.split(r"CREATE FUNCTION ", commands)[1:]
    assert len(bodies) == 3
    for body in bodies:
        assert "public.teaching_actor(p_actor, p_tenant)" in body
        assert "INSERT INTO public.admin_audit_log" in body
        assert "'faculty_user_id'" in body


def test_history_is_kept_rather_than_deleted():
    sql = TABLE.read_text(encoding="utf-8") + COMMANDS.read_text(encoding="utf-8")
    assert "DELETE FROM public.teaching_assignments" not in sql
    assert "ON DELETE RESTRICT" in sql
