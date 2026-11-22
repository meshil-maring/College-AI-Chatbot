"""Institution administrators and the Owner, through audited database commands.

Every command re-checks the actor in the database: reads need an active
administrator, changes need the institution's current Owner.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client


def _call(client: Client, name: str, params: dict[str, Any]) -> dict[str, Any]:
    data = client.rpc(name, params).execute().data
    if not isinstance(data, dict):
        raise RuntimeError(f"{name} returned no result")
    return data


def read(client: Client, actor_id: UUID | str, institution_id: UUID | str) -> dict[str, Any]:
    return _call(client, "read_institution_admins", {"p_actor": str(actor_id), "p_tenant": str(institution_id)})


def create_invitation(
    client: Client, *, actor_id: UUID | str, institution_id: UUID | str, email: str, full_name: str | None,
    token_hash: str, expires_at: datetime, protected_token: str,
) -> dict[str, Any]:
    return _call(client, "create_admin_invitation", {
        "p_actor": str(actor_id), "p_tenant": str(institution_id), "p_email": email,
        "p_full_name": full_name, "p_token_hash": token_hash,
        "p_expires_at": expires_at.isoformat(), "p_protected_token": protected_token,
    })


def cancel_invitation(client: Client, actor_id: UUID | str, institution_id: UUID | str, invitation_id: UUID) -> dict:
    return _call(client, "cancel_admin_invitation", {
        "p_actor": str(actor_id), "p_tenant": str(institution_id), "p_invitation": str(invitation_id),
    })


def revoke(client: Client, actor_id: UUID | str, institution_id: UUID | str, user_id: UUID) -> dict[str, Any]:
    return _call(client, "revoke_institution_admin", {
        "p_actor": str(actor_id), "p_tenant": str(institution_id), "p_user": str(user_id),
    })


def transfer_ownership(client: Client, actor_id: UUID | str, institution_id: UUID | str, user_id: UUID) -> dict:
    return _call(client, "transfer_institution_ownership", {
        "p_actor": str(actor_id), "p_tenant": str(institution_id), "p_new_owner": str(user_id),
    })
