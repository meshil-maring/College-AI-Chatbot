"""Phase 7.14 — University Admin invitation, roster, revocation and audit contracts.

Security invariants baked into these schemas:

* ``extra="forbid"`` on every request model. The invitation-create payload is
  just an ``email``; ``role``, ``institution_id``, ``scope``, ``permissions``,
  ``status`` and ``expires_at`` are structurally unrepresentable, so a client can
  neither escalate the invited role nor extend the expiry nor redirect the
  invitation to another tenant. The institution is a validated PATH parameter
  resolved server-side, and the acting actor is always the server-resolved
  application user behind the verified JWT.
* The acceptance payload carries ONLY what Supabase Auth needs to create the
  account (a password and a display name). It contains no role, institution or
  scope field: ``invitation -> institution -> role`` is resolved entirely
  server-side from the invitation row, so a client cannot talk its way into a
  different tenant or a different role.
* Every response is an explicit projection. ``token_hash`` has no field anywhere
  in this module, so it is structurally impossible for the platform boundary to
  disclose a token digest.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Phase 7.14 lifecycle vocabulary. ``invited`` is the only non-terminal state.
InvitationStatus = Literal["invited", "accepted", "cancelled", "expired"]

# Platform audit vocabulary, mirroring the Phase 7.15 migration CHECK constraint.
PlatformAuditAction = Literal[
    "institution_created",
    "institution_updated",
    "institution_suspended",
    "institution_activated",
    "admin_assigned",
    "institution_admin_invited",
    "institution_admin_invitation_accepted",
    "institution_admin_invitation_expired",
    "institution_admin_invitation_cancelled",
    "institution_admin_revoked",
    # Phase 7.15 invitation delivery / email verification.
    "institution_admin_invitation_email_sent",
    "institution_admin_invitation_email_failed",
    "institution_admin_invitation_resent",
    "institution_admin_invitation_verified",
]

# Phase 7.15 delivery bookkeeping. Deliberately NOT lifecycle states: the
# invitation lifecycle stays ``invited``/``accepted``/``cancelled``/``expired``
# so the Phase 7.14 terminal-state trigger remains the single authority and no
# redundant lifecycle field is introduced.
EmailDeliveryStatus = Literal["pending", "sent", "failed"]

MAX_INVITE_EMAIL_LENGTH = 320
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 200
MAX_NAME_LENGTH = 200


def _normalized_email(v: EmailStr) -> str:
    """Lowercase and trim so invitation identity is deterministic and case-free."""
    return str(v).strip().lower()


class AdminInvitationCreateRequest(BaseModel):
    """Invite one person to be University Admin of the institution in the path.

    This is the ENTIRE payload. There is no ``role``, ``institution_id``,
    ``scope``, ``status`` or ``expires_at`` field: the granted role is a server
    constant (``admin``), the institution is the validated path parameter, and
    the expiry is a server-computed constant. No password and no Auth credential
    of any kind travels through this endpoint.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=MAX_INVITE_EMAIL_LENGTH)

    @field_validator("email")
    @classmethod
    def _email_normalized(cls, v: EmailStr) -> str:
        return _normalized_email(v)


class AdminInvitationAcceptRequest(BaseModel):
    """Secure account setup performed by the invited person.

    This is the ONLY endpoint in the platform surface that accepts a password,
    and it is reached by the invited administrator themselves — never by the
    Super Admin and never as part of institution management. The password is
    forwarded to Supabase Auth (GoTrue) and is never stored in this application's
    database, never compared here, never logged, and never echoed back.

    There is no ``role``/``institution_id``/``scope`` field: those come from the
    invitation row resolved server-side.
    """

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    first_name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    last_name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)

    @field_validator("password")
    @classmethod
    def _password_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def _name_blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None


class AdminInvitationView(BaseModel):
    """Safe projection of one invitation for the Super Admin roster.

    Contains the invitation id, the bound institution, the invitee's email, the
    lifecycle status, the timestamps needed to explain the state, and the
    Phase 7.15 delivery/verification bookkeeping. There is no ``token_hash``
    field and no raw token: a digest cannot be leaked through this projection
    even by accident.

    ``email_delivery_status``/``email_delivery_at``/``email_delivery_attempts``
    exist so a Super Admin can tell the difference between "the link exists"
    and "the email actually went out" — an invitation whose email failed is
    still a live, acceptable invitation, but a Super Admin needs to know to
    resend it. ``email_verified_at`` is set by the SERVER at acceptance, never
    by a client request.
    """

    invitation_id: UUID
    institution_id: UUID
    email: str
    status: InvitationStatus
    expires_at: str | None
    created_at: str | None
    accepted_at: str | None
    cancelled_at: str | None
    email_verified_at: str | None = None
    email_delivery_status: EmailDeliveryStatus = "pending"
    email_delivery_at: str | None = None
    email_delivery_attempts: int = 0
    resend_count: int = 0
    last_sent_at: str | None = None


class AdminInvitationCreatedResponse(BaseModel):
    """Result of creating one University Admin invitation.

    The raw ``invitation_token`` is returned exactly once, in this response
    only. It is never stored, never logged, never written to the audit ledger
    and never re-servable afterwards — if the operator loses it, the invitation
    is resent (which supersedes the token anyway). ``invitation_url`` is the
    same token shaped as a frontend route so the operator can copy a working
    link directly.

    Phase 7.15 adds ``email_delivery``: the real, explicit outcome of the
    delivery attempt. When it is ``failed``, ``invitation_token`` is still
    returned once so the operator has a fallback, but the response says
    plainly that the email did not go out and that the invitation should be
    resent — a delivery failure is never reported as success.
    """

    invitation: AdminInvitationView
    invitation_token: str
    invitation_url: str
    expires_in_hours: int
    email_delivery: EmailDeliveryOutcome


