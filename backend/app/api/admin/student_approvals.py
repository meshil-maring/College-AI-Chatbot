"""Institution-scoped student account approval endpoints."""

from uuid import UUID

from fastapi import Depends

from app.core.errors import AppError
from app.core.security import scope_tenant, user_tenant_id
from app.services.admin import admin_academics
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _APPROVAL

router = create_feature_router()


def _approval_scope(current_user: dict) -> tuple[UUID | None, bool]:
    """Return the active institution already verified by the approval dependency."""
    tenant = user_tenant_id(current_user)
    if tenant is None:
        raise AppError(
            "No institution scope could be resolved for this account",
            status_code=403,
            code="SCOPE_MISSING",
        )
    return tenant, False


@router.get("/students/pending")
def list_pending_students(
    institution_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(_APPROVAL),
) -> list[dict]:
    """List pending account approvals for the caller's own institution.

    A foreign institution filter is rejected with TENANT_MISMATCH."""
    tenant, _is_platform_admin = _approval_scope(current_user)
    effective = scope_tenant(current_user, institution_id)
    return admin_academics.list_pending_approvals(effective, limit=limit, offset=offset)


@router.post("/students/{student_id}/approve")
def approve_student(student_id: UUID, current_user: dict = Depends(_APPROVAL)) -> dict:
    """Approve a pending student (pending -> approved)."""
    tenant, _is_platform_admin = _approval_scope(current_user)
    approved = admin_academics.approve_student(student_id, tenant, actor=current_user)
    return approved


@router.post("/students/{student_id}/reject")
def reject_student(student_id: UUID, current_user: dict = Depends(_APPROVAL)) -> dict:
    """Reject a pending student (pending -> rejected; record preserved)."""
    tenant, _is_platform_admin = _approval_scope(current_user)
    rejected = admin_academics.reject_student(student_id, tenant)
    common.record_audit(
        current_user,
        "student.reject",
        "students",
        str(student_id),
        {"approval_status": "rejected"},
    )
    return rejected
