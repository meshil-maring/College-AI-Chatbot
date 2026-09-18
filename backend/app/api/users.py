"""Phase 6.13.5 — User registration API (students, faculty, staff).

Public, unauthenticated endpoint: users register under an existing ACTIVE
institution. The registration type determines which fields are required and
which role the user will eventually receive upon approval.

Flow implemented:

    POST /api/v1/users/register
      -> validate UserRegistrationRequest (extra="forbid")
      -> resolve institution by PUBLIC code (must be ACTIVE)
      -> validate institution-scoped identity fields
      -> create Supabase Auth account (existing mechanism)
      -> create public.users link row
      -> for students: create students profile (approval_status='pending')
      -> for faculty/staff: create membership request (pending, NO role)
      -> 201 UserRegistrationResponse (no password, no token)

Security invariants (inherited from existing Phase 6.3 / 6.13 schemas):

* ``UserRegistrationRequest`` uses ``extra="forbid"`` — clients can never
  inject ``role``, ``scope_type``, ``scope_id`` or any authorization field.
* ``registration_type`` is a Literal restricted to ``student | faculty | staff``
  — "admin" is unrepresentable and rejected with 422.
* NO role is assigned at registration time. For students, the existing Phase 6.4
  approval workflow will grant the "student" role. For faculty/staff, the
  institution admin approves the membership request and grants the role
  server-side (existing Phase 6.13.4 pattern).
* All registrations start in PENDING state — no unrestricted protected access
  before approval.
* Institution must be ACTIVE — pending/rejected/inactive institutions cannot
  accept registrations.
* Passwords go ONLY to Supabase Auth (GoTrue); never stored, hashed, or echoed.
* Approval workflow NOT implemented here — handled by existing architecture.

CUSTOMER: This endpoint replaces the need for separate student/faculty/staff
registration endpoints. All three user types register through this single
unified endpoint.
"""

from fastapi import APIRouter

from app.schemas.users import (
    UserRegistrationRequest,
    UserRegistrationResponse,
)
from app.services.user_registration import register_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    status_code=201,
    response_model=UserRegistrationResponse,
    summary="Register a student, faculty, or staff member",
)
def register_user_endpoint(
    body: UserRegistrationRequest,
) -> UserRegistrationResponse:
    """Register a student, faculty, or staff member under an active institution.

    Public endpoint. The request schema is ``extra="forbid"`` so clients cannot
    inject role / scope / status fields. The service resolves the institution
    from the public code, validates identity fields, creates the auth account
    and user record, and creates the appropriate pending profile/request.
    """
    return register_user(body)