class AdminInvitationResendResponse(BaseModel):
    """Result of superseding a pending invitation's token and re-sending it.

    The NEW token is returned exactly once, by the same rule as creation: it
    is stored only as a SHA-256 digest, so this response is the only place it
    will ever exist. The previously issued URL is already dead by the time
    this response is produced.
    """

    invitation: AdminInvitationView
    invitation_token: str
    invitation_url: str
    expires_in_hours: int
    email_delivery: EmailDeliveryOutcome
    previous_token_invalidated: bool = True
    message: str


class AdminInvitationAcceptanceResponse(BaseModel):
    """Result of accepting an invitation and setting up the account.

    Tells the person what to do next and confirms the role/scope the SERVER
    granted. It deliberately contains no token, no session and no credential:
    the person still authenticates through the ordinary admin login route with
    the password they just chose.
    """

    institution_id: UUID
    institution_name: str
    email: str
    role: Literal["admin"]
    scope: Literal["institution"] = "institution"
    message: str


class EmailDeliveryOutcome(BaseModel):
    """What actually happened when the server tried to send the invitation.

    This is the Phase 7.15 answer to "do not silently report success if the
    delivery provider failed": the create and resend responses both carry this
    object, and ``status`` is the provider's real result, not an optimistic
    assumption.

    Only the provider's NAME and a bounded, non-sensitive status code are
    exposed. There is no provider API key, no message body, no SMTP response
    and no credential of any kind in this model — the API cannot leak the
    delivery credential because the model has no field to leak it into.
    """

    status: Literal["sent", "failed"]
    provider: str
    detail: str | None = None


class AdminInvitationPublicView(BaseModel):
    """What an unauthenticated invitation holder may see about their own token.

    Deliberately minimal: status, the institution name it is bound to, and the
    expiry. It exposes no user records, no invitation id, no audit data, no
    other tenant information and no token material.
    """

    status: InvitationStatus
    institution_name: str
    institution_code: str
    email: str
    expires_at: str | None
    email_verified: bool = False


class AdminRosterEntry(BaseModel):
    """One row of the institution's University Admin roster.

    An entry is EITHER an accepted admin (with its opaque user id and account
    status) OR a pending/terminal invitation (with no user id at all). Only
    platform-administration fields appear: email, lifecycle status and the
    expiry. Never a password, token, name record or student data.
    """

    email: str
    kind: Literal["admin", "invitation"]
    status: str
    user_id: UUID | None = None
    invitation_id: UUID | None = None
    institution_id: UUID
    expires_at: str | None = None
    email_delivery_status: EmailDeliveryStatus | None = None
    email_delivery_attempts: int | None = None
    email_verified: bool = False
    resend_count: int | None = None


class AdminRosterResponse(BaseModel):
    """The institution's University Admins: accepted accounts + invitations."""

    institution_id: UUID
    admins: list[AdminRosterEntry]
    pending_invitations: list[AdminRosterEntry]
    admin_count: int


class AdminInvitationCancellationResponse(BaseModel):
    """Result of cancelling a pending invitation."""

    invitation_id: UUID
    institution_id: UUID
    status: Literal["cancelled"] = "cancelled"
    already_applied: bool
    message: str


class AdminRevocationResponse(BaseModel):
    """Result of revoking an institution admin.

    States explicitly that only the institution-scoped ``admin`` grant was
    removed and that the person's account and any other role they hold were
    preserved, so the confirmation can never over-promise.
    """

    institution_id: UUID
    user_id: UUID
    revoked: bool
    already_revoked: bool
    message: str


class PlatformAuditEntry(BaseModel):
    """One read-only platform audit record.

    ``actor_email`` and ``institution_name`` are resolved server-side so the
    operator can see WHO acted and WHERE, without exposing any other tenant's
    data or the operator's own credentials. ``details`` is the bounded,
    non-sensitive jsonb summary the server wrote.
    """

    audit_id: UUID
    actor_user_id: UUID | None
    actor_email: str | None
    action: PlatformAuditAction
    institution_id: UUID
    institution_name: str | None
    target_user_id: UUID | None
    result: str
    details: dict[str, object]
    performed_at: str | None


class PlatformAuditListResponse(BaseModel):
    """Paginated, read-only platform audit page."""

    entries: list[PlatformAuditEntry]
    total: int
    limit: int
    offset: int


class AdminInvitationExpiry(BaseModel):
    """Server-owned invitation lifetime configuration (no client influence)."""

    expires_at: datetime
    expires_in_hours: int


class AdminInvitationExpirySweepResult(BaseModel):
    """Result of one run of the invitation expiry cleanup.

    ``expired`` counts rows this run actually transitioned; ``already_terminal``
    counts rows that were already accepted/cancelled/expired and were therefore
    left completely untouched. That split is what makes the operation's
    idempotency visible: running the sweep twice reports zero transitions the
    second time and changes nothing.
    """

    scanned: int
    expired: int
    already_terminal: int
