"""Phase 6.13 — Organization, institution, and staff/faculty registration.

Registration flows (all server-side; no client-controlled privileges):

    1. register_organization
       payload -> validate org code + admin email
               -> Supabase Auth account (existing mechanism)
               -> public.users row
               -> organizations row (status 'pending')
               -> user_roles: role 'admin', scope (organization, org_id)
       The submitting user becomes the initial ORGANIZATION ADMIN.

    2. register_institution
       payload -> resolve organization by PUBLIC code (+ join code when issued)
               -> Supabase Auth account + public.users row
               -> institutions row (status 'pending'; is_active derived false)
               -> user_roles: role 'admin', scope (institution, inst_id)
               -> institution_join_requests row (status 'pending')
       The organization admin approves the join request to activate it.

    3. register_staff_or_faculty
       payload -> resolve institution by code (must be ACTIVE)
               -> Supabase Auth account + public.users row
               -> institution_membership_requests row (pending; NO role)
       The role is granted ONLY during admin approval, server-side.

Decisions:

    * decide_organization  (platform admin): pending -> active | rejected
    * decide_join_request  (org admin):      pending -> approved | rejected
    * decide_membership    (institution/org admin): pending -> approved | rejected
        approved  -> user_roles write (requested_role, institution scope)
        rejected  -> no role

Failure handling reuses the locked Phase 6.3 compensation primitives
(``_create_auth_account`` / ``_create_public_user`` / ``_try_delete_*``) —
Supabase Auth (GoTrue) cannot join a PostgREST transaction, so partial writes
are compensated best-effort. Passwords go ONLY to Supabase Auth.
"""

from __future__ import annotations

import hmac
import secrets
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import tenancy as tenancy_repo
from app.schemas.tenancy import (
    ApprovalDecisionRequest,
    DecisionResponse,
    InstitutionRegistrationRequest,
    InstitutionRegistrationResponse,
    OrganizationRegistrationRequest,
    OrganizationResponse,
    StaffFacultyRegistrationRequest,
    StaffFacultyRegistrationResponse,
)
from app.services.authorization import (
    INSTITUTION,
    ORGANIZATION,
    assert_can_decide_join_request,
    assert_can_manage_institution,
    resolve_authorization_context,
)
from app.services.student_registration import (
    _create_auth_account,
    _create_public_user,
    _try_delete_auth_user,
    _try_delete_user_row,
)

PENDING = "pending"
ACTIVE = "active"
REJECTED = "rejected"

# Length of the organization-issued institution join code (crypto-random,
# presented alongside the public organization code at institution registration).
JOIN_CODE_LENGTH = 12


def _normalize_code(value: str) -> str:
    code = (value or "").strip().upper()
    if not code:
        raise AppError(
            "Code must not be blank",
            status_code=422,
            code="VALIDATION_ERROR",
        )
    return code


def _verify_join_code(organization: dict, supplied: str | None) -> None:
    """Constant-time join-code verification.

    'Typing an organization name (or code)' is never sufficient when the
    organization has issued a join code: the request must also present the
    organization's server-issued code, compared in constant time.
    """
    required = organization.get("join_code")
    if not required:
        return
    if supplied is None or not hmac.compare_digest(
        str(supplied).strip().encode(), str(required).strip().encode()
    ):
        raise AppError(
            "Join code verification failed for this organization",
            status_code=403,
            code="INVALID_JOIN_CODE",
        )


def _assert_institution_active(institution: dict) -> None:
    """Only ACTIVE institutions accept staff/faculty (or any) onboarding."""
    if institution.get("status") != ACTIVE or not institution.get("is_active", False):
        raise AppError(
            "This institution is not currently accepting registrations",
            status_code=403,
            code="INSTITUTION_NOT_ACCEPTING_REGISTRATIONS",
        )


def _grant_role(
    db,
    *,
    user_id: str,
    role_name: str,
    scope_type: str,
    scope_id: str | None,
    scope_organization_id: str | None,
) -> dict:
    """Server-side role grant: user_roles write with Phase 6.13 scope columns."""
    role = tenancy_repo.get_role_by_name(db, role_name)
    if role is None:
        raise AppError(
            f"Role '{role_name}' is not configured",
            status_code=500,
            code="ROLE_NOT_CONFIGURED",
        )
    return tenancy_repo.assign_user_role_scope(
        db,
        user_id=user_id,
        role_id=role["role_id"],
        scope_type=scope_type,
        scope_id=scope_id,
        scope_organization_id=scope_organization_id,
    )


