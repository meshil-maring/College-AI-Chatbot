"""Phase 7.14 — University Admin invitation repository.

Data access only: every function takes an already-created Supabase ``Client`` as
its first argument and contains NO authorization logic, matching the established
``app/repositories`` convention. Authorization for the *creation* endpoints lives
exclusively in ``require_super_admin``; the *acceptance* endpoint is authorized
by possession of a valid, unexpired, unconsumed invitation token.

Token model
-----------
The raw token exists only in the process that generated it and only inside the
single invitation-creation HTTP response. This module stores and compares a
SHA-256 digest (``token_hash``); the raw value is never written to the database,
never written to the audit ledger, and never logged. Because the token is 384
bits of ``secrets`` entropy, the digest cannot be brute-forced, and because the
lookup is by digest the database never sees the credential itself.

Single-use enforcement
----------------------
``claim_invitation`` performs a CONDITIONAL update
``... WHERE status = 'invited' AND expires_at > now()``. Two concurrent
acceptance requests for the same token therefore produce exactly one winner:
Postgres takes a row lock and the loser's ``RETURNING`` set is empty. Combined
with the Phase 7.14 migration's terminal-state trigger (a consumed invitation
can never return to ``invited``) this makes replay structurally impossible
rather than a matter of application timing.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

# Raw token entropy in bytes -> 384 bits -> 64 URL-safe base64 characters.
# Long enough that guessing is infeasible, short enough to paste into a URL.
TOKEN_BYTES = 48

# The invited role is fixed. It is NOT read from any request body, query
# parameter or client-controlled field, so an invitation can never be replayed
# into a different privilege level.
INVITED_ROLE = "admin"

STATUS_INVITED = "invited"
STATUS_ACCEPTED = "accepted"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"

TERMINAL_STATUSES = frozenset({STATUS_ACCEPTED, STATUS_CANCELLED, STATUS_EXPIRED})

# Columns the platform UI may see. ``token_hash`` is deliberately ABSENT: no
# read projection used by the API can therefore ever include it.
#
# Phase 7.15 adds the delivery/verification bookkeeping columns to this
# projection so the roster can show delivery state. They are status metadata
# only: no token material, no provider credential and no message body.
INVITATION_VIEW_COLUMNS = (
    "invitation_id, institution_id, email, role_name, status, expires_at, "
    "accepted_at, cancelled_at, accepted_user_id, created_by, created_at, "
    "updated_at, email_verified_at, email_delivery_status, email_delivery_at, "
    "email_delivery_attempts, resend_count, last_sent_at"
)

# ---------------------------------------------------------------------------
# Phase 7.15 delivery / verification vocabulary.
#
# These are NOT lifecycle states. The invitation lifecycle stays exactly as
# Phase 7.14 defined it (invited -> accepted | cancelled | expired) so the
# existing terminal-state trigger remains the single authority; delivery and
# verification are orthogonal bookkeeping about the SAME row.
# ---------------------------------------------------------------------------
DELIVERY_PENDING = "pending"
DELIVERY_SENT = "sent"
DELIVERY_FAILED = "failed"

DELIVERY_STATUSES = frozenset({DELIVERY_PENDING, DELIVERY_SENT, DELIVERY_FAILED})

# Bounded so a client can never request an unbounded sweep page.
SWEEP_PAGE_MAX = 200


def generate_invitation_token() -> str:
    """Return a fresh, cryptographically random, URL-safe raw token.

    ``secrets`` is the OS CSPRNG (the same primitive the project's existing
    join-code generation already uses). The value is returned to the caller ONCE
    and is never persisted.
    """
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_invitation_token(raw_token: str) -> str:
    """Return the lowercase SHA-256 hex digest stored as ``token_hash``.

    SHA-256 over a 384-bit random token is safe here precisely because the input
    has no dictionary structure: there is nothing to attack with rainbow tables,
    and the digest cannot be inverted to a usable token.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return [row for row in data if row]
    return [data] if data else []


def get_invitation_by_token_hash(
    client: Client, token_hash: str
) -> dict[str, Any] | None:
    """Resolve a presented token digest to its invitation row, or None.

    A miss is indistinguishable from a miss for any other token: the lookup is a
    single digest equality match, so an attacker cannot distinguish "no such
    token" from "token of a different shape" and no table name or existence
    detail is ever surfaced to the caller.
    """
    response = (
        client.table("platform_admin_invitations")
        .select(INVITATION_VIEW_COLUMNS)
        .eq("token_hash", token_hash)
        .maybe_single()
        .execute()
    )
    return response.data if response is not None and response.data else None


def get_invitation_by_id(
    client: Client, invitation_id: UUID | str
) -> dict[str, Any] | None:
    """Resolve one invitation by its own id (roster/cancellation lookups)."""
    response = (
        client.table("platform_admin_invitations")
        .select(INVITATION_VIEW_COLUMNS)
        .eq("invitation_id", str(invitation_id))
        .maybe_single()
        .execute()
    )
    return response.data if response is not None and response.data else None


