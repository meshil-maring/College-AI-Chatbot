"""Phase 6.13.3 — Institution registration / join request API.

Public, unauthenticated endpoint: a new institution submits a registration
request to join an EXISTING organization, and the submitting user becomes the
initial INSTITUTION ADMIN — server-side, with the existing Supabase Auth
mechanism and the Phase 6.13 scope model.

Flow implemented (reuses the Phase 6.13.1 tenancy service unchanged):

    POST /api/v1/institutions/register
      -> validate (InstitutionRegistrationRequest, extra="forbid")
      -> resolve organization by PUBLIC code (case-insensitive; must be ACTIVE)
      -> verify the organization-issued join code when one exists
         (constant-time compare; never client-chosen)
      -> uniqueness pre-checks (institution code, admin email)
      -> Supabase Auth account (existing GoTrue signup — password ONLY to GoTrue)
      -> public.users link row
      -> institutions row (status='pending', is_active=False trigger-derived)
      -> user_roles row (role 'admin', scope institution/inst_id/org_id)
      -> institution_join_requests row (status='pending')
      -> 201 InstitutionRegistrationResponse (no password, no token)

Security invariants (inherited from the existing schemas and services):

* ``InstitutionRegistrationRequest`` uses ``extra="forbid"`` — clients can
  never inject ``role``, ``scope_type``, ``scope_id`` or any authorization
  field. The role and scope are assigned ONLY by the service, and the scope is
  bound to the SERVER-RESOLVED organization (the client cannot override the
  organization id).
* The institution stays ``pending`` and the join request stays ``pending``:
  no institution-scoped access is usable before an organization admin approves
  the join request (Phase 6.13.4). Every authorization guard checks the
  institution status, which is 'pending' — access fails closed.
* The password goes ONLY to Supabase Auth (GoTrue); it is never stored,
  hashed, or echoed by the application.
* Approval / activation workflow is explicitly Phase 6.13.4 — not here.
"""

from fastapi import APIRouter, Depends
from uuid import UUID

from app.core.security import get_current_user
from app.schemas.tenancy import (
    ApprovalDecisionRequest,
    DecisionResponse,
    InstitutionRegistrationRequest,
    InstitutionRegistrationResponse,
)
from app.services.tenancy import (
    decide_join_request,
    get_authorization_context_for_user,
    register_institution,
)

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.post(
    "/register",
    status_code=201,
    response_model=InstitutionRegistrationResponse,
    summary="Register an institution and request to join an existing organization",
    description="""Submit a new institution registration under an existing
    organization. The organization is resolved SERVER-SIDE from its public
    ``organization_code`` (case-insensitive) plus its organization-issued
    ``join_code`` when one exists — the client cannot override the resolved
    organization id. The submitting user becomes the initial institution
    administrator with ``role=admin`` and ``scope=institution``. The
    institution starts in ``pending`` status with a pending join request and
    gains access only when an organization administrator approves the join
    request.

    Public / self-service — no authentication required.
    """,
)
def register_institution_endpoint(
    body: InstitutionRegistrationRequest,
) -> InstitutionRegistrationResponse:
    """Register an institution + create its initial institution admin.

    Public endpoint. The request schema is ``extra="forbid"`` so clients
    cannot inject role / scope / status fields. The service resolves the
    organization from the public code, assigns the ``admin`` role with
    ``institution`` scope server-side, and records the pending join request.
    """
    return register_institution(body)


@router.post(
    "/join-requests/{join_request_id}/decision",
    status_code=200,
    response_model=DecisionResponse,
    summary="Approve or reject an institution join request (organization admin)",
    description="""Approve or reject a PENDING institution join request. Only
    the OWNING organization's admin (``role=admin``,
    ``scope_type='organization'``, server-resolved scope) — or a platform
    admin — may decide; institution-scoped users (including the requesting
    institution's own admin) can NEVER decide a join request, and one
    organization can never decide another organization's request (403
    ``ORGANIZATION_MISMATCH`` otherwise).

    Approval activates the institution (``status='active'``,
    ``is_active=true`` trigger-derived), granting its initial admin protected
    institution-scoped access. Rejection sets the join request and institution
    to ``rejected`` — the institution stays inaccessible. Repeated decisions
    are safe: only ``pending`` requests can be decided (422
    ``JOIN_REQUEST_NOT_PENDING`` otherwise).

    Authenticated endpoint — never public.
    """,
)
def decide_join_request_endpoint(
    join_request_id: UUID,
    body: ApprovalDecisionRequest,
    current_user: dict = Depends(get_current_user),
) -> DecisionResponse:
    """Organization-admin approve/reject of an institution join request.

    Thin delegation to the existing ``decide_join_request`` service: the
    authorization context is resolved SERVER-SIDE from the verified JWT, then
    the existing ``assert_can_decide_join_request`` guard and decision logic
    run unchanged. Tenant isolation is enforced entirely server-side.
    """
    authorization_context = get_authorization_context_for_user(current_user)
    return decide_join_request(
        current_user,
        authorization_context,
        str(join_request_id),
        body,
    )