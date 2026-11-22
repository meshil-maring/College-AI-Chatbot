"""Account history of one Staff, Faculty or administrator (User Management U10).

Reads the institution's own audit entries about the person: invitations,
role, status and department changes, profile edits and responsibilities. The
person must belong to the administrator's institution, so another tenant's
history is never readable.
"""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import admin_audit
from app.repositories.admin import admin_memberships as membership_repo
from app.schemas.admin.member_profiles import MemberHistory, MemberHistoryEntry

MEMBER_ROLES = frozenset({"staff", "faculty", "admin"})

# Readable descriptions of the recorded actions; unknown ones fall back to the code.
LABELS = {
    "role.assignment": "Role granted",
    "member.role.change": "Role changed",
    "member.department.assign": "Primary department set",
    "member.departments.additional": "Additional departments changed",
    "member.profile.saved": "Employee profile saved",
    "staff_suspended": "Suspended", "faculty_suspended": "Suspended",
    "staff_deactivated": "Deactivated", "faculty_deactivated": "Deactivated",
    "staff_reactivated": "Reactivated", "faculty_reactivated": "Reactivated",
    "academic.department.head.add": "Appointed Head of Department",
    "academic.department.head.end": "Head of Department appointment ended",
    "academic.department.head.expired": "Head of Department term ran out",
    "academic.department.head.term": "Head of Department dates changed",
    "academic.department.head": "Head of Department changed",
    "member.responsibility.assign": "Responsibility assigned",
    "member.responsibility.end": "Responsibility ended",
    "institution.admin.revoke": "Administrator access removed",
    "institution.owner.transfer": "Ownership transferred",
}


def _require_person(client, institution_id: UUID, user_id: UUID) -> None:
    for grant in membership_repo.list_user_grants(client, user_id):
        role = (grant.get("roles") or {}).get("name")
        if (
            role in MEMBER_ROLES
            and grant.get("scope_type") == "institution"
            and str(grant.get("scope_id")) == str(institution_id)
        ):
            return
    raise AppError("Member not found", 404, "MEMBER_NOT_FOUND")


def _actor_names(client, actor_ids: set[str]) -> dict[str, str]:
    if not actor_ids:
        return {}
    rows = (
        client.table("users").select("id, email, first_name, last_name").in_("id", sorted(actor_ids)).execute().data
        or []
    )
    names = {}
    for row in rows:
        name = " ".join(part for part in [row.get("first_name"), row.get("last_name")] if part)
        names[str(row["id"])] = name or str(row.get("email") or "")
    return names


def history(institution_id: UUID, user_id: UUID) -> MemberHistory:
    client = get_admin_client()
    _require_person(client, institution_id, user_id)
    rows: list[dict[str, Any]] = admin_audit.list_member_history(client, institution_id, user_id)
    names = _actor_names(client, {str(row["actor_user_id"]) for row in rows if row.get("actor_user_id")})
    entries = [
        MemberHistoryEntry(
            audit_id=row["audit_id"],
            action=row["action"],
            label=LABELS.get(str(row["action"]), str(row["action"]).replace("_", " ").replace(".", " ")),
            actor_name=names.get(str(row.get("actor_user_id")), "System"),
            performed_at=row["performed_at"],
            details=row.get("record_data") if isinstance(row.get("record_data"), dict) else {},
        )
        for row in rows
    ]
    return MemberHistory(user_id=user_id, entries=entries)
