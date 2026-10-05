"""Phase 7.13 — Super Admin institution-management service.

Business logic for the platform-scoped institution boundary.

Authorization model
-------------------
Every function here is reached ONLY through an API route that declares
``Depends(require_super_admin)``. The service therefore never re-derives
platform authority from a request body, query string or URL value: the acting
``actor_user_id`` is the ``user_id`` that ``require_super_admin`` resolved from
the verified JWT's application user, and the ``institution_id`` is only ever a
*target resource* read from the path. Neither is treated as a credential.

Lifecycle model
---------------
The platform lifecycle reuses the existing Phase 6.13 ``institutions.status``
vocabulary:

    create    -> ACTIVE (an explicitly platform-provisioned tenant)
    active    -> normal institutional functionality
    suspended -> normal institutional access restricted; ALL data retained
    activate  -> suspended back to ACTIVE

Suspension writes ONLY ``status``. The Phase 6.13 trigger derives
``is_active = false`` from it, which is what the existing public-chat,
sign-in, student-context and ``assert_tenant_context_active`` guards already
read — so restriction propagates through one existing source of truth and no
student, faculty, staff, admin, knowledge or document row is ever deleted.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import platform_institutions as platform_repo
from app.schemas.platform import (
    AdminAssignmentRequest,
    InstitutionAdminAssignmentResponse,
    InstitutionAdminView,
    InstitutionCreateRequest,
    InstitutionDetailResponse,
    InstitutionLifecycleResponse,
    InstitutionListResponse,
    InstitutionSummary,
    InstitutionUpdateRequest,
)

# Exact, user-safe wording of what suspension does and does not do. Surfaced in
# the API response so the confirmation dialog can never over- or under-promise.
SUSPENSION_MESSAGE = (
    "Institution suspended. Existing data was retained and no accounts were "
    "revoked. Institutional access is restricted until the institution is "
    "activated again."
)
ACTIVATION_MESSAGE = (
    "Institution activated. Normal institutional functionality is restored."
)


def _actor_user_id(actor: dict[str, Any]) -> str:
    """Extract the server-resolved actor id from the authorized principal."""
    user_id = actor.get("user_id")
    if not user_id:
        raise AppError(
            "You do not have permission to perform this action",
            status_code=403,
            code="FORBIDDEN",
        )
    return str(user_id)


def _require_institution(client, institution_id: UUID) -> dict[str, Any]:
    """Load one institution or fail with the standard 404 envelope."""
    row = platform_repo.get_platform_institution(client, institution_id)
    if row is None:
        raise AppError(
            "Institution not found",
            status_code=404,
            code="INSTITUTION_NOT_FOUND",
        )
    return row


def _supplied_fields(model: Any) -> dict[str, Any]:
    """Extract only the fields a client actually supplied.

    ``exclude_unset`` keeps an omitted field out of the write entirely, so a
    partial PATCH can never blank a value the operator did not touch.
    """
    return model.model_dump(exclude_unset=True)

def list_institutions() -> InstitutionListResponse:
    """Return the platform institution list with safe metadata only."""
    client = get_admin_client()
    rows = platform_repo.list_platform_institutions(client)
    admin_counts = platform_repo.list_institution_admin_counts(client)
    return InstitutionListResponse(
        institutions=[
            InstitutionSummary(
                id=UUID(str(row["institution_id"])),
                code=str(row["code"]),
                name=str(row["name"]),
                status=str(row.get("status", "pending")),
                is_active=bool(row.get("is_active", False)),
                admin_count=admin_counts.get(str(row["institution_id"]), 0),
            )
            for row in rows
        ]
    )


def get_institution(institution_id: UUID) -> InstitutionDetailResponse:
    """Return one institution's safe detail projection."""
    client = get_admin_client()
    row = _require_institution(client, institution_id)
    return _to_detail(client, row)


