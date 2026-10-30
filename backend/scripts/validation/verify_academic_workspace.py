"""Read configured Academic Setup APIs through a database-resolved admin scope.

Run from backend/. This performs catalogue reads only and prints counts without
tokens, identities, names, emails or record contents. It creates no sessions and
does not impersonate a user over HTTP; HTTP authentication is covered separately.
"""

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.supabase import get_admin_client, get_user_by_auth_id
from app.services.academics.academic_setup import get_setup
from app.services.academics.academic_structure import get_structure
from app.services.academics.semester_registration import catalogue as get_registration
from app.services.auth.authorization import resolve_institution_authorization_context


async def verify():
    client = get_admin_client()
    grants = client.table("user_roles").select(
        "user_id,scope_id,roles!inner(name,is_active)"
    ).eq("scope_type", "institution").eq("roles.name", "admin").eq(
        "roles.is_active", True
    ).limit(20).execute().data
    for grant in grants or []:
        account = client.table("users").select("auth_user_id").eq(
            "id", grant["user_id"]
        ).eq("status", "active").maybe_single().execute()
        if not account or not account.data:
            continue
        user = await get_user_by_auth_id(account.data["auth_user_id"], include_permissions=True)
        if not user:
            continue
        context = resolve_institution_authorization_context(user, allowed_roles=("admin",))
        user["institution_id"] = str(context.institution_id)
        base = get_setup(user)
        structure = get_structure(user)
        registration = get_registration(user)
        assert str(base.institution_id) == str(structure.institution_id) == str(context.institution_id)
        assert registration["institution_id"] == str(context.institution_id)
        for catalogue in (base, structure):
            for records in catalogue.records.values():
                assert all(str(row["institution_id"]) == str(context.institution_id) for row in records)
        return {
            "tenant_verified": True,
            "base_catalogues": {str(entity): len(rows) for entity, rows in base.records.items()},
            "structure_catalogues": {str(entity): len(rows) for entity, rows in structure.records.items()},
            "manageable_structure_entities": sorted(str(entity) for entity in structure.manageable),
            "recent_academic_events": len(structure.activities),
            "registration_catalogue": {
                "subject_option_groups": len(registration["groups"]),
                "eligible_students": len(registration["students"]),
                "semester_assignments": len(registration["assignments"]),
                "can_manage_choices": registration["can_manage_choices"],
                "can_assign": registration["can_assign"],
            },
        }
    raise RuntimeError("No active institution administrator was available for the read-only check")


if __name__ == "__main__":
    try:
        print(json.dumps(asyncio.run(verify()), indent=2))
    except Exception as error:
        print(json.dumps({"verified": False, "error_type": type(error).__name__}))
        raise SystemExit(1) from None
