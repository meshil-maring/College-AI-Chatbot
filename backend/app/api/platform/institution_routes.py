"""Platform institution routes."""

from uuid import UUID
from fastapi import Depends, status
from app.schemas.platform.platform import (
    AdminAssignmentRequest,
    InstitutionAdminAssignmentResponse,
    InstitutionCreateRequest,
    InstitutionDetailResponse,
    InstitutionLifecycleResponse,
    InstitutionListResponse,
    InstitutionUpdateRequest,
)
from app.services.platform import platform_institutions as service
from fastapi import APIRouter
from app.api.platform.dependencies import _SUPER_ADMIN

router = APIRouter(prefix="/platform")


@router.get("/me")
async def platform_me(current_user: dict = Depends(_SUPER_ADMIN)) -> dict[str, str]:
    """Return only the safe identity needed to prove platform authorization."""
    return {"role": "super_admin", "scope": "platform"}


@router.get(
    "/institutions",
    response_model=InstitutionListResponse,
    summary="List every institution on the platform (Super Admin)",
)
async def list_platform_institutions(
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionListResponse:
    """Return safe platform metadata for every institution.

    Exposes only id, code, name, lifecycle status, availability and the count
    of assigned admins. Never student information, academic records, documents,
    credentials or any other tenant-owned data.
    """
    return service.list_institutions()


@router.post(
    "/institutions",
    response_model=InstitutionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an institution (Super Admin)",
)
async def create_platform_institution(
    body: InstitutionCreateRequest,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionDetailResponse:
    """Create an institution in ACTIVE status.

    Only ``name`` and ``code`` are required; branding is optional. The code is
    normalized and validated server-side and must be unique. The institution is
    attached to the reserved platform organization, so the Super Admin never
    selects a tenant parent. The action is audited as ``institution_created``.
    """
    return service.create_institution(current_user, body)


@router.get(
    "/institutions/{institution_id}",
    response_model=InstitutionDetailResponse,
    summary="Read one institution's platform configuration (Super Admin)",
)
async def read_platform_institution(
    institution_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionDetailResponse:
    """Return one institution's safe detail projection."""
    return service.get_institution(institution_id)


@router.patch(
    "/institutions/{institution_id}",
    response_model=InstitutionDetailResponse,
    summary="Update an institution's configuration (Super Admin)",
)
async def update_platform_institution(
    institution_id: UUID,
    body: InstitutionUpdateRequest,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionDetailResponse:
    """Update name, routing code and optional branding/contact configuration.

    The primary key and the owning organization are structurally unchangeable, so
    this can never reassign an existing institution's students, knowledge or
    documents. Lifecycle status is intentionally NOT part of this payload: use
    the dedicated suspend/activate endpoints so each transition is separately
    confirmed and separately audited.
    """
    return service.update_institution(current_user, institution_id, body)


@router.post(
    "/institutions/{institution_id}/suspend",
    response_model=InstitutionLifecycleResponse,
    summary="Suspend an institution (Super Admin)",
)
async def suspend_platform_institution(
    institution_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionLifecycleResponse:
    """Restrict an institution's normal access while retaining all its data.

    No student, faculty, staff, admin, knowledge or document row is deleted and
    no account is revoked. Audited as ``institution_suspended``.
    """
    return service.suspend_institution(current_user, institution_id)


@router.post(
    "/institutions/{institution_id}/activate",
    response_model=InstitutionLifecycleResponse,
    summary="Approve/activate a pending or suspended institution (Super Admin)",
)
async def activate_platform_institution(
    institution_id: UUID,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionLifecycleResponse:
    """Approve a pending institution or restore a suspended institution.

    Pending self-registrations become usable only through this explicit,
    protected platform action. Because suspension never removed data,
    restoring active status also fully restores a suspended tenant. Audited as
    ``institution_activated``.
    """
    return service.activate_institution(current_user, institution_id)


@router.post(
    "/institutions/{institution_id}/admins",
    response_model=InstitutionAdminAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign an existing account as University Admin (Super Admin)",
)
async def assign_platform_institution_admin(
    institution_id: UUID,
    body: AdminAssignmentRequest,
    current_user: dict = Depends(_SUPER_ADMIN),
) -> InstitutionAdminAssignmentResponse:
    """Grant the institution-scoped ``admin`` role to an existing account.

    The account must already exist; this endpoint never provisions an Auth
    account and accepts no password. The granted role is fixed to
    institution-scoped ``admin``, so it can never confer ``super_admin`` or any
    platform scope. Audited as ``admin_assigned``.
    """
    return service.assign_university_admin(current_user, institution_id, body)