def create_institution(
    actor: dict[str, Any], payload: InstitutionCreateRequest
) -> InstitutionDetailResponse:
    """Create an institution in ACTIVE state and audit the action.

    Requires only name + code. The owning organization is the reserved platform
    parent created by the Phase 7.13 migration, so a Super Admin never has to
    pick a tenant parent and can never move an institution into an unrelated
    organization.
    """
    actor_user_id = _actor_user_id(actor)
    client = get_admin_client()

    if platform_repo.institution_code_taken(client, payload.code):
        raise AppError(
            "This institution code is already taken",
            status_code=409,
            code="INSTITUTION_CODE_TAKEN",
        )

    organization_id = platform_repo.get_platform_organization_id(client)
    if organization_id is None:
        # Fail closed rather than creating an institution without the parent the
        # Phase 6.13 FK requires.
        raise AppError(
            "Platform configuration is incomplete",
            status_code=500,
            code="PLATFORM_ORGANIZATION_NOT_CONFIGURED",
        )

    fields = _supplied_fields(payload)
    row = platform_repo.insert_platform_institution(
        client,
        organization_id=organization_id,
        name=payload.name,
        code=payload.code,
        fields=fields,
    )
    platform_repo.record_institution_audit(
        client,
        actor_user_id=actor_user_id,
        action=platform_repo.AUDIT_INSTITUTION_CREATED,
        institution_id=row["institution_id"],
        details={"code": payload.code, "status": "active"},
    )
    return _to_detail(client, row)


def update_institution(
    actor: dict[str, Any], institution_id: UUID, payload: InstitutionUpdateRequest
) -> InstitutionDetailResponse:
    """Update safe institution configuration and audit the change.

    The primary key, the owning organization and every tenant-owned record are
    structurally out of reach: only ``MUTABLE_INSTITUTION_FIELDS`` can be written.
    Lifecycle ``status`` is not part of the request schema at all.
    """
    actor_user_id = _actor_user_id(actor)
    client = get_admin_client()
    existing = _require_institution(client, institution_id)

    fields = _supplied_fields(payload)
    changed = sorted(key for key in fields if fields[key] != existing.get(key))
    if not changed:
        return _to_detail(client, existing)

    if "code" in changed and platform_repo.institution_code_taken(
        client, str(fields["code"]), excluding_institution_id=institution_id
    ):
        raise AppError(
            "This institution code is already taken",
            status_code=409,
            code="INSTITUTION_CODE_TAKEN",
        )

    row = platform_repo.update_platform_institution(client, institution_id, fields)
    if row is None:
        row = _require_institution(client, institution_id)
    platform_repo.record_institution_audit(
        client,
        actor_user_id=actor_user_id,
        action=platform_repo.AUDIT_INSTITUTION_UPDATED,
        institution_id=institution_id,
        details={"changed_fields": changed},
    )
    return _to_detail(client, row)
def suspend_institution(
    actor: dict[str, Any], institution_id: UUID
) -> InstitutionLifecycleResponse:
    """Suspend an institution, retaining all of its data.

    Writes only ``status = 'suspended'``. No student, faculty, staff, admin,
    knowledge or document row is deleted, and no account is revoked. Repeating
    the call is safe and is recorded as ``already_applied``.
    """
    return _set_lifecycle(
        actor,
        institution_id,
        target_status="suspended",
        action=platform_repo.AUDIT_INSTITUTION_SUSPENDED,
        message=SUSPENSION_MESSAGE,
    )


def activate_institution(
    actor: dict[str, Any], institution_id: UUID
) -> InstitutionLifecycleResponse:
    """Reactivate a suspended institution. Data was never removed, so restoring
    ``status = 'active'`` fully restores normal functionality."""
    return _set_lifecycle(
        actor,
        institution_id,
        target_status="active",
        action=platform_repo.AUDIT_INSTITUTION_ACTIVATED,
        message=ACTIVATION_MESSAGE,
    )


def assign_university_admin(
    actor: dict[str, Any],
    institution_id: UUID,
    payload: AdminAssignmentRequest,
) -> InstitutionAdminAssignmentResponse:
    """Assign an EXISTING account as University Admin of one institution.

    This is a controlled assignment, not provisioning: the account must already
    exist in ``public.users``, the payload carries no password, and the granted
    role is hard-coded to the institution-scoped ``admin`` role. It can never
    grant ``super_admin`` or a platform scope.
    """
    actor_user_id = _actor_user_id(actor)
    client = get_admin_client()
    institution = _require_institution(client, institution_id)

    user = platform_repo.get_user_by_email(client, payload.email)
    if user is None:
        raise AppError(
            "No account exists for this email address",
            status_code=404,
            code="USER_NOT_FOUND",
        )
    if user.get("status") != "active":
        raise AppError(
            "This account is not active",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )

    organization_id = institution.get("organization_id") or (
        platform_repo.get_platform_organization_id(client)
    )
    if organization_id is None:
        raise AppError(
            "Platform configuration is incomplete",
            status_code=500,
            code="PLATFORM_ORGANIZATION_NOT_CONFIGURED",
        )

    already_assigned = platform_repo.has_institution_admin_grant(
        client, user["id"], institution_id
    )
    if not already_assigned:
        platform_repo.assign_institution_admin(
            client,
            actor_user_id=actor_user_id,
            user_id=user["id"],
            institution_id=institution_id,
        )
    platform_repo.record_institution_audit(
        client,
        actor_user_id=actor_user_id,
        action=platform_repo.AUDIT_ADMIN_ASSIGNED,
        institution_id=institution_id,
        target_user_id=user["id"],
        result=(
            platform_repo.AUDIT_RESULT_ALREADY_APPLIED
            if already_assigned
            else platform_repo.AUDIT_RESULT_SUCCESS
        ),
    )
    return InstitutionAdminAssignmentResponse(
        institution_id=institution_id,
        assigned=not already_assigned,
        already_assigned=already_assigned,
        admin=InstitutionAdminView(
            user_id=UUID(str(user["id"])),
            email=str(user["email"]),
            institution_id=institution_id,
        ),
    )


def _set_lifecycle(
    actor: dict[str, Any],
    institution_id: UUID,
    *,
    target_status: str,
    action: str,
    message: str,
) -> InstitutionLifecycleResponse:
    """Shared suspend/activate transition with idempotent auditing."""
    actor_user_id = _actor_user_id(actor)
    client = get_admin_client()
    existing = _require_institution(client, institution_id)

    if str(existing.get("status")) == target_status:
        platform_repo.record_institution_audit(
            client,
            actor_user_id=actor_user_id,
            action=action,
            institution_id=institution_id,
            result=platform_repo.AUDIT_RESULT_ALREADY_APPLIED,
            details={"status": target_status},
        )
        return InstitutionLifecycleResponse(
            id=institution_id,
            code=str(existing["code"]),
            name=str(existing["name"]),
            status=target_status,
            is_active=bool(existing.get("is_active", False)),
            already_applied=True,
            message=message,
        )

    updated = platform_repo.set_institution_status(client, institution_id, target_status)
    if updated is None:
        updated = _require_institution(client, institution_id)
    platform_repo.record_institution_audit(
        client,
        actor_user_id=actor_user_id,
        action=action,
        institution_id=institution_id,
        details={"status": target_status},
    )
    return InstitutionLifecycleResponse(
        id=institution_id,
        code=str(updated.get("code", existing["code"])),
        name=str(updated.get("name", existing["name"])),
        status=target_status,
        is_active=bool(updated.get("is_active", target_status == "active")),
        already_applied=False,
        message=message,
    )


def _to_detail(client, row: dict[str, Any]) -> InstitutionDetailResponse:
    """Project a raw institution row into the safe detail response."""
    institution_id = UUID(str(row["institution_id"]))
    return InstitutionDetailResponse(
        id=institution_id,
        code=str(row["code"]),
        name=str(row["name"]),
        display_name=row.get("display_name"),
        status=str(row.get("status", "pending")),
        is_active=bool(row.get("is_active", False)),
        logo_url=row.get("logo_url"),
        primary_color=row.get("primary_color"),
        secondary_color=row.get("secondary_color"),
        welcome_message=row.get("welcome_message"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        admin_count=platform_repo.count_institution_admins(client, institution_id),
    )
