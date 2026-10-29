"""Run-owned confirmed test accounts; no invitations or credential logs."""

from contextlib import contextmanager
from datetime import date
import secrets
from uuid import uuid4

from app.config import settings


@contextmanager
def accounts(db, tenant, evidence, save):
    if not settings.is_local_environment:
        raise RuntimeError("Live acceptance requires development/test settings")
    institution = db.table("institutions").select("organization_id,status,is_active").eq(
        "institution_id", tenant).single().execute().data
    if institution["status"] != "active" or not institution["is_active"]:
        raise RuntimeError("Test institution is inactive")
    owned = []
    credentials = {}
    evidence["accounts"] = owned
    try:
        for role in ("admin", "staff", "faculty", "student"):
            actor = str(uuid4())
            email = f"qa-chat-{evidence['run']}-{role}@example.com"
            password = secrets.token_urlsafe(32)
            account = db.auth.admin.create_user({
                "email": email, "password": password, "email_confirm": True,
                "user_metadata": {"collegeai_chat_validation": evidence["run"]},
            })
            record = {"user_id": actor, "auth_user_id": str(account.user.id), "role": role}
            owned.append(record)
            save()
            db.table("users").insert({
                "id": actor, "auth_user_id": record["auth_user_id"], "email": email,
                "first_name": "Chat Acceptance", "last_name": role, "status": "active",
            }).execute()
            role_id = db.table("roles").select("id").eq("name", role).eq(
                "is_active", True).single().execute().data["id"]
            db.table("user_roles").insert({
                "user_id": actor, "role_id": role_id, "scope_type": "institution",
                "scope_id": tenant, "scope_organization_id": institution["organization_id"],
            }).execute()
            if role == "student":
                db.table("students").insert({
                    "user_id": actor, "institution_id": tenant, "student_number": "CHAT-" + evidence["run"],
                    "enrollment_date": date.today().isoformat(), "approval_status": "approved", "is_active": True,
                }).execute()
            credentials[role] = {"email": email, "password": password, "user_id": actor}
        print("PASS: four run-owned accounts created without sending email", flush=True)
        yield credentials
    finally:
        failures = []
        for record in owned:
            actions = {
                "roles_removed": lambda: db.table("user_roles").delete().eq("user_id", record["user_id"]).execute(),
                "inactive": lambda: db.table("users").update({"status": "inactive"}).eq(
                    "id", record["user_id"]).eq("auth_user_id", record["auth_user_id"]).execute(),
                "auth_banned": lambda: db.auth.admin.update_user_by_id(
                    record["auth_user_id"], {"ban_duration": "876000h"}),
            }
            if record["role"] == "student":
                actions["student_inactive"] = lambda: db.table("students").update({"is_active": False}).eq(
                    "user_id", record["user_id"]).execute()
            for name, action in actions.items():
                try:
                    action()
                    record[name] = True
                except Exception as failure:
                    record[name] = False
                    failures.append(f"{record['role']}:{name}:{type(failure).__name__}")
            save()
        if failures:
            raise RuntimeError("Account cleanup incomplete: " + ", ".join(failures))
        print("PASS: test accounts inactive, grants removed and Auth sign-in blocked", flush=True)
