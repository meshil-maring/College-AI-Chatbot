"""Public, token-authorized student account setup."""

from fastapi import APIRouter, Request

from app.schemas.invitations.student_onboarding import (
    StudentInvitationCompleteRequest,
    StudentInvitationCompleteResponse,
    StudentInvitationInspectRequest,
    StudentInvitationPublicView,
)
from app.services.auth.auth_security import enforce_auth_rate_limit
from app.services.invitations import student_onboarding_acceptance

router = APIRouter(prefix="/student-onboarding", tags=["student-onboarding"])


@router.post("/inspect", response_model=StudentInvitationPublicView)
def inspect_student_invitation(
    body: StudentInvitationInspectRequest,
    request: Request,
) -> StudentInvitationPublicView:
    enforce_auth_rate_limit("registration", request)
    return student_onboarding_acceptance.inspect(body.token)


@router.post("/complete", response_model=StudentInvitationCompleteResponse)
def complete_student_invitation(
    body: StudentInvitationCompleteRequest,
    request: Request,
) -> StudentInvitationCompleteResponse:
    enforce_auth_rate_limit("password", request)
    return student_onboarding_acceptance.complete(body.token, body.password)
