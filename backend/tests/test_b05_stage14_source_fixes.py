"""Offline orchestration and source contracts; never PostgreSQL execution.

Atomicity below is simulated by an RPC fake. SQL engine rollback, trigger
execution, uniqueness and locking remain separate runtime validation items.
"""

from pathlib import Path
from unittest.mock import MagicMock


from app.repositories.invitations import platform_admin_invitations as repo

ROOT = Path(__file__).parents[2]
SQL = ROOT / "supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql"
TOKEN = "a" * 64
INV = "20000000-0000-0000-0000-000000000001"
USER = "30000000-0000-0000-0000-000000000001"
AUTH = "50000000-0000-0000-0000-000000000001"
INST = "40000000-0000-0000-0000-000000000001"
OP = "60000000-0000-0000-0000-000000000001"
ACTOR = {"user_id": USER, "auth_user_id": AUTH}


def test_sql_recovery_and_audit_bindings_are_source_checks_only():
    source = SQL.read_text(encoding="utf-8")
    recover = source.split("CREATE FUNCTION public.b05_recover_accepted_invitation", 1)[
        1
    ].split("$$;", 1)[0]
    for predicate in [
        "v_inv.token_hash IS DISTINCT FROM p_digest",
        "v_inv.acceptance_id IS NULL",
        "v_op.kind IS DISTINCT FROM p_kind",
        "v_op.invitation_id IS DISTINCT FROM p_id",
        "v_op.user_id IS DISTINCT FROM v_inv.accepted_user_id",
        "auth_user_id = v_op.auth_user_id",
        "NOT v_op.new_account",
        "v_op.stage NOT IN ('accepted','confirmed')",
    ]:
        assert predicate in recover
    assert recover.count("FOR UPDATE") == 3
    assert "INSERT INTO" not in recover and "UPDATE public." not in recover
    audit = source.split("CREATE FUNCTION public.b05_record_invitation_lifecycle", 1)[
        1
    ].split("$$;", 1)[0]
    assert audit.index(
        "INSERT INTO public.b05_invitation_lifecycle_audit"
    ) < audit.index("INSERT INTO public.platform_institution_audit_log")
    assert "ON CONFLICT DO NOTHING" in audit and "IF NOT FOUND THEN RETURN" in audit
    assert "WHEN p_repair THEN 'repair_actor'" in audit
    assert audit.index("IF p_repair THEN RETURN") < audit.index(
        "INSERT INTO public.platform_institution_audit_log"
    )
    assert "PRIMARY KEY (kind,invitation_id,status)" in source
    assert (
        "trg_b05_lifecycle_audit AFTER UPDATE OF status ON public.platform_admin_invitations"
        in source
    )
    assert (
        "trg_b05_platform_lifecycle_audit AFTER UPDATE OF status ON public.platform_super_admin_invitations"
        in source
    )
    legacy = source.split("CREATE FUNCTION public.b05_decide_legacy_membership", 1)[
        1
    ].split("$$;", 1)[0]
    assert (
        legacy.index("FOR UPDATE")
        < legacy.index("UPDATE public.institution_membership_requests")
        < legacy.index("PERFORM public.phase81_assign_institution_role_audited")
        < legacy.index("INSERT INTO public.admin_audit_log")
    )
    assert "decided_by_user_id IS DISTINCT FROM p_actor_user_id" in legacy
    assert "decision_reason IS DISTINCT FROM p_reason" in legacy
    assert "DELETE" not in legacy
    assert source.rstrip().endswith("COMMIT;")


def test_expiry_candidate_rpc_is_bounded_and_can_repair_terminal_audits():
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = [
        {"invitation_id": INV, "status": "expired"}
    ]
    assert repo.list_expiring_pending_invitations(client, limit=10000) == [
        {"invitation_id": INV, "status": "expired"}
    ]
    client.rpc.assert_called_once_with("b05_expiry_candidates", {"p_limit": 200})
    client.table.assert_not_called()
    source = (
        SQL.read_text(encoding="utf-8")
        .split("CREATE FUNCTION public.b05_expiry_candidates", 1)[1]
        .split("$$;", 1)[0]
    )
    assert "i.status = 'expired' AND NOT EXISTS" in source
    assert "public.b05_invitation_lifecycle_audit" in source
    assert "to_jsonb(i) - 'token_hash'" in source


def test_stopped_successor_has_exact_post_b05_layout_and_preserves_original():
    import hashlib

    review = ROOT / "docs/reviews/student_enrollment_final_2026-10-11"
    original = (review / "SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql").read_bytes()
    successor = (
        review / "SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql"
    ).read_text(encoding="utf-8")
    assert (
        hashlib.sha256(original).hexdigest()
        == "897a4c786adc487bce04462690f8a4bbcab215f2e3e53841f84a82f40c1a63c7"
    )
    source = original.decode("utf-8")
    assert "NOT attisdropped)<>11 THEN" in source
    assert "NOT attisdropped)<>12 THEN" in successor
    assert "('decision_key','text')" in successor
    assert (
        "attnum=12 AND NOT attisdropped AND NOT attnotnull AND NOT atthasdef"
        in successor
    )
    assert "public.b05_decision_audit_key" in successor
    import re

    ledger = successor.split(
        "FROM supabase_migrations.schema_migrations) IS DISTINCT FROM ARRAY[", 1
    )[1].split("]::text[] THEN", 1)[0]
    versions = re.findall(r"'(\d{14})'", ledger)
    current_versions = sorted(
        path.name.split("_", 1)[0]
        for path in (ROOT / "supabase/migrations").glob("*.sql")
    )
    assert versions == current_versions[: len(versions)]
    assert len(versions) == 40 and versions[-1] == "20261017000000"
    # Exact retained stop statements, not merely a count of RAISE EXCEPTIONs.
    stops = [
        line
        for line in source.splitlines()
        if line.startswith("DO $review_stop$")
        or line.startswith("DO $dependency_stop$")
    ]
    assert len(stops) == 2
    for stop in stops:
        assert stop in successor
    assert source.rstrip().endswith("ROLLBACK;") and successor.rstrip().endswith(
        "ROLLBACK;"
    )


def test_legacy_routine_identities_and_authorization_are_not_replaced():
    source = SQL.read_text(encoding="utf-8")
    assert "phase723_approve_membership_with_invitation" not in "\n".join(
        line
        for line in source.splitlines()
        if line.startswith(("CREATE", "DROP", "ALTER", "REVOKE", "GRANT"))
    )
    assignment = source.split(
        "CREATE FUNCTION public.phase81_assign_institution_role_audited(", 1
    )[1].split(") RETURNS", 1)[0]
    assert (
        "p_actor_auth_user_id uuid" in assignment
    )  # A distinct five-argument overload.
    assert "DROP FUNCTION" not in source
