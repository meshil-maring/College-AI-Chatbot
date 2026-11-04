from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

from app.config import settings
from app.repositories.invitations import student_onboarding as repository


ROOT = Path(__file__).parents[3]
MIGRATION = ROOT / "supabase/migrations/20261104000000_student_onboarding_development_resend_override.sql"


def test_resend_rpc_receives_server_owned_development_mode(monkeypatch):
    client = Mock()
    client.rpc.return_value.execute.return_value.data = {"invitation_id": "row"}

    repository.resend(
        client,
        actor="actor",
        tenant=UUID("10000000-0000-0000-0000-000000000001"),
        invitation=UUID("20000000-0000-0000-0000-000000000001"),
        token_hash="a" * 64,
        expires_at="2099-01-01T00:00:00Z",
        development_mode=settings.is_local_environment,
    )

    assert client.rpc.call_args.args[0] == "resend_student_onboarding_invitation"
    assert client.rpc.call_args.args[1]["p_development_mode"] is True


def test_migration_limits_production_and_resets_only_development_counter():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "IF NOT COALESCE(p_development_mode, false)" in sql
    assert "resend_window_count >= 3" in sql
    assert "WHEN COALESCE(p_development_mode, false) THEN 0" in sql
    assert "GRANT EXECUTE" in sql and "TO service_role" in sql
