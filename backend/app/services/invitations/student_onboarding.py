"""Institution-scoped student invitation lifecycle and account activation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.core.permissions import permission_matches
from app.db.supabase import get_admin_client
from app.repositories.invitations import student_onboarding as repository
from app.schemas.invitations.student_onboarding import (
    StudentIdentityInput,
    StudentIdentityReviewRequest,
    StudentIdentityReviewResponse,
    StudentInvitationBulkRequest,
    StudentInvitationBulkRow,
    StudentInvitationBulkResponse,
    StudentInvitationCreatedResponse,
    StudentInvitationListResponse,
    StudentInvitationRowResult,
    StudentInvitationView,
)
from app.services.academics.authorization import scope, validated_scope_permissions
from app.services.invitations.student_onboarding_common import (
    database as _database,
    token as _token,
)
from app.services.invitations import student_onboarding_email as invitation_email

INVITATION_TTL = timedelta(minutes=10)
REQUIRED_ADMIN_PERMISSIONS = (
    "students.create", "students.approve", "students.update", "students.read", "courses.manage",
)


def admin_context(
    actor: dict[str, Any],
    required_permissions: tuple[str, ...] = REQUIRED_ADMIN_PERMISSIONS,
    denied_message: str = "You do not have permission to provision students.",
) -> tuple[Any, UUID, str]:
    tenant, _ = scope(actor)
    if not isinstance(tenant, UUID):
        tenant = UUID(str(tenant))
    client = get_admin_client()
    permissions = validated_scope_permissions(client, actor, tenant)
    if any(not permission_matches(permissions, code) for code in required_permissions):
        raise AppError(
            denied_message,
            403,
            "FORBIDDEN",
        )
    return client, tenant, str(actor["user_id"])


def _admin(actor: dict[str, Any]) -> tuple[Any, UUID, str]:
    return admin_context(actor)


def project_invitation(row: dict[str, Any]) -> StudentInvitationView:
    fields = StudentInvitationView.model_fields
    values = {key: row.get(key) for key in fields}
    if "resend_count" not in row:
        values["resend_count"] = row.get("resend_window_count", 0)
    return StudentInvitationView.model_validate(values)


def _issue(client, tenant, actor_id, identity: StudentIdentityInput | StudentInvitationBulkRow, section_id: UUID):
    raw_token, token_hash = _token()
    expires_at = datetime.now(timezone.utc) + INVITATION_TTL
    payload = identity.model_dump(mode="json")
    payload.update({
        "academic_section_id": str(section_id),
        "token_hash": token_hash,
        "expires_at": expires_at.isoformat(),
    })
    row = _database(lambda: repository.create(
        client, actor=actor_id, tenant=tenant, payload=payload,
    ))
    return deliver_setup_link(client, tenant, actor_id, row, raw_token, expires_at)


def deliver_setup_link(client, tenant, actor_id, row, raw_token, expires_at):
    attempt = int(row.get("email_delivery_attempts") or 0) + 1
    try:
        result = invitation_email.send_setup_link(
            to_email=row["email"],
            institution_name=str(row.get("institution_name") or "your institution"),
            student_name=row["student_name"],
            batch_code=str(row.get("batch_code") or "assigned batch"),
            section_name=str(row.get("section_name") or "assigned section"),
            raw_token=raw_token,
            expires_at=expires_at,
            invitation_id=str(row["invitation_id"]),
            attempt=attempt,
        )
        status = "sent" if result.status == "sent" else "failed"
    except AppError as exc:
        if exc.code != "EMAIL_NOT_CONFIGURED":
            raise
        status = "failed"
    recorded = _database(lambda: repository.record_delivery(
        client, actor=actor_id, tenant=tenant,
        invitation=UUID(str(row["invitation_id"])),
        token_hash=str(row["token_hash"]), status=status,
    ))
    if not recorded:
        raise AppError("Invitation delivery status could not be recorded. Refresh before retrying.", 503, "DELIVERY_STATUS_UNAVAILABLE")
    row.update({
        "email_delivery_status": status,
        "email_delivery_attempts": attempt,
        "last_sent_at": datetime.now(timezone.utc).isoformat() if status == "sent" else row.get("last_sent_at"),
    })
    return StudentInvitationCreatedResponse(
        invitation=project_invitation(row),
        delivery_status=status,
        delivery_message=invitation_email.delivery_message(status),
    )


def create_invitation(actor: dict[str, Any], payload) -> StudentInvitationCreatedResponse:
    client, tenant, actor_id = _admin(actor)
    return _issue(client, tenant, actor_id, payload, payload.academic_section_id)


def create_bulk(actor: dict[str, Any], payload: StudentInvitationBulkRequest) -> StudentInvitationBulkResponse:
    client, tenant, actor_id = _admin(actor)
    seen: set[tuple[str, str]] = set()
    results: list[StudentInvitationRowResult] = []
    for identity in payload.students:
        index = identity.source_row
        keys = {
            ("email", identity.email.casefold()),
            ("register", identity.register_number.casefold()),
        }
        if identity.university_roll_number:
            keys.add(("roll", identity.university_roll_number.casefold()))
        if seen.intersection(keys):
            results.append(StudentInvitationRowResult(
                row=index, status="duplicate", message="Duplicates another row in this upload.",
            ))
            continue
        seen.update(keys)
        try:
            created = _issue(client, tenant, actor_id, identity, payload.academic_section_id)
        except AppError as exc:
            results.append(StudentInvitationRowResult(row=index, status="failed", message=exc.message))
            continue
        results.append(StudentInvitationRowResult(
            row=index,
            status="created",
            invitation=created.invitation,
            delivery_status=created.delivery_status,
            message=created.delivery_message,
        ))
    created_count = sum(result.status == "created" for result in results)
    return StudentInvitationBulkResponse(
        total=len(results), created=created_count,
        failed=len(results) - created_count, rows=results,
    )


def list_pending(actor: dict[str, Any]) -> StudentInvitationListResponse:
    client, tenant, actor_id = _admin(actor)
    rows = _database(lambda: repository.list_pending(client, actor=actor_id, tenant=tenant))
    return StudentInvitationListResponse(invitations=[project_invitation(row) for row in rows])


def review_identity(
    actor: dict[str, Any], payload: StudentIdentityReviewRequest,
) -> StudentIdentityReviewResponse:
    client, tenant, actor_id = _admin(actor)
    result = _database(lambda: repository.review_identity(
        client,
        actor=actor_id,
        tenant=tenant,
        identity=payload.model_dump(mode="json"),
    ))
    return StudentIdentityReviewResponse.model_validate(result)


def reassign(actor: dict[str, Any], invitation_id: UUID, section_id: UUID) -> StudentInvitationView:
    client, tenant, actor_id = _admin(actor)
    row = _database(lambda: repository.reassign(
        client, actor=actor_id, tenant=tenant, invitation=invitation_id, section=section_id,
    ))
    return project_invitation(row)


def resend(actor: dict[str, Any], invitation_id: UUID) -> StudentInvitationCreatedResponse:
    client, tenant, actor_id = _admin(actor)
    raw_token, token_hash = _token()
    expires_at = datetime.now(timezone.utc) + INVITATION_TTL
    row = _database(lambda: repository.resend(
        client, actor=actor_id, tenant=tenant, invitation=invitation_id,
        token_hash=token_hash, expires_at=expires_at.isoformat(),
    ))
    return deliver_setup_link(client, tenant, actor_id, row, raw_token, expires_at)
