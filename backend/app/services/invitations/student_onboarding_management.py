"""Institution-scoped edits and cancellation for pending student invitations."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.repositories.invitations import student_onboarding as repository
from app.schemas.invitations.student_onboarding import StudentInvitationCancelResponse
from app.schemas.invitations.student_onboarding_management import (
    StudentInvitationUpdateResponse,
)
from app.services.invitations.student_onboarding import (
    INVITATION_TTL,
    admin_context,
    deliver_setup_link,
    project_invitation,
)
from app.services.invitations.student_onboarding_common import database, token


def _run(operation):
    try:
        return database(operation)
    except AppError as exc:
        if exc.code == "INVITATION_INVALID":
            raise AppError(
                "Pending student invitation not found or no longer available.",
                404,
                "INVITATION_NOT_FOUND",
            ) from exc
        raise


def update(
    actor: dict[str, Any], invitation_id: UUID, payload: dict[str, Any]
) -> StudentInvitationUpdateResponse:
    required = ("students.update",)
    if payload.get("academic_section_id") is not None:
        required += ("courses.manage",)
    client, tenant, actor_id = admin_context(
        actor,
        required,
        denied_message="You do not have permission to edit this student invitation.",
    )
    raw_token, token_hash = token()
    expires_at = datetime.now(timezone.utc) + INVITATION_TTL
    row = _run(
        lambda: repository.update(
            client,
            actor=actor_id,
            tenant=tenant,
            invitation=invitation_id,
            payload=payload,
            token_hash=token_hash,
            expires_at=expires_at.isoformat(),
        )
    )
    email_changed = row.get("email_changed") is True
    if not email_changed:
        return StudentInvitationUpdateResponse(
            invitation=project_invitation(row),
            email_changed=False,
        )
    delivery = deliver_setup_link(
        client, tenant, actor_id, row, raw_token, expires_at
    )
    return StudentInvitationUpdateResponse(
        invitation=delivery.invitation,
        email_changed=True,
        delivery_status=delivery.delivery_status,
        delivery_message=delivery.delivery_message,
    )


def cancel(
    actor: dict[str, Any], invitation_id: UUID
) -> StudentInvitationCancelResponse:
    client, tenant, actor_id = admin_context(
        actor,
        ("students.delete",),
        denied_message="You do not have permission to cancel this student invitation.",
    )
    result = _run(
        lambda: repository.cancel(
            client, actor=actor_id, tenant=tenant, invitation=invitation_id
        )
    )
    return StudentInvitationCancelResponse.model_validate(result)
