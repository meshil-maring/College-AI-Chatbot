"""Persistence boundary for student onboarding invitation RPCs."""

from typing import Any
from uuid import UUID

from supabase import Client


def _data(response: Any) -> Any:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return data[0] if data else None
    return data


def create(client: Client, *, actor: str, tenant: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    return _data(client.rpc("create_student_onboarding_invitation", {
        "p_actor": actor,
        "p_tenant": str(tenant),
        "p_email": payload["email"],
        "p_student_name": payload["student_name"],
        "p_register_number": payload["register_number"],
        "p_university_roll_number": payload.get("university_roll_number"),
        "p_section": payload["academic_section_id"],
        "p_token_hash": payload["token_hash"],
        "p_expires_at": payload["expires_at"],
    }).execute())


def list_pending(client: Client, *, actor: str, tenant: UUID) -> list[dict[str, Any]]:
    data = _data(client.rpc("read_student_onboarding_invitations", {
        "p_actor": actor, "p_tenant": str(tenant),
    }).execute())
    return data if isinstance(data, list) else []


def review_identity(
    client: Client, *, actor: str, tenant: UUID, identity: dict[str, Any],
) -> dict[str, Any]:
    return _data(client.rpc("review_student_onboarding_identity", {
        "p_actor": actor,
        "p_tenant": str(tenant),
        "p_email": identity.get("email"),
        "p_register_number": identity.get("register_number"),
        "p_university_roll_number": identity.get("university_roll_number"),
    }).execute())


def reassign(client: Client, *, actor: str, tenant: UUID, invitation: UUID, section: UUID) -> dict[str, Any]:
    return _data(client.rpc("reassign_student_onboarding_section", {
        "p_actor": actor, "p_tenant": str(tenant),
        "p_invitation": str(invitation), "p_section": str(section),
    }).execute())


def update(
    client: Client, *, actor: str, tenant: UUID, invitation: UUID,
    payload: dict[str, Any], token_hash: str, expires_at: str,
) -> dict[str, Any]:
    return _data(client.rpc("update_student_onboarding_invitation", {
        "p_actor": actor,
        "p_tenant": str(tenant),
        "p_invitation": str(invitation),
        "p_email": payload["email"],
        "p_student_name": payload["student_name"],
        "p_register_number": payload["register_number"],
        "p_university_roll_number": payload.get("university_roll_number"),
        "p_section": payload.get("academic_section_id"),
        "p_token_hash": token_hash,
        "p_expires_at": expires_at,
    }).execute())


def cancel(
    client: Client, *, actor: str, tenant: UUID, invitation: UUID,
) -> dict[str, Any]:
    return _data(client.rpc("cancel_student_onboarding_invitation", {
        "p_actor": actor, "p_tenant": str(tenant),
        "p_invitation": str(invitation),
    }).execute())


def resend(
    client: Client,
    *,
    actor: str,
    tenant: UUID,
    invitation: UUID,
    token_hash: str,
    expires_at: str,
    development_mode: bool,
) -> dict[str, Any]:
    return _data(client.rpc("resend_student_onboarding_invitation", {
        "p_actor": actor, "p_tenant": str(tenant), "p_invitation": str(invitation),
        "p_token_hash": token_hash,
        "p_expires_at": expires_at,
        # This is server-owned configuration, never client input.
        "p_development_mode": development_mode,
    }).execute())


def record_delivery(
    client: Client, *, actor: str, tenant: UUID, invitation: UUID,
    token_hash: str, status: str,
) -> bool:
    return _data(client.rpc("record_student_onboarding_delivery", {
        "p_actor": actor, "p_tenant": str(tenant),
        "p_invitation": str(invitation), "p_token_hash": token_hash, "p_status": status,
    }).execute()) is True


def inspect(client: Client, *, token_hash: str) -> dict[str, Any] | None:
    data = _data(client.rpc("inspect_student_onboarding_invitation", {
        "p_token_hash": token_hash,
    }).execute())
    return data if isinstance(data, dict) else None


def claim_setup(client: Client, *, invitation: UUID, token_hash: str) -> bool:
    return _data(client.rpc("claim_student_onboarding_setup", {
        "p_invitation": str(invitation), "p_token_hash": token_hash,
    }).execute()) is True


def release_setup(client: Client, *, invitation: UUID, token_hash: str) -> bool:
    return _data(client.rpc("release_student_onboarding_setup", {
        "p_invitation": str(invitation), "p_token_hash": token_hash,
    }).execute()) is True


def record_auth_user(client: Client, *, invitation: UUID, token_hash: str, auth_user: str) -> bool:
    return _data(client.rpc("record_student_onboarding_auth_user", {
        "p_invitation": str(invitation), "p_token_hash": token_hash,
        "p_auth_user": auth_user,
    }).execute()) is True


def complete(client: Client, *, invitation: UUID, token_hash: str, auth_user: str) -> dict[str, Any]:
    return _data(client.rpc("complete_student_onboarding_invitation", {
        "p_invitation": str(invitation), "p_token_hash": token_hash,
        "p_auth_user": auth_user,
    }).execute())
