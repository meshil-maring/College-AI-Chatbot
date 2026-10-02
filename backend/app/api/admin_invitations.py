"""Phase 7.14 — Public University Admin invitation boundary.

These two routes are reached by the INVITED PERSON, not by a Super Admin, and
they are therefore the only unauthenticated routes in the platform namespace.
They are authorized by POSSESSION of a one-time, expiring invitation token —
the same "bearer capability" shape the existing password-recovery flow uses —
and by nothing else.

What this boundary deliberately does NOT do:

* accept a role, a scope, a permission set or an institution id. Those are
  resolved entirely server-side from the invitation row, so a tampered body
  cannot redirect an invitation to another tenant or another privilege level;
* accept an authenticated session, because at this point the person has no
  account yet — the whole purpose of the flow is to create one securely;
* return anything about the platform beyond the single invitation's own
  institution name and expiry.

Password handling: the invited person sets their OWN password here, and it is
forwarded straight to Supabase Auth (GoTrue). No password is ever stored in this
application's database, compared here, written to an audit record, or returned in
any response.
Email delivery and verification
------------------------------
Phase 7.15 added an email-delivery boundary behind this API. Neither route
exposes anything about it: the acceptance page learns the invited address and
the SERVER's verification state from the inspection call, and nothing here can
influence which address an account is created with.

Rate limiting
-------------
Both routes are unauthenticated, so both are charged against per-peer budgets
before any work happens. The peer address is the DIRECT ASGI client address —
``X-Forwarded-For`` is deliberately ignored, exactly as in Phase 7.8, because
this repository has no trusted-proxy configuration.
"""

from fastapi import APIRouter, Request, status

from app.schemas.admin_invitations import (
    AdminInvitationAcceptRequest,
    AdminInvitationAcceptanceResponse,
    AdminInvitationPublicView,
)
from app.services import platform_admin_invitations as service

router = APIRouter(prefix="/admin-invitations", tags=["admin-invitations"])

# Base64url tokens are variable length by design; this bound only rejects
# absurd input before it reaches the hashing/lookup step.
MAX_TOKEN_LENGTH = 256


def _peer(http_request: Request) -> str:
    """Return the direct peer address for abuse-control bucketing."""
    client = http_request.client
    return client.host if client is not None else "unknown"


@router.get(
    "/{token}",
    response_model=AdminInvitationPublicView,
    summary="Inspect a University Admin invitation (token holder)",
)
def inspect_admin_invitation(token: str, request: Request) -> AdminInvitationPublicView:
    """Show what an invitation link grants, before accepting it.

    Returns only the status, the institution it is bound to, the invitee email,
    the expiry and the server-established verification state. It never returns
    a token hash, a user record, audit data or any other institution's
    information. An unknown or malformed token gets the same generic 400, so
    this route cannot be used to enumerate tokens.

    Rate limited per peer address (60 requests / 300 s by default); exceeding
    the budget returns a safe 429 that discloses no counter state.
    """
    return service.inspect_invitation(token, peer=_peer(request))


@router.post(
    "/{token}/accept",
    response_model=AdminInvitationAcceptanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Accept a University Admin invitation and set up the account",
)
def accept_admin_invitation(
    token: str,
    body: AdminInvitationAcceptRequest,
    request: Request,
) -> AdminInvitationAcceptanceResponse:
    """Consume the invitation and provision the institution-scoped admin.

    The server validates the token, verifies expiry and status, resolves the
    institution FROM THE INVITATION, creates the Auth account through the
    existing GoTrue signup path with THAT SAME server-derived address, atomically
    consumes the token, grants the fixed institution-scoped ``admin`` role and
    audits the result.

    The request body carries no email field at all, so the invited address
    cannot be swapped during acceptance. The invitation is one-time: a second
    acceptance with the same token fails, even if the two requests race.

    Rate limited per token (5 / 300 s) and per peer address (20 / 300 s) by
    default, which bounds automated password/registration attempts and token
    replay without making legitimate acceptance unreliable.
    """
    return service.accept_invitation(token, body, peer=_peer(request))