# ============================================================================
# 1. Organization registration
# ============================================================================


def register_organization(payload: OrganizationRegistrationRequest) -> OrganizationResponse:
    """Register an organization + its initial organization admin account."""
    code = _normalize_code(payload.organization_code)
    email = str(payload.admin_email).strip().lower()

    db = get_admin_client()

    if tenancy_repo.organization_code_exists(db, code):
        raise AppError(
            "This organization code is already taken",
            status_code=409,
            code="ORGANIZATION_CODE_TAKEN",
        )
    if tenancy_repo.get_user_by_email(db, email) is not None:
        raise AppError(
            "An account already exists for this email",
            status_code=409,
            code="EMAIL_ALREADY_REGISTERED",
        )

    # The join code is issued by the SERVER (never chosen by the client) and is
    # shared by the organization admin with its institutions.
    join_code = secrets.token_hex(JOIN_CODE_LENGTH // 2).upper()

    auth_user_id = _create_auth_account(email, payload.admin_password)

    user_id: str | None = None
    organization: dict | None = None
    try:
        user_id = _create_public_user(
            db,
            auth_user_id,
            email,
            payload.admin_first_name,
            payload.admin_last_name,
        )
        organization = tenancy_repo.insert_organization(
            db,
            name=payload.name,
            organization_code=code,
            official_email=str(payload.official_email).strip().lower(),
            contact_information=payload.contact_information,
            status=PENDING,
            join_code=join_code,
        )
        # Initial ORGANIZATION ADMIN identity: role 'admin', org scope. The
        # user_roles scope trigger/check guarantees the org binding is real.
        _grant_role(
            db,
            user_id=user_id,
            role_name="admin",
            scope_type=ORGANIZATION,
            scope_id=organization["organization_id"],
            scope_organization_id=organization["organization_id"],
        )
    except Exception as exc:
        if user_id is not None:
            _try_delete_user_row(db, user_id)
        _try_delete_auth_user(auth_user_id)
        if isinstance(exc, AppError):
            raise
        raise AppError(
            "Registration failed - could not create the organization record",
            status_code=500,
            code="REGISTRATION_FAILED",
        ) from exc

    return OrganizationResponse(
        message=(
            "Organization registered. The account is pending platform approval; "
            "institutions can only join once the organization is active."
        ),
        organization_id=UUID(str(organization["organization_id"])),
        organization_code=str(organization["organization_code"]),
        status=str(organization["status"]),
        admin_user_id=UUID(user_id),
        email=email,  # type: ignore[arg-type]
    )


# ============================================================================
# 2. Institution registration (join request to an organization)
# ============================================================================


def register_institution(
    payload: InstitutionRegistrationRequest,
) -> InstitutionRegistrationResponse:
    """Register an institution + initial admin + join request (pending).

    The organization relationship is verified with the PUBLIC organization
    code plus the organization-issued join code (constant-time compare) —
    never by "typing an organization name".
    """
    code = _normalize_code(payload.institution_code)
    org_code = _normalize_code(payload.organization_code)
    email = str(payload.admin_email).strip().lower()

    db = get_admin_client()

    organization = tenancy_repo.get_organization_by_code(db, org_code)
    if organization is None:
        raise AppError(
            "Organization not found",
            status_code=404,
            code="ORGANIZATION_NOT_FOUND",
        )
    if organization.get("status") != ACTIVE:
        raise AppError(
            "This organization is not currently accepting institution requests",
            status_code=403,
            code="ORGANIZATION_NOT_ACCEPTING_REQUESTS",
        )
    _verify_join_code(organization, payload.join_code)

    if tenancy_repo.institution_code_exists(db, code):
        raise AppError(
            "This institution code is already taken",
            status_code=409,
            code="INSTITUTION_CODE_TAKEN",
        )
    if tenancy_repo.get_user_by_email(db, email) is not None:
        raise AppError(
            "An account already exists for this email",
            status_code=409,
            code="EMAIL_ALREADY_REGISTERED",
        )

    auth_user_id = _create_auth_account(email, payload.admin_password)

    user_id: str | None = None
    institution: dict | None = None
    try:
        user_id = _create_public_user(
            db,
            auth_user_id,
            email,
            payload.admin_first_name,
            payload.admin_last_name,
        )
        institution = tenancy_repo.insert_institution(
            db,
            organization_id=organization["organization_id"],
            name=payload.name,
            code=code,
            email=str(payload.official_email).strip().lower(),
            address=payload.location,
        )
        # Initial INSTITUTION ADMIN identity: role 'admin' scoped to THIS
        # (still pending) institution. Access stays fail-closed because every
        # guard checks the institution status, which is 'pending'.
        _grant_role(
            db,
            user_id=user_id,
            role_name="admin",
            scope_type=INSTITUTION,
            scope_id=institution["institution_id"],
            scope_organization_id=organization["organization_id"],
        )
        tenancy_repo.insert_join_request(
            db,
            organization_id=organization["organization_id"],
            institution_id=institution["institution_id"],
            requested_institution_code=code,
            requested_by_user_id=user_id,
        )
    except Exception as exc:
        if user_id is not None:
            _try_delete_user_row(db, user_id)
        _try_delete_auth_user(auth_user_id)
        if isinstance(exc, AppError):
            raise
        raise AppError(
            "Registration failed - could not create the institution record",
            status_code=500,
            code="REGISTRATION_FAILED",
        ) from exc

    return InstitutionRegistrationResponse(
        message=(
            "Institution registered. The join request is pending approval by "
            "the organization admin."
        ),
        institution_id=UUID(str(institution["institution_id"])),
        institution_code=str(institution["code"]),
        organization_id=UUID(str(organization["organization_id"])),
        status=str(institution["status"]),
        admin_user_id=UUID(user_id),
        email=email,  # type: ignore[arg-type]
    )

# ============================================================================
# 3. Staff / faculty registration (pending; role granted ONLY at approval)
# ============================================================================


def register_staff_or_faculty(
    payload: StaffFacultyRegistrationRequest,
) -> StaffFacultyRegistrationResponse:
    """Register a staff/faculty onboarding request (pending; NO role granted)."""
    code = _normalize_code(payload.institution_code)
    email = str(payload.email).strip().lower()

    db = get_admin_client()

    institution = tenancy_repo.get_institution_by_code(db, code)
    if institution is None:
        raise AppError(
            "Institution not found",
            status_code=404,
            code="INSTITUTION_NOT_FOUND",
        )
    _assert_institution_active(institution)
    if tenancy_repo.get_user_by_email(db, email) is not None:
        raise AppError(
            "An account already exists for this email",
            status_code=409,
            code="EMAIL_ALREADY_REGISTERED",
        )

    auth_user_id = _create_auth_account(email, payload.password)

    user_id: str | None = None
    try:
        user_id = _create_public_user(
            db,
            auth_user_id,
            email,
            payload.first_name,
            payload.last_name,
        )
        request_row = tenancy_repo.insert_membership_request(
            db,
            institution_id=institution["institution_id"],
            organization_id=institution["organization_id"],
            user_id=user_id,
            requested_role=payload.requested_role,
            official_email=email,
            full_name=f"{payload.first_name.strip()} {payload.last_name.strip()}".strip(),
            designation=payload.designation,
            department=payload.department,
        )
    except Exception as exc:
        if user_id is not None:
            _try_delete_user_row(db, user_id)
        _try_delete_auth_user(auth_user_id)
        if isinstance(exc, AppError):
            raise
        raise AppError(
            "Registration failed - could not create the onboarding request",
            status_code=500,
            code="REGISTRATION_FAILED",
        ) from exc

    return StaffFacultyRegistrationResponse(
        message=(
            "Registration submitted. Your account is pending approval by the "
            "institution admin."
        ),
        request_id=UUID(str(request_row["request_id"])),
        institution_id=UUID(str(institution["institution_id"])),
        requested_role=payload.requested_role,
        email=email,  # type: ignore[arg-type]
    )


# ============================================================================
# Approval / rejection decisions (server-side role writes only)
# ============================================================================



def decide_organization(
    current_user: dict[str, Any],
    authorization_context: dict[str, Any],
    organization_id: str,
    decision: ApprovalDecisionRequest,
) -> DecisionResponse:
    """Platform admin activates or rejects a pending organization."""
    assert_can_manage_organization(
        current_user,
        authorization_context,
        organization_id,
    )
    db = get_admin_client()
    org = tenancy_repo.get_organization_by_id(db, UUID(organization_id))
    if org is None:
        raise AppError(
            "Organization not found",
            status_code=404,
            code="ORGANIZATION_NOT_FOUND",
        )
    if org.get("status") != PENDING:
        raise AppError(
            "Only pending organizations can be decided right now",
            status_code=422,
            code="ORGANIZATION_NOT_PENDING",
        )
    tenancy_repo.update_organization_status(db, str(org["organization_id"]), decision.decision)
    tenancy_repo.update_join_requests_for_organization(
        db,
        org["organization_id"],
        decision.decision,
    )
    return DecisionResponse(
        message=(
            f"Organization status set to '{decision.decision}'. "
            "All pending join requests for this organization are decided accordingly."
        ),
        status=decision.decision,
    )


def decide_join_request(
    current_user: dict[str, Any],
    authorization_context: dict[str, Any],
    join_request_id: str,
    decision: ApprovalDecisionRequest,
) -> DecisionResponse:
    """Organization admin approves or rejects a pending institution join request."""
    db = get_admin_client()
    join_request = tenancy_repo.get_join_request_by_id(db, UUID(join_request_id))
    if join_request is None:
        raise AppError(
            "Join request not found",
            status_code=404,
            code="JOIN_REQUEST_NOT_FOUND",
        )
    assert_can_decide_join_request(authorization_context, join_request)
    if join_request.get("status") != PENDING:
        raise AppError(
            "This join request has already been decided",
            status_code=422,
            code="JOIN_REQUEST_NOT_PENDING",
        )
    tenancy_repo.update_join_request_status(db, str(join_request["request_id"]), decision.decision)
    if decision.decision == "approve":
        tenancy_repo.update_institution_status_for_join(
            db,
            str(join_request["institution_id"]),
            ACTIVE,
        )
    else:
        tenancy_repo.update_institution_status_for_join(
            db,
            str(join_request["institution_id"]),
            REJECTED,
        )
    return DecisionResponse(
        message=(
            "Join request decided. Institution status updated accordingly."
        ),
        status=decision.decision,
    )


def decide_membership_request(
    current_user: dict[str, Any],
    authorization_context: dict[str, Any],
    request_id: str,
    decision: ApprovalDecisionRequest,
) -> DecisionResponse:
    """Institution admin (or org admin, or platform admin) approves/rejects a
    staff/faculty onboarding request."""
    db = get_admin_client()
    req = tenancy_repo.get_membership_request_by_id(db, UUID(request_id))
    if req is None:
        raise AppError(
            "Membership onboarding request not found",
            status_code=404,
            code="MEMBERSHIP_REQUEST_NOT_FOUND",
        )
    assert_can_manage_institution(
        current_user,
        authorization_context,
        req["institution_id"],
    )
    if req.get("status") != PENDING:
        raise AppError(
            "This onboarding request has already been decided",
            status_code=422,
            code="MEMBERSHIP_REQUEST_NOT_PENDING",
        )
    tenancy_repo.update_membership_request_status(
        db,
        str(req["request_id"]),
        decision.decision,
    )
    if decision.decision == "approve":
        tenancy_repo.assign_membership_role(
            db,
            user_id=req["user_id"],
            role_name=req["requested_role"],
            institution_id=req["institution_id"],
            organization_id=req["organization_id"],
        )
    else:
        tenancy_repo.remove_membership_on_reject(
            db,
            user_id=req["user_id"],
            institution_id=req["institution_id"],
        )
    return DecisionResponse(
        message=(
            "Membership request decided. "
            + ("The role was granted." if decision.decision == "approve" else "No role was granted.")
        ),
        status=decision.decision,
    )


def get_authorization_context_for_user(
    current_user: dict[str, Any],
) -> dict[str, Any]:
    """Public-facing convenience: resolve the phase 6.13 identity context."""
    return resolve_authorization_context(current_user)


