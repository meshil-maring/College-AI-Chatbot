"""Public student registration API (Phase 6.3).

Self-service endpoint: no authentication is required. A prospective student
submits a registration for a specific institution; the backend validates the
institution + identity fields, creates the Supabase Auth account through the
existing mechanism, creates the public.users link, and creates a students
profile that ALWAYS starts with ``approval_status='pending'``.

Security: the request schema is ``extra="forbid"``, so client-supplied
``role`` / ``approval_status`` / institution-creation keys are rejected with
422 before any service call. Approval (pending -> approved) is exclusively
Phase 6.4 and is never reachable from this endpoint.
"""

from fastapi import APIRouter

from app.services.student_registration import (
    RegistrationResponse,
    StudentRegistrationRequest,
    register_student,
)

router = APIRouter(prefix="/registration", tags=["registration"])


@router.post("", status_code=201, response_model=RegistrationResponse)
def register_student_endpoint(
    body: StudentRegistrationRequest,
) -> RegistrationResponse:
    """Submit a student registration request for a specific institution.

    Public / self-service. Accepts only the identity fields defined on
    ``StudentRegistrationRequest``; any extra field (role, approval_status,
    institution creation keys, ...) is rejected with 422. The created student
    always has ``approval_status='pending'``.
    """
    return register_student(body)