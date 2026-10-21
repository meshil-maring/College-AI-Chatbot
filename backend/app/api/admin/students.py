"""Admin students endpoints."""

from uuid import UUID

from fastapi import Depends

from app.core.errors import AppError
from app.core.security import scope_tenant, user_tenant_id
from app.services.admin import admin_academics
from app.services.admin.admin_academics import StudentCreate, StudentUpdate
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN, _APPROVAL


router = create_feature_router()


@router.get("/students")
def list_students(
    institution_id: UUID,
    program_id: UUID | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    institution_id = common.scope_institution(current_user, institution_id)
    return admin_academics.list_students(
        institution_id,
        program_id=program_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/students", status_code=201)
def create_student(
    payload: StudentCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_row_tenant(current_user, payload.institution_id)
    created = admin_academics.create_student(payload)
    common.record_audit(
        current_user,
        "student.create",
        "students",
        created["student_id"],
        {
            "student_number": payload.student_number,
            "institution_id": str(payload.institution_id),
        },
    )
    return created


def _approval_scope(current_user: dict) -> tuple[UUID | None, bool]:
    """Resolve the approval scope for the authenticated caller.

    The ``_APPROVAL`` dependency has already required an ACTIVE, institution
    scoped grant, so the only accepted outcome is that institution. This helper
    fails closed if that scope is absent (defense in depth — it must never
    degrade to an unrestricted global queue).
    """
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
    """List students awaiting approval.

    Tenant-bound approvers: always scoped to their own institution; a
    requested foreign institution is rejected (403 TENANT_MISMATCH).
    Platform-level admins: global queue, optionally filtered by an explicit
    institution_id (Phase 6.1 platform passthrough).
    """
    tenant, _is_platform_admin = _approval_scope(current_user)
    effective = scope_tenant(current_user, institution_id)
    return admin_academics.list_pending_approvals(
        effective, limit=limit, offset=offset
    )


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


@router.get("/students/{student_id}")
def get_student(student_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    student = admin_academics.get_student(student_id)
    common.assert_row_tenant(current_user, student.get("institution_id"))
    return student


@router.patch("/students/{student_id}")
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_row_tenant(current_user, admin_academics.get_student(student_id).get("institution_id"))
    updated = admin_academics.update_student(student_id, payload)
    common.record_audit(
        current_user,
        "student.update",
        "students",
        str(student_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/students/{student_id}")
def archive_student(student_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    """Soft-archive a student (academic history retained, access ended)."""
    common.assert_row_tenant(current_user, admin_academics.get_student(student_id).get("institution_id"))
    archived = admin_academics.archive_student(student_id)
    common.record_audit(current_user, "student.archive", "students", str(student_id), None)
    return archived
