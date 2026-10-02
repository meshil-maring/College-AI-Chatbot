"""Phase 7.15 — abuse controls for the public University Admin invitation routes.

The primitive is REUSED from Phase 7.8 (``SlidingWindowRateLimiter`` in
``app.services.public_abuse_controls``) rather than a second, unrelated rate
limiter: same dependency-free, thread-safe, process-local sliding window, same
"direct ASGI peer address only, never X-Forwarded-For" trust posture.

The BUDGETS are deliberately separate from the public-chat budgets, because
invitation traffic has different characteristics:

* Public chat is high-volume and many-anonymous-user; one message per request.
* The invitation boundary is low-volume and high-value: a single leaked or
  guessed token IS the authorization. Acceptance is therefore budgeted per
  TOKEN as well as per IP, so one token cannot be brute-forced, and resend is
  budgeted per INVITATION, per INSTITUTION, per ACTOR and per IP, so one
  operator cannot mail-bomb an institution or an invitee.

Selected values (all configurable; defaults shown) over a 300-second window:

    inspect  per IP            60
    accept   per token          5
    accept   per IP            20
    resend   per invitation     3
    resend   per institution   10
    resend   per actor         20
    resend   per IP             5

A legitimate invitee inspects the link once or twice and accepts once, so five
acceptances per token is generous while still making automated attempts on a
single token impractical. A 429 body exposes neither counter values nor any
other internal limiter state.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.core.errors import AppError
from app.services.public_abuse_controls import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)

# A dedicated limiter instance: invitation counters must never share a bucket
# with public-chat counters, and vice versa.
invitation_rate_limiter = SlidingWindowRateLimiter()

RATE_LIMITED_CODE = "INVITATION_RATE_LIMITED"
RATE_LIMITED_MESSAGE = (
    "Too many invitation requests. Please wait a moment and try again."
)


def _client_identity(peer: str | None) -> str:
    """Normalize the direct ASGI peer address.

    ``X-Forwarded-For`` / ``Forwarded`` are deliberately ignored: this
    repository has no trusted-proxy configuration, and honouring a
    client-supplied header would turn every per-IP limit into a no-op.
    """
    value = (peer or "").strip()
    return value or "unknown"


def _enforce(scope: str, rules: list[tuple[str, str, int]]) -> None:
    """Charge one request across every supplied scope atomically."""
    if not settings.invitation_rate_limit_enabled:
        return
    retry_after = invitation_rate_limiter.check(
        rules, settings.invitation_rate_limit_window_seconds
    )
    if retry_after is None:
        return
    capped = min(max(1, retry_after), settings.invitation_retry_after_cap_seconds)
    logger.warning("event=admin_invitation_rate_limited scope=%s status=429", scope)
    raise AppError(
        RATE_LIMITED_MESSAGE,
        status_code=429,
        code=RATE_LIMITED_CODE,
        headers={"Retry-After": str(capped)},
    )


def enforce_inspect_rate_limit(peer: str | None) -> None:
    """Limit token INSPECTION.

    Inspection is the enumerable surface: it is unauthenticated and its
    response differs for a live token versus an unknown one, so it gets the
    most generous budget of the three while still bounding automated
    enumeration.
    """
    _enforce(
        "inspect",
        [
            (
                "inspect-ip",
                _client_identity(peer),
                settings.invitation_inspect_ip_limit_requests,
            )
        ],
    )


def enforce_accept_rate_limit(token_fingerprint: str, peer: str | None) -> None:
    """Limit ACCEPTANCE on one token and from one peer address.

    ``token_fingerprint`` is the invitation's stored SHA-256 digest, never the
    raw token: the limiter therefore keys on a value that is already persisted
    server-side, so no usable credential is ever held in process memory as a
    rate-limit key.
    """
    _enforce(
        "accept",
        [
            (
                "accept-token",
                token_fingerprint or "unknown",
                settings.invitation_accept_token_limit_requests,
            ),
            (
                "accept-ip",
                _client_identity(peer),
                settings.invitation_accept_ip_limit_requests,
            ),
        ],
    )


def enforce_resend_rate_limit(
    *,
    invitation_id: str,
    institution_id: str,
    actor_user_id: str,
    peer: str | None,
) -> None:
    """Limit RESEND across invitation, institution, actor and peer.

    Resend mints a fresh credential and sends a real email, so it is the most
    abusable operation in the flow: a caller who could resend freely could
    both mail-bomb an invitee and keep several live tokens in circulation.
    The per-invitation budget is what bounds how many live tokens exist.
    """
    _enforce(
        "resend",
        [
            (
                "resend-invitation",
                str(invitation_id),
                settings.invitation_resend_invitation_limit_requests,
            ),
            (
                "resend-institution",
                str(institution_id),
                settings.invitation_resend_institution_limit_requests,
            ),
            (
                "resend-actor",
                str(actor_user_id),
                settings.invitation_resend_actor_limit_requests,
            ),
            (
                "resend-ip",
                _client_identity(peer),
                settings.invitation_resend_ip_limit_requests,
            ),
        ],
    )


def reset_invitation_abuse_state() -> None:
    """Test hook; production code never resets enforcement state."""
    invitation_rate_limiter.reset()