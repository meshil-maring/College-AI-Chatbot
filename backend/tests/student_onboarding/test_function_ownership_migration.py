from pathlib import Path
import re


ROOT = Path(__file__).parents[3]
MIGRATION = ROOT / "supabase/migrations/20261104170000_student_onboarding_function_ownership.sql"


def test_student_onboarding_security_definers_are_owned_by_postgres():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert re.search(
        r"ALTER FUNCTION public\.inspect_student_onboarding_invitation\(text\)\s+OWNER TO postgres",
        sql,
    )
    assert re.search(
        r"ALTER FUNCTION public\.complete_student_onboarding_invitation\(\s*uuid,text,uuid\s*\)\s+OWNER TO postgres",
        sql,
    )
    assert "FROM PUBLIC,anon,authenticated,service_role" in sql
    assert "TO service_role" in sql