def find_pending_invitation(
    client: Client, *, institution_id: UUID | str, email: str
) -> dict[str, Any] | None:
    """Return an outstanding (not yet terminal) invitation for one invitee.

    Used to make duplicate invitations idempotent at the service layer. The
    database UNIQUE constraint is on ``token_hash`` only, so this read is what
    keeps a single email from accumulating several live invitations.
    """
    response = (
        client.table("platform_admin_invitations")
        .select(INVITATION_VIEW_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("email", email.strip().lower())
        .eq("status", STATUS_INVITED)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = _rows(response)
    return rows[0] if rows else None


def list_invitations(
    client: Client, institution_id: UUID | str
) -> list[dict[str, Any]]:
    """Return every invitation for one institution, newest first (roster)."""
    response = (
        client.table("platform_admin_invitations")
        .select(INVITATION_VIEW_COLUMNS)
        .eq("institution_id", str(institution_id))
        .order("created_at", desc=True)
        .execute()
    )
    return _rows(response)


def cancel_invitation(client: Client, invitation_id: UUID | str) -> bool:
    """Cancel a still-pending invitation. Returns True when this call cancelled it.

    The update is CONDITIONAL on ``status = 'invited'``, so an invitation that
    was accepted or expired in the meantime is never overwritten — the cancel
    loses the race instead of destroying an audit-relevant transition.
    """
    now = datetime.now(timezone.utc).isoformat()
    response = (
        client.table("platform_admin_invitations")
        .update({"status": STATUS_CANCELLED, "cancelled_at": now})
        .eq("invitation_id", str(invitation_id))
        .eq("status", STATUS_INVITED)
        .execute()
    )
    return bool(_rows(response))


def expire_invitation(client: Client, invitation_id: UUID | str) -> bool:
    """Mark a pending invitation EXPIRED. Returns True when this call expired it.

    Used when acceptance observes an elapsed ``expires_at``. The transition is
    persisted (and separately audited) so the roster reflects reality instead of
    showing a permanently "invited" row.
    """
    response = (
        client.table("platform_admin_invitations")
        .update({"status": STATUS_EXPIRED})
        .eq("invitation_id", str(invitation_id))
        .eq("status", STATUS_INVITED)
        .execute()
    )
    return bool(_rows(response))


def claim_invitation(
    client: Client, invitation_id: UUID | str, *, accepted_user_id: UUID | str
) -> dict[str, Any] | None:
    """Atomically consume an invitation, or return None when it was not claimable.

    The single conditional statement
    ``UPDATE ... WHERE invitation_id = ? AND status = 'invited' AND expires_at > now()``
    is the ONLY place an invitation becomes consumed. Because the same statement
    re-checks status and expiry, expiry is enforced by the database at the exact
    moment of consumption and not merely by an earlier read: a token that expires
    between the read and this write cannot be accepted.
    """
    now = datetime.now(timezone.utc).isoformat()
    response = (
        client.table("platform_admin_invitations")
        .update(
            {
                "status": STATUS_ACCEPTED,
                "accepted_at": now,
                "accepted_user_id": str(accepted_user_id),
            }
        )
        .eq("invitation_id", str(invitation_id))
        .eq("status", STATUS_INVITED)
        .gt("expires_at", now)
        .execute()
    )
    rows = _rows(response)
    return rows[0] if rows else None
def insert_invitation(
    client: Client,
    *,
    institution_id: UUID | str,
    email: str,
    token_hash: str,
    expires_at: datetime,
    created_by: UUID | str,
) -> dict[str, Any]:
    """Insert one INVITED invitation and return the stored row.

    ``role_name`` is written by the server constant, never by a caller. The
    supplied ``token_hash`` is the only credential-derived value that ever
    reaches the database.
    """
    response = (
        client.table("platform_admin_invitations")
        .insert(
            {
                "institution_id": str(institution_id),
                "email": email.strip().lower(),
                "token_hash": token_hash,
                "role_name": INVITED_ROLE,
                "status": STATUS_INVITED,
                "expires_at": expires_at.isoformat(),
                "created_by": str(created_by),
            }
        )
        .execute()
    )
    rows = _rows(response)
    if not rows or not rows[0].get("invitation_id"):
        raise RuntimeError("platform_admin_invitations insert returned no row")
    return rows[0]


def rotate_invitation_token(
    client: Client,
    invitation_id: UUID | str,
    *,
    token_hash: str,
    expires_at: datetime,
) -> dict[str, Any] | None:
    """Supersede an invitation's token in place, or return None if not pending.

    This is the whole of the resend strategy, and it is deliberately a SINGLE
    conditional statement:

        UPDATE ... SET token_hash = <new>, expires_at = <new>
        WHERE invitation_id = ? AND status = 'invited'

    Because the old digest is overwritten rather than inserted alongside it,
    the previous URL stops resolving at the database level the instant the
    statement commits. There is therefore never more than one usable
    invitation URL per invitation row, and no "which token is current?"
    bookkeeping can ever drift.

    The update is conditional on ``status = 'invited'``, so a resend can never
    revive an accepted, cancelled or expired invitation. The Phase 7.14
    lifecycle trigger still guards the status transition; the Phase 7.15
    migration additionally permits this one field pair to change while the row
    is pending, and continues to forbid every other identity field.
    """
    response = (
        client.table("platform_admin_invitations")
        .update(
            {
                "token_hash": token_hash,
                "expires_at": expires_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("invitation_id", str(invitation_id))
        .eq("status", STATUS_INVITED)
        .execute()
    )
    rows = _rows(response)
    return rows[0] if rows else None


def record_email_delivery(
    client: Client,
    invitation_id: UUID | str,
    *,
    status: str,
) -> dict[str, Any] | None:
    """Persist the outcome of one delivery attempt (sent or failed).

    This is the minimal "delivery record" the Phase 7.15 brief calls for: it
    keeps just enough state for a controlled retry and for the roster to be
    honest about whether the invitee was ever actually reached. It is
    deliberately NOT a general outbox or messaging platform — it stores no
    message body, no subject, no recipient list and no provider credential.
    """
    if status not in DELIVERY_STATUSES:
        raise ValueError("unsupported email delivery status")
    now = datetime.now(timezone.utc)
    response = (
        client.table("platform_admin_invitations")
        .update(
            {
                "email_delivery_status": status,
                "email_delivery_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        )
        .eq("invitation_id", str(invitation_id))
        .execute()
    )
    rows = _rows(response)
    return rows[0] if rows else None


def increment_delivery_attempt(
    client: Client, invitation_id: UUID | str, *, sent: bool
) -> dict[str, Any] | None:
    """Count one delivery attempt and, when it succeeded, stamp ``last_sent_at``.

    Attempt counting is what makes delivery behaviour observable after the
    fact, and it lives on the invitation row so it survives a process restart
    (the in-process rate limiter deliberately does not).

    The counter is a read-modify-write rather than a database-side
    ``col + 1`` expression, so it is only ever advisory: concurrent sends can
    undercount, which is acceptable for an observability counter and is never
    used as a security decision. The security decisions (token rotation,
    claim, expiry) all remain single conditional statements.
    """
    current = get_invitation_by_id(client, invitation_id)
    attempts = int((current or {}).get("email_delivery_attempts") or 0) + 1
    now = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "email_delivery_attempts": attempts,
        "updated_at": now,
    }
    if sent:
        payload["last_sent_at"] = now
    response = (
        client.table("platform_admin_invitations")
        .update(payload)
        .eq("invitation_id", str(invitation_id))
        .execute()
    )
    rows = _rows(response)
    return rows[0] if rows else None


def increment_resend_count(
    client: Client, invitation_id: UUID | str
) -> dict[str, Any] | None:
    """Count one resend against the invitation.

    Advisory only (see :func:`increment_delivery_attempt`): the actual
    protection against resend abuse is the multi-scope in-process limiter plus
    the fact that a resend INVALIDATES the previous token rather than issuing an
    additional one. This counter exists so an operator reviewing the roster can
    see that a link was reissued several times.
    """
    current = get_invitation_by_id(client, invitation_id)
    count = int((current or {}).get("resend_count") or 0) + 1
    response = (
        client.table("platform_admin_invitations")
        .update(
            {"resend_count": count, "updated_at": datetime.now(timezone.utc).isoformat()}
        )
        .eq("invitation_id", str(invitation_id))
        .execute()
    )
    rows = _rows(response)
    return rows[0] if rows else None


def mark_email_verified(client: Client, invitation_id: UUID | str) -> bool:
    """Record that the invited email address was verified server-side.

    Verification is ESTABLISHED BY THE SERVER, never asserted by the browser:
    this function is only called after acceptance proved that the Auth account
    it created carries exactly the invitation's email address. It is therefore
    monotonic — once verified, always verified — and it returns True only when
    this call performed the transition.

    Only ``email_verified_at`` changes here: the invitation's own lifecycle
    status is untouched, so an invitation that has not been accepted can never
    look verified.
    """
    now = datetime.now(timezone.utc).isoformat()
    response = (
        client.table("platform_admin_invitations")
        .update({"email_verified_at": now})
        .eq("invitation_id", str(invitation_id))
        .is_("email_verified_at", "null")
        .execute()
    )
    return bool(_rows(response))


def list_expiring_pending_invitations(
    client: Client, *, limit: int = SWEEP_PAGE_MAX
) -> list[dict[str, Any]]:
    """Return pending invitations whose ``expires_at`` has elapsed.

    This is only ever a CLEANUP query. The acceptance transaction remains
    authoritative: ``claim_invitation`` re-checks ``expires_at > now()`` in the
    same conditional statement that consumes the token, so an invitation the
    sweep has not reached yet is still refused at acceptance time.
    """
    now = datetime.now(timezone.utc).isoformat()
    response = (
        client.table("platform_admin_invitations")
        .select(INVITATION_VIEW_COLUMNS)
        .eq("status", STATUS_INVITED)
        .lte("expires_at", now)
        .order("expires_at")
        .limit(max(1, min(int(limit), SWEEP_PAGE_MAX)))
        .execute()
    )
    return _rows(response)