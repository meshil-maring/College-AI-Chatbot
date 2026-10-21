"""Recover only recorded progress; never repeat an uncertain account creation.

All operation writes lock invitation then operation in SQL. No provider call
runs inside a SQL transaction. A lost create response requires provider evidence
from an authorized operator; token possession cannot establish its outcome.
"""
from app.core.errors import AppError
from app.repositories.invitations import platform_admin_invitations as repo
from app.services.auth import student_registration as accounts


def reconciliation():
    return AppError(
        "This acceptance requires reconciliation. Contact your administrator.",
        409, "INVITATION_RECONCILIATION_REQUIRED",
    )


def recover_accepted_account(client, invitation, token_hash, *, kind="institution"):
    """Resolve canonical IDs under database locks; confirmation is the only I/O."""
    operation = repo.recover_accepted_operation(
        client, invitation["invitation_id"], token_hash, kind=kind,
    )
    if not operation or not operation.get("new_account") or operation.get("stage") not in ("accepted", "confirmed"):
        raise reconciliation()
    if operation["stage"] == "confirmed":
        return
    accounts._confirm_invited_auth_account(client, operation["auth_user_id"])
    if not repo.advance_operation(client, operation["acceptance_id"],
                                  expected_stage="accepted", stage="confirmed"):
        current = repo.recover_accepted_operation(client, invitation["invitation_id"], token_hash, kind=kind)
        if not current or current.get("stage") != "confirmed":
            raise reconciliation()


def complete_acceptance(client, invitation, operation, *, acceptance_id, token_hash, payload, kind="institution"):
    if not operation or operation.get("reconciliation_required"):
        raise reconciliation()
    acceptance_id = operation["acceptance_id"]
    stage = operation["stage"]
    auth_id, user_id = operation.get("auth_user_id"), operation.get("user_id")
    if stage == "reserved":
        if payload is None:
            raise reconciliation()
        # CAS before I/O: a competing retry cannot also create an account.
        started = repo.advance_operation(client, acceptance_id, expected_stage="reserved", stage="provider_started")
        if not started:
            raise reconciliation()
        auth_id = accounts._create_auth_account(str(invitation["email"]), payload.password, invitation_only=True)
        recorded = repo.advance_operation(client, acceptance_id, expected_stage="provider_started",
                                          stage="provider_created", auth_user_id=auth_id)
        if not recorded:
            raise reconciliation()
        stage = "provider_created"
    if stage == "provider_started":
        raise reconciliation()
    if stage == "provider_created":
        if not auth_id:
            raise reconciliation()
        # The provisioning RPC inserts or resolves by the recorded Auth ID and
        # persists user_id in the same transaction; lost responses are recoverable.
        recorded = repo.advance_operation(
            client, acceptance_id, expected_stage="provider_created", stage="user_created",
            auth_user_id=auth_id, first_name=payload.first_name if payload else None,
            last_name=payload.last_name if payload else None,
        )
        if not recorded:
            raise reconciliation()
        user_id = recorded["user_id"]
        stage = "user_created"
    if stage == "user_created":
        claimed = repo.claim_invitation(client, invitation["invitation_id"], kind=kind,
                                       token_hash=token_hash, acceptance_id=acceptance_id,
                                       accepted_user_id=user_id)
        if not claimed or not claimed.get("accepted"):
            raise reconciliation()
        stage = "accepted"
    if stage == "accepted" and operation["new_account"]:
        accounts._confirm_invited_auth_account(client, auth_id)
        if not repo.advance_operation(client, acceptance_id, expected_stage="accepted", stage="confirmed"):
            raise reconciliation()
        stage = "confirmed"
    if stage not in ("accepted", "confirmed"):
        raise reconciliation()
