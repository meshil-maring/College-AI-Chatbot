"""Phase 6.13.2 — Organization registration API.

Public, unauthenticated endpoint: a new organization submits its registration
and the submitting user becomes the initial ORGANIZATION ADMIN — server-side,
with the existing Supabase Auth mechanism and the Phase 6.13 scope model.

Security invariants (inherited from the existing schemas and services):

* ``OrganizationRegistrationRequest`` uses ``extra="forbid"`` — clients can
  never inject ``role``, ``scope_type``, ``scope_id`` or any authorization
  field. The role and scope are assigned ONLY by the service.
* The password goes ONLY to Supabase Auth (GoTrue); it is never stored,
  hashed, or echoed by the application.
* After registration the admin's JWT (obtained separately via login) resolves
  to ``role=admin``, ``scope_type=organization``, ``scope_id=<org.id>``.
* No institution is created automatically — institution onboarding is Phase
  6.13.3.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.tenancy import (
    ApprovalDecisionRequest,
    DecisionResponse,
    OrganizationRegistrationRequest,
    OrganizationResponse,
)
from app.services.tenancy import (
    decide_organization,
    get_authorization_context_for_user,
    register_organization,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post(
    "/register",
    status_code=201,
    response_model=OrganizationResponse,
    summary="Register an organization and its initial organization admin",
    description="""Create a new organization account. The submitting user becomes
    the initial organization administrator with ``role=admin`` and
    ``scope=organization``. The organization starts in ``pending`` status and
    must be approved by a platform administrator before it can accept
    institution join requests.

    Public / self-service — no authentication required.
    """,
)
def register_organization_endpoint(body: OrganizationRegistrationRequest) -> OrganizationResponse:
    """Register an organization + create its initial organization admin.

    Public endpoint. The request schema is ``extra="forbid"`` so clients
    cannot inject role / scope / status fields. The service assigns the
    ``admin`` role with ``organization`` scope server-side.
    """
    return register_organization(body)


@router.post(
    "/{organization_id}/decision",
    status_code=200,
    response_model=DecisionResponse,
    summary="Approve or reject a pending organization (platform authority only)",
    description="""Activate or reject a PENDING organization. This is a
    PLATFORM-level decision: the authenticated account must resolve to the
    existing ``admin`` role with ``scope_type='platform'`` (Phase 6.13 scope
    model). Organization admins can manage their own organization but can
    NEVER self-approve it — the platform review gate is enforced server-side
    by the service (403 otherwise).

    Repeated decisions are safe: only ``pending`` organizations can be decided
    (422 ``ORGANIZATION_NOT_PENDING`` otherwise). Approving the organization
    also approves its still-pending institution join requests (and activates
    those institutions); rejecting it rejects them (institutions become
    ``rejected`` and stay inaccessible).

    Authenticated endpoint — never public.
    """,
)
def decide_organization_endpoint(
    organization_id: UUID,
    body: ApprovalDecisionRequest,
    current_user: dict = Depends(get_current_user),
) -> DecisionResponse:
    """Platform-level approve/reject of a pending organization.

    Thin delegation to the existing ``decide_organization`` service: the
    authorization context is resolved SERVER-SIDE from the verified JWT
    (never from a client-supplied claim), then the existing scope guards and
    decision logic run unchanged.
    """
    authorization_context = get_authorization_context_for_user(current_user)
    return decide_organization(
        current_user,
        authorization_context,
        str(organization_id),
        body,
    )
