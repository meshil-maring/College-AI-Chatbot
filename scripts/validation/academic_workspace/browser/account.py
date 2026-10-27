"""Run-owned development administrator; no invitations, email or password logs."""

from contextlib import contextmanager
import json
from pathlib import Path
import secrets
from uuid import uuid4

from app.config import settings


@contextmanager
def test_administrator(client, tenant, log_dir):
    if not settings.is_local_environment:
        raise RuntimeError("Browser test account requires a development/test configuration")
    institution = client.table("institutions").select(
        "organization_id,status,is_active"
    ).eq("institution_id", tenant).single().execute().data
    if institution["status"] != "active" or not institution["is_active"]:
        raise RuntimeError("Selected browser-test institution is inactive")
    run = uuid4().hex
    email = f"qa-browser-{run}@example.com"
    password = secrets.token_urlsafe(32)
    auth_id, actor = None, str(uuid4())
    evidence = {"run": run, "institution_id": tenant, "user_id": actor, "disabled": False}
    try:
        account = client.auth.admin.create_user({
            "email": email, "password": password, "email_confirm": True,
            "user_metadata": {"collegeai_validation_run": run},
        })
        auth_id = str(account.user.id)
        evidence["auth_user_id"] = auth_id
        client.table("users").insert({
            "id": actor, "auth_user_id": auth_id, "email": email,
            "first_name": "Browser", "last_name": "Reliability Test", "status": "active",
        }).execute()
        role = client.table("roles").select("id").eq("name", "admin").eq("is_active", True).single().execute().data
        client.table("user_roles").insert({
            "user_id": actor, "role_id": role["id"], "scope_type": "institution",
            "scope_id": tenant, "scope_organization_id": institution["organization_id"],
        }).execute()
        print("CREATED: run-owned development test administrator; no email sent", flush=True)
        yield {"email": email, "password": password, "prefix": "E2E" + run[:8].upper(), "user_id": actor}
    finally:
        if auth_id:
            # Retain the inactive application identity for any academic audit
            # events; revoke only this run's grant and block future sign-in.
            operations = {
                "roles_removed": lambda: client.table("user_roles").delete().eq("user_id", actor).execute(),
                "application_inactive": lambda: client.table("users").update({"status": "inactive"})
                    .eq("id", actor).eq("auth_user_id", auth_id).execute(),
                "auth_banned": lambda: client.auth.admin.update_user_by_id(auth_id, {"ban_duration": "876000h"}),
            }
            for name, operation in operations.items():
                try:
                    operation()
                    evidence[name] = True
                except Exception as error:
                    evidence[name] = False
                    print(f"CLEANUP FAILED: {name} ({type(error).__name__}); inspect run evidence", flush=True)
            evidence["disabled"] = all(evidence[name] for name in operations)
        Path(log_dir, f"browser-account-{run}.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        if auth_id and not evidence["disabled"]:
            raise RuntimeError("Browser administrator cleanup incomplete; inspect run evidence")
        print("CLEANUP: browser test administrator disabled and its role removed", flush=True)
