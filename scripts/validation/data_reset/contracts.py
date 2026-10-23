"""Preserved catalogue and immutable-audit contracts for reset validation."""

import json


def configuration_snapshot(execute, catalogs):
    values = ", ".join(
        f"'{table}', (SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), "
        f"'[]'::jsonb) FROM public.{table} t)"
        for table in catalogs
    )
    return json.loads(execute(f"SELECT jsonb_build_object({values});"))


def reset_requires_audit_review(execute, reset):
    """The current append-only audit schema must block historical global resets."""
    guarded = execute(
        "SELECT EXISTS(SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' "
        "AND NOT t.tgisinternal AND (t.tgtype::integer & 32) <> 0)"
    )
    if guarded != "t":
        return False
    snapshot = """
        SELECT md5(jsonb_build_object(
            'auth', (SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM auth.users t),
            'users', (SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM public.users t),
            'roles', (SELECT jsonb_agg(to_jsonb(t) ORDER BY user_id,role_id) FROM public.user_roles t),
            'audit', (SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text) FROM public.admin_audit_log t),
            'orgs', (SELECT jsonb_agg(to_jsonb(t) ORDER BY organization_id) FROM public.organizations t)
        )::text)
    """
    before = execute(snapshot)
    execute(reset, expect_success=False)
    assert execute(snapshot) == before
    print(
        "PASS: immutable audit protection rejects global reset and preserves all accounts",
        flush=True,
    )
    return True
