"""Student account approval with tenant checks and atomic provisioning."""

import logging
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import admin_academics as academics_repo

logger = logging.getLogger(__name__)


def _approval_tenant_mismatch() -> AppError:
    return AppError(
        "This resource belongs to a different institution",
        status_code=403,
        code="TENANT_MISMATCH",
    )


def list_pending_approvals(
    institution_id: UUID | str | None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List pending accounts for the trusted scope supplied by the API.

    Public approval routes require an active institution grant. The optional
    None scope remains an internal repository contract, not a global API queue."""
    db = get_admin_client()
    return academics_repo.list_pending_students(
        db, institution_id, limit=limit, offset=offset
    )


def _resolve_approval_target(
    student_id: UUID | str,
    institution_id: UUID | str | None,
) -> dict:
    """Fetch target student; enforce tenant BEFORE state (no state leak)."""
    db = get_admin_client()
    target = academics_repo.get_student_for_approval(db, student_id)
    if target is None:
        raise AppError("Student not found", status_code=404, code="STUDENT_NOT_FOUND")
    if institution_id is not None and str(target.get("institution_id")) != str(
        institution_id
    ):
        raise _approval_tenant_mismatch()
    return target


def _conditional_approval_write(
    student_id: UUID | str,
    tenant: UUID | str,
    new_status: str,
) -> dict:
    """Apply the conditional pending->new write; map races to 409/404."""
    db = get_admin_client()
    updated = academics_repo.set_student_approval_status(
        db, student_id, tenant, new_status
    )
    if updated is not None:
        return updated
    current = academics_repo.get_student_for_approval(db, student_id)
    if current is None:
        raise AppError("Student not found", status_code=404, code="STUDENT_NOT_FOUND")
    raise AppError(
        f"Student is not pending approval (current: {current.get('approval_status')})",
        status_code=409,
        code="STUDENT_NOT_PENDING",
    )


def approve_student(student_id, institution_id, *, actor=None) -> dict:
    """Approve, provision the student grant and persist decision audit atomically.

    Same authorization as the current API: institution-scoped admin or staff.
    Existing approved rows are repairable through the same authorized command.
    """
    if (
        not actor
        or not actor.get("user_id")
        or not actor.get("auth_user_id")
        or institution_id is None
        or not set(actor.get("roles", [])) & {"admin", "staff"}
    ):
        raise AppError("Verified student approver required", 403, "FORBIDDEN")
    target = _resolve_approval_target(student_id, institution_id)
    if target.get("approval_status") not in ("pending", "approved"):
        raise AppError("Student has a different decision", 409, "STUDENT_NOT_PENDING")
    try:
        result = academics_repo.approve_student_and_provision(
            get_admin_client(),
            student_id=student_id,
            institution_id=institution_id,
            actor_user_id=actor["user_id"],
            actor_auth_user_id=actor["auth_user_id"],
        )
    except AppError:
        raise
    except Exception as exc:
        if isinstance(exc, APIError) and exc.code in {"PGRST202", "42883", "42703"}:
            logger.warning(
                "event=student_approval_unavailable category=database_schema"
            )
            raise AppError(
                "Student approval is unavailable. Contact your platform administrator.",
                status_code=503,
                code="STUDENT_APPROVAL_UNAVAILABLE",
            ) from None
        raise AppError(
            "Student approval requires retry or reconciliation",
            409,
            "STUDENT_PROVISIONING_UNCERTAIN",
        ) from exc
    if result.get("not_found"):
        raise AppError("Student not found", 404, "STUDENT_NOT_FOUND")
    if result.get("conflict"):
        raise AppError("Student has a different decision", 409, "STUDENT_NOT_PENDING")
    if not (
        result.get("role_granted")
        and result.get("audit_persisted")
        and isinstance(result.get("student"), dict)
        and result["student"].get("approval_status") == "approved"
    ):
        raise AppError(
            "Student provisioning did not complete",
            409,
            "STUDENT_PROVISIONING_UNCERTAIN",
        )
    return result["student"]


def reject_student(
    student_id: UUID | str,
    institution_id: UUID | str | None,
) -> dict:
    """Reject a pending account while preserving its identity and credentials.

    Institution API callers always supply their verified tenant. Internal callers
    may resolve the target tenant before the conditional pending-only write."""
    target = _resolve_approval_target(student_id, institution_id)
    if target.get("approval_status") != "pending":
        raise AppError(
            f"Student is not pending approval (current: {target.get('approval_status')})",
            status_code=409,
            code="STUDENT_NOT_PENDING",
        )
    tenant = (
        institution_id if institution_id is not None else target.get("institution_id")
    )
    return _conditional_approval_write(student_id, tenant, "rejected")
