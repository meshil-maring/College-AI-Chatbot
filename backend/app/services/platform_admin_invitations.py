"""Phase 7.14 — Super Admin University Admin lifecycle service.

This module owns the complete University Admin lifecycle:

    INVITED --> ACCEPTED --> ACTIVE --> REVOKED
           \\-> EXPIRED     \\-> CANCELLED

Authorization model
-------------------
Two DIFFERENT authorization contexts meet here, and they are deliberately kept
apart:

* Platform management (create / cancel / roster / revoke / audit) is reachable
  ONLY through API routes that declare ``Depends(require_super_admin)``. The
  acting ``actor_user_id`` is the application user the server resolved from the
  verified JWT; an ``institution_id`` in a path is a *target resource*, never an
  authorization credential.
* Invitation inspection/acceptance is authorized by POSSESSION of a valid,
  unexpired, unconsumed invitation token — the same "bearer capability" shape the
  existing password-recovery flows already use. It accepts no actor, no role and
  no institution from the client.

The invitation row is the SINGLE source of truth for ``institution -> role``.
Acceptance resolves that chain server-side; the request body is never consulted
for authorization, so an invitation can be used for exactly one institution and
exactly one role, namely the fixed institution-scoped ``admin``.

Password handling
-----------------
No password is ever accepted on the platform-management surface. On acceptance,
the invited person supplies their own password; it is forwarded straight to
Supabase Auth (GoTrue) through the EXISTING ``_create_auth_account`` primitive
and is never stored in this application's database, never logged and never
returned. The resulting role then resolves through the established chain
JWT -> get_current_user -> get_user_by_auth_id -> user_roles -> roles ->
institution -> resolve_primary_role.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import platform_admin_invitations as invite_repo
from app.repositories import platform_institutions as platform_repo
from app.schemas.admin_invitations import (
    AdminInvitationAcceptRequest,
    AdminInvitationAcceptanceResponse,
    AdminInvitationCancellationResponse,
    AdminInvitationCreateRequest,
    AdminInvitationCreatedResponse,
    AdminInvitationExpirySweepResult,
    AdminInvitationPublicView,
    AdminInvitationResendResponse,
    AdminInvitationView,
    AdminRevocationResponse,
    AdminRosterEntry,
    AdminRosterResponse,
    EmailDeliveryOutcome,
    PlatformAuditEntry,
    PlatformAuditListResponse,
)
from app.services import email_delivery
from app.services import invitation_abuse_controls as abuse
from app.services import student_registration as student_svc

logger = logging.getLogger(__name__)

# Default invitation lifetime: 24 hours. This is a SERVER constant — no client
# can supply or extend it, and acceptance re-checks ``expires_at`` inside the
# atomic claim statement so a token that elapses mid-request is still refused.
INVITATION_TTL_HOURS = 24

# Where an operator should send the invited person. A relative path, so no
# backend host assumption is baked into the response.
INVITATION_ACCEPT_ROUTE = "/admin-invite/{token}"

RESEND_MESSAGE = (
    "A new invitation link has been issued and emailed to the invited address. "
    "The previous link no longer works."
)
DELIVERY_FAILED_MESSAGE = (
    "The invitation was created, but the email could not be sent. Use Resend to "
    "issue a new link and try again."
)

CANCELLATION_MESSAGE = (
    "Invitation cancelled. The link can no longer be used and the invitation "
    "record was retained for the audit trail."
)
REVOCATION_MESSAGE = (
    "University Admin access revoked for this institution. The account itself "
    "and any other role it holds were preserved."
)
ACCEPTANCE_MESSAGE = (
    "Your University Admin account is ready. Sign in with the password you just "
    "created using the admin login page."
)
NOT_INSTITUTION_ADMIN_MESSAGE = (
    "This account does not hold a University Admin grant for this institution. "
    "Nothing was changed."
)
def _actor_user_id(actor: dict[str, Any]) -> str:
    """Extract the server-resolved actor id from the authorized principal."""
    user_id = actor.get("user_id")
    if not user_id:
        raise AppError(
            "You do not have permission to perform this action",
            status_code=403,
            code="FORBIDDEN",
        )
    return str(user_id)


def _require_institution(client, institution_id: UUID) -> dict[str, Any]:
    """Load one institution or fail with the standard 404 envelope."""
    row = platform_repo.get_platform_institution(client, institution_id)
    if row is None:
        raise AppError(
            "Institution not found",
            status_code=404,
            code="INSTITUTION_NOT_FOUND",
        )
    return row


def _require_active_institution(client, institution_id: UUID) -> dict[str, Any]:
    """Load one institution and refuse anything that is not fully ACTIVE.

    Inviting into, and accepting into, a suspended or pending institution would
    hand out tenant access the platform has explicitly restricted, so both paths
    fail closed here using the same Phase 6.13 status vocabulary.
    """
    institution = _require_institution(client, institution_id)
    if institution.get("status") != "active" or not institution.get("is_active", False):
        raise AppError(
            "This institution is not currently active",
            status_code=409,
            code="INSTITUTION_INACTIVE",
        )
    return institution


def _parse_instant(value: Any) -> datetime | None:
    """Parse a timestamptz column into an aware datetime, tolerating None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _expired(invitation: dict[str, Any]) -> bool:
    """True when the invitation's own expiry timestamp is in the past.

    This is a convenience check used only to produce the friendliest possible
    error BEFORE doing any work. It is NOT the security control: the authoritative
    expiry check is the ``expires_at > now()`` predicate inside the atomic claim
    statement, which cannot be raced.
    """
    expires_at = _parse_instant(invitation.get("expires_at"))
    return expires_at is not None and expires_at <= datetime.now(timezone.utc)


def _to_invitation_view(row: dict[str, Any]) -> AdminInvitationView:
    """Project a stored invitation row into its safe API representation.

    The raw token and the stored digest are both absent from the projection, so
    neither can appear in a response even by accident. The Phase 7.15 delivery
    counters are included because a Super Admin needs to distinguish "the link
    exists" from "the email actually went out".
    """
    return AdminInvitationView(
        invitation_id=UUID(str(row["invitation_id"])),
        institution_id=UUID(str(row["institution_id"])),
        email=str(row["email"]),
        status=str(row.get("status", invite_repo.STATUS_INVITED)),
        expires_at=row.get("expires_at"),
        created_at=row.get("created_at"),
        accepted_at=row.get("accepted_at"),
        cancelled_at=row.get("cancelled_at"),
        email_verified_at=row.get("email_verified_at"),
        email_delivery_status=str(
            row.get("email_delivery_status") or invite_repo.DELIVERY_PENDING
        ),
        email_delivery_at=row.get("email_delivery_at"),
        email_delivery_attempts=int(row.get("email_delivery_attempts") or 0),
        resend_count=int(row.get("resend_count") or 0),
        last_sent_at=row.get("last_sent_at"),
    )


def _delivery_outcome(result: email_delivery.EmailDeliveryResult) -> EmailDeliveryOutcome:
    """Convert a provider result into the safe API projection.

    ``detail`` is the provider's bounded status code (e.g.
    ``EMAIL_PROVIDER_NOT_CONFIGURED``), never a provider response body, a
    credential or a token.
    """
    return EmailDeliveryOutcome(
        status=result.status,
        provider=result.provider,
        detail=result.detail or None,
    )


def _send_and_record_invitation_email(
    client,
    *,
    invitation: dict[str, Any],
    institution_name: str,
    raw_token: str,
    expires_at: datetime,
    actor_user_id: str,
) -> EmailDeliveryOutcome:
    """Attempt delivery, then persist and audit the REAL outcome.

    This is the Phase 7.15 delivery boundary and the ordering the brief
    requires:

        invitation row committed  →  email attempted  →  result recorded + audited

    No database transaction is held open across the provider call: this
    repository's Supabase access pattern issues independent statements rather
    than wrapping a block in one long-lived transaction, so a slow provider
    cannot pin database resources. The trade-off is explicit and documented
    rather than hidden: if the process dies between the commit and the result
    write, the invitation row keeps ``email_delivery_status='pending'`` and the
    roster shows a pending delivery, which is honest and recoverable by a
    resend.

    Critically, NOTHING about authorization happens here. A failure grants no
    access, creates no account and does not consume the invitation — the
    invitation simply remains a live invitation whose email has not arrived.
    """
    result = email_delivery.deliver_invitation_email(
        email_delivery.get_email_provider(),
        to_email=str(invitation["email"]),
        institution_name=institution_name,
        raw_token=raw_token,
        expires_at=expires_at,
    )
    sent = result.status == email_delivery.DELIVERY_SENT
    try:
        invite_repo.record_email_delivery(
            client,
            invitation["invitation_id"],
            status=invite_repo.DELIVERY_SENT if sent else invite_repo.DELIVERY_FAILED,
        )
        invite_repo.increment_delivery_attempt(
            client, invitation["invitation_id"], sent=sent
        )
    except Exception:  # noqa: BLE001 - bookkeeping must not mask the result
        logger.warning("event=admin_invitation_delivery_record_failed")

    # Audit records the outcome; it never records the token or the provider key.
    platform_repo.record_institution_audit(
        client,
        actor_user_id=actor_user_id,
        action=(
            platform_repo.AUDIT_ADMIN_INVITATION_EMAIL_SENT
            if sent
            else platform_repo.AUDIT_ADMIN_INVITATION_EMAIL_FAILED
        ),
        institution_id=invitation["institution_id"],
        result=(
            platform_repo.AUDIT_RESULT_SUCCESS
            if sent
            else platform_repo.AUDIT_RESULT_FAILED
        ),
        target_user_id=None,
        details={
            "invitation_id": str(invitation["invitation_id"]),
            "provider": result.provider,
            "delivery_status": result.status,
        },
    )
    return _delivery_outcome(result)
def _resolve_live_invitation(client, raw_token: str) -> dict[str, Any]:
    """Resolve a presented token to its invitation, or raise a safe error.

    Hashes the token, performs a single digest lookup, then validates status and
    expiry server-side. An unknown token and a structurally invalid token produce
    the SAME generic 400, so this endpoint cannot be used to probe which tokens
    exist.
    """
    invalid = AppError(
        "This invitation link is not valid",
        status_code=400,
        code="INVITATION_INVALID",
    )
    if not raw_token or not (32 <= len(raw_token) <= 256):
        raise invalid

    invitation = invite_repo.get_invitation_by_token_hash(
        client, invite_repo.hash_invitation_token(raw_token)
    )
    if invitation is None:
        raise invalid

    status = str(invitation.get("status"))
    if status == invite_repo.STATUS_CANCELLED:
        raise AppError(
            "This invitation has been cancelled",
            status_code=410,
            code="INVITATION_CANCELLED",
        )
    if status == invite_repo.STATUS_ACCEPTED:
        raise AppError(
            "This invitation has already been used",
            status_code=410,
            code="INVITATION_ALREADY_ACCEPTED",
        )
    if status == invite_repo.STATUS_EXPIRED or _expired(invitation):
        if status == invite_repo.STATUS_INVITED:
            # Persist the transition so the roster and the audit trail reflect
            # the truth instead of showing a permanently "invited" row.
            invite_repo.expire_invitation(client, invitation["invitation_id"])
            platform_repo.record_institution_audit(
                client,
                actor_user_id=invitation["created_by"],
                action=platform_repo.AUDIT_ADMIN_INVITATION_EXPIRED,
                institution_id=invitation["institution_id"],
                details={"email": invitation.get("email")},
            )
        raise AppError(
            "This invitation has expired",
            status_code=410,
            code="INVITATION_EXPIRED",
        )
    return invitation


def create_invitation(
    actor: dict[str, Any],
    institution_id: UUID,
    payload: AdminInvitationCreateRequest,
) -> AdminInvitationCreatedResponse:
    """Issue a one-time, expiring University Admin invitation.

    The email is the ONLY client-supplied value. The role is the server constant
    ``admin``, the institution is the path resource, and the expiry is a server
    constant — so this endpoint cannot grant ``super_admin``, ``staff``,
    ``faculty`` or ``student``, cannot extend the lifetime, and cannot be pointed
    at another institution. No password and no Auth credential is involved.

    A duplicate outstanding invitation for the same email and institution is
    refused: no second live token is issued, so a mis-click cannot leave two
    usable links in circulation for the same person.
    """
    actor_user_id = _actor_user_id(actor)
    client = get_admin_client()
    institution = _require_active_institution(client, institution_id)

    email = payload.email
    existing = invite_repo.find_pending_invitation(
        client, institution_id=institution_id, email=email
    )
    if existing is not None and not _expired(existing):
        raise AppError(
            "An active invitation already exists for this email address",
            status_code=409,
            code="INVITATION_ALREADY_PENDING",
        )

    raw_token = invite_repo.generate_invitation_token()
    token_hash = invite_repo.hash_invitation_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITATION_TTL_HOURS)

    row = invite_repo.insert_invitation(
        client,
        institution_id=institution_id,
        email=email,
        token_hash=token_hash,
        expires_at=expires_at,
        created_by=actor_user_id,
    )
    platform_repo.record_institution_audit(
        client,
        actor_user_id=actor_user_id,
        action=platform_repo.AUDIT_ADMIN_INVITED,
        institution_id=institution_id,
        details={"email": email, "expires_at": row.get("expires_at")},
    )
    # Phase 7.15: the invitation row is committed FIRST, then the email is
    # attempted, then the real outcome is recorded. A delivery failure leaves a
    # perfectly valid invitation behind (recoverable by resending) and grants
    # nothing at all — no Auth account, no role, no consumed token.
    delivery = _send_and_record_invitation_email(
        client,
        invitation=row,
        institution_name=str(institution.get("name", "")),
        raw_token=raw_token,
        expires_at=expires_at,
        actor_user_id=actor_user_id,
    )
    # The raw token is returned HERE and nowhere else — it is not stored, not
    # logged, and not written to the audit ledger (whose details carry only the
    # email and the expiry).
    return AdminInvitationCreatedResponse(
        invitation=_to_invitation_view(row),
        invitation_token=raw_token,
        invitation_url=INVITATION_ACCEPT_ROUTE.format(token=raw_token),
        expires_in_hours=INVITATION_TTL_HOURS,
        email_delivery=delivery,
    )


def _rotated_source(
    rotated: dict[str, Any] | None, original: dict[str, Any]
) -> dict[str, Any]:
    """Return the rotated row, falling back to the already-read original.

    Repository stubs in tests may return a minimal row; the fallback keeps the
    resend path total without ever inventing an identity, because the fallback
    is the very row the server itself read a moment ago.
    """
    return rotated if rotated else original


def resend_invitation(
    actor: dict[str, Any],
    institution_id: UUID,
    invitation_id: UUID,
    *,
    peer: str | None = None,
) -> AdminInvitationResendResponse:
    """Supersede a pending invitation's token and email the new link.

    Strategy (deterministic, one live token at a time):

        existing invitation
            → generate a NEW cryptographically random token
            → OVERWRITE the stored digest + expiry in one conditional update
              (``WHERE status = 'invited'``) — the old URL is now dead
            → attempt delivery and record + audit the real outcome

    Why overwrite rather than insert a second row: a second row would leave the
    previous URL valid and would accumulate live tokens for one person. Here
    there is exactly one usable URL per invitation at every moment, so a leaked
    link is closed by a single resend with no residual access.

    Only a PENDING invitation can be resent. An accepted, cancelled or expired
    invitation is refused with 409 and left untouched — the Phase 7.14
    terminal-state trigger enforces the same rule in the database, so even a
    concurrent race cannot revive a consumed invitation.

    The institution binding is verified before anything is written, so an
    operator can never resend another tenant's invitation by guessing its id.
    """
    actor_user_id = _actor_user_id(actor)
    abuse.enforce_resend_rate_limit(
        invitation_id=str(invitation_id),
        institution_id=str(institution_id),
        actor_user_id=actor_user_id,
        peer=peer,
    )
    client = get_admin_client()
    institution = _require_institution(client, institution_id)

    invitation = invite_repo.get_invitation_by_id(client, invitation_id)
    if invitation is None or str(invitation["institution_id"]) != str(institution_id):
        raise AppError(
            "Invitation not found",
            status_code=404,
            code="INVITATION_NOT_FOUND",
        )

    status = str(invitation.get("status"))
    if status != invite_repo.STATUS_INVITED or _expired(invitation):
        # Accepted / cancelled / already expired. If it merely LOOKS pending but
        # has elapsed, persist and audit the expiry so the roster tells the
        # truth, exactly as the acceptance path does.
        if status == invite_repo.STATUS_INVITED:
            invite_repo.expire_invitation(client, invitation_id)
            platform_repo.record_institution_audit(
                client,
                actor_user_id=invitation["created_by"],
                action=platform_repo.AUDIT_ADMIN_INVITATION_EXPIRED,
                institution_id=institution_id,
                details={"email": invitation.get("email")},
            )
        raise AppError(
            "Only a pending invitation can be resent",
            status_code=409,
            code="INVITATION_NOT_RESENDABLE",
        )

    raw_token = invite_repo.generate_invitation_token()
    token_hash = invite_repo.hash_invitation_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITATION_TTL_HOURS)

    # The single point at which the old token stops working. If this returns
    # None the invitation stopped being pending in the meantime and nothing was
    # sent, so no live token exists that nobody knows about.
    rotated = invite_repo.rotate_invitation_token(
        client,
        invitation_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    if rotated is None:
        raise AppError(
            "Only a pending invitation can be resent",
            status_code=409,
            code="INVITATION_NOT_RESENDABLE",
        )

    try:
        invite_repo.increment_resend_count(client, invitation_id)
    except Exception:  # noqa: BLE001 - advisory counter only
        logger.warning("event=admin_invitation_resend_count_failed")

    platform_repo.record_institution_audit(
        client,
        actor_user_id=actor_user_id,
        action=platform_repo.AUDIT_ADMIN_INVITATION_RESENT,
        institution_id=institution_id,
        details={
            "invitation_id": str(invitation_id),
            "email": invitation.get("email"),
            "expires_at": expires_at.isoformat(),
        },
    )

    source = _rotated_source(rotated, invitation)
    delivery = _send_and_record_invitation_email(
        client,
        invitation=source,
        institution_name=str(institution.get("name", "")),
        raw_token=raw_token,
        expires_at=expires_at,
        actor_user_id=actor_user_id,
    )
    message = (
        RESEND_MESSAGE
        if delivery.status == email_delivery.DELIVERY_SENT
        else "A new invitation link was issued, but the email could not be sent. "
        "Try resending again."
    )
    return AdminInvitationResendResponse(
        invitation=_to_invitation_view(source),
        invitation_token=raw_token,
        invitation_url=INVITATION_ACCEPT_ROUTE.format(token=raw_token),
        expires_in_hours=INVITATION_TTL_HOURS,
        email_delivery=delivery,
        previous_token_invalidated=True,
        message=message,
    )


def inspect_invitation(
    raw_token: str, *, peer: str | None = None
) -> AdminInvitationPublicView:
    """Let the invitation holder see what their own link grants.

    Accepts an opaque token and returns ONLY the binding it carries: the
    institution it is for, the invitee email, the lifecycle status/expiry and
    the SERVER's verification state. There is no invitation id, no user record,
    no token hash, no audit data and no other institution's information in the
    response.

    ``email_verified`` is read from the invitation row the server itself just
    fetched. It is never accepted from the request, and it can only be true
    because acceptance proved the Auth account carries exactly the invited
    address — the browser cannot assert it.
    """
    abuse.enforce_inspect_rate_limit(peer)
    client = get_admin_client()
    invitation = _resolve_live_invitation(client, raw_token)
    institution = _require_institution(client, UUID(str(invitation["institution_id"])))
    return AdminInvitationPublicView(
        status=str(invitation.get("status", invite_repo.STATUS_INVITED)),
        institution_name=str(institution.get("name", "")),
        institution_code=str(institution.get("code", "")),
        email=str(invitation["email"]),
        expires_at=invitation.get("expires_at"),
        email_verified=bool(invitation.get("email_verified_at")),
    )
def accept_invitation(
    raw_token: str,
    payload: AdminInvitationAcceptRequest,
    *,
    peer: str | None = None,
) -> AdminInvitationAcceptanceResponse:
    """Consume an invitation and provision the institution-scoped University Admin.

    The order below is the security-relevant part:

    1. Charge the per-token / per-IP acceptance budget (Phase 7.15 abuse
       control) BEFORE any credential is touched, so automated attempts against
       one token are bounded.
    2. Resolve the token to its invitation row and validate status + expiry.
    3. Resolve the INSTITUTION from that row (never from the request) and
       require it to be ACTIVE, so a suspended tenant grants nothing.
    4. Derive the account email FROM THE INVITATION ROW. The request body has no
       email field at all (``extra="forbid"``), so the invited address cannot be
       swapped for an attacker's during acceptance.
    5. Create the Auth account through the EXISTING GoTrue signup primitive,
       using that server-derived address. The person chooses their own
       password; it is never stored, compared or logged by this application.
    6. Create the ``public.users`` link row.
    7. CLAIM the invitation with one atomic conditional update. This is the
       single-use gate: if it does not return a row, the invitation was already
       consumed (or expired) and the whole acceptance is refused and compensated.
    8. Grant the FIXED institution-scoped ``admin`` role via the existing
       ``assign_user_role_scope`` primitive, so the Phase 6.13 scope trigger
       keeps cross-organization grants structurally impossible.
    9. Record the server-established email verification, then write the audit
       records.

    Email ownership verification (Phase 7.15)
    -----------------------------------------
    The invitation email is BOUND to the acceptance at the point where the Auth
    account is created: ``Auth email = invitation.email``, established entirely
    server-side from the stored row. The email the invitation was DELIVERED to
    is therefore the only address the account can ever have. Verification is
    then recorded as a server-authoritative fact on the invitation row
    (``email_verified_at``) and audited; it is never a field the browser can
    set, because the acceptance schema has no such field and rejects extras.

    Because the role is granted only AFTER the claim and is a server constant,
    an accepted admin can never become ``super_admin`` and can never be scoped to
    an institution other than the one the invitation is bound to.
    """
    abuse.enforce_accept_rate_limit(
        invite_repo.hash_invitation_token(raw_token or ""), peer
    )
    client = get_admin_client()
    invitation = _resolve_live_invitation(client, raw_token)

    institution_id = UUID(str(invitation["institution_id"]))
    institution = _require_active_institution(client, institution_id)
    # The single source of truth for WHO this account belongs to. Taken from the
    # stored invitation, never from the request body.
    email = str(invitation["email"])

    # An account that already exists cannot be silently re-provisioned. The
    # operator is pointed at the existing Phase 7.13 assignment capability,
    # which is the supported path for granting a role to an existing account.
    if platform_repo.get_user_by_email(client, email) is not None:
        raise AppError(
            "An account already exists for this email address. Ask your "
            "platform administrator to assign your existing account instead.",
            status_code=409,
            code="ACCOUNT_ALREADY_EXISTS",
        )

    auth_user_id = student_svc._create_auth_account(email, payload.password)
    user_id: str | None = None
    try:
        user_id = student_svc._create_public_user(
            client,
            auth_user_id,
            email,
            payload.first_name or "University",
            payload.last_name or "Admin",
        )
        # The one-time gate. Losing this race consumes nothing and grants nothing.
        claimed = invite_repo.claim_invitation(
            client, invitation["invitation_id"], accepted_user_id=user_id
        )
        if claimed is None:
            raise AppError(
                "This invitation link is not valid",
                status_code=400,
                code="INVITATION_INVALID",
            )

        organization_id = institution.get("organization_id") or (
            platform_repo.get_platform_organization_id(client)
        )
        if organization_id is None:
            raise AppError(
                "Platform configuration is incomplete",
                status_code=500,
                code="PLATFORM_ORGANIZATION_NOT_CONFIGURED",
            )

        platform_repo.assign_institution_admin(
            client,
            user_id=user_id,
            institution_id=institution_id,
            organization_id=organization_id,
        )
        # Phase 7.15: record that the invited email address was verified. This
        # runs only AFTER the account exists AND the claim succeeded, and the
        # address compared here is the one the server passed to Auth — the
        # invitation's own. A mismatch is impossible by construction (there is
        # no client email field), but the equality is asserted explicitly so the
        # invariant is enforced rather than merely assumed.
        if email.strip().lower() != str(invitation["email"]).strip().lower():
            raise AppError(
                "This invitation link is not valid",
                status_code=400,
                code="INVITATION_EMAIL_MISMATCH",
            )
        invite_repo.mark_email_verified(client, invitation["invitation_id"])
        platform_repo.record_institution_audit(
            client,
            actor_user_id=user_id,
            action=platform_repo.AUDIT_ADMIN_INVITATION_VERIFIED,
            institution_id=institution_id,
            target_user_id=user_id,
            details={"email": email, "verified_by": "invitation_acceptance"},
        )
    except Exception as exc:  # noqa: BLE001 - compensated, then re-raised
        # Best-effort compensation, mirroring the established Phase 6.3 pattern.
        # The Auth account and the users row are removed so a failed acceptance
        # never leaves an orphaned identity behind. The invitation itself is NOT
        # resurrected (its terminal transition is permanent by design).
        if user_id is not None:
            student_svc._try_delete_user_row(client, user_id)
        student_svc._try_delete_auth_user(auth_user_id)
        if isinstance(exc, AppError):
            raise
        logger.warning("event=admin_invitation_acceptance_failed category=database")
        raise AppError(
            "Unable to complete the invitation at this time. Please contact "
            "your platform administrator.",
            status_code=500,
            code="INVITATION_ACCEPTANCE_FAILED",
        ) from exc

    platform_repo.record_institution_audit(
        client,
        actor_user_id=user_id,
        action=platform_repo.AUDIT_ADMIN_INVITATION_ACCEPTED,
        institution_id=institution_id,
        target_user_id=user_id,
        details={"email": email, "role": invite_repo.INVITED_ROLE},
    )
    return AdminInvitationAcceptanceResponse(
        institution_id=institution_id,
        institution_name=str(institution.get("name", "")),
        email=email,
        role="admin",
        message=ACCEPTANCE_MESSAGE,
    )
def cancel_invitation(
    actor: dict[str, Any], institution_id: UUID, invitation_id: UUID
) -> AdminInvitationCancellationResponse:
    """Cancel a still-pending invitation, making its token permanently unusable.

    The institution binding is verified BEFORE any mutation, so an operator can
    never cancel another tenant's invitation by guessing its id. The invitation
    row is NEVER deleted — only transitioned — so the audit trail and the
    already-written ``institution_admin_invited`` record both remain intact.
    """
    actor_user_id = _actor_user_id(actor)
    client = get_admin_client()
    _require_institution(client, institution_id)

    invitation = invite_repo.get_invitation_by_id(client, invitation_id)
    if invitation is None or str(invitation["institution_id"]) != str(institution_id):
        raise AppError(
            "Invitation not found",
            status_code=404,
            code="INVITATION_NOT_FOUND",
        )

    if invite_repo.cancel_invitation(client, invitation_id):
        platform_repo.record_institution_audit(
            client,
            actor_user_id=actor_user_id,
            action=platform_repo.AUDIT_ADMIN_INVITATION_CANCELLED,
            institution_id=institution_id,
            details={"email": invitation.get("email")},
        )
        already_applied = False
    else:
        # Accepted / expired / already cancelled: nothing to undo.
        already_applied = True

    return AdminInvitationCancellationResponse(
        invitation_id=invitation_id,
        institution_id=institution_id,
        already_applied=already_applied,
        message=CANCELLATION_MESSAGE,
    )


def get_admin_roster(institution_id: UUID) -> AdminRosterResponse:
    """Return an institution's University Admins and its pending invitations.

    Two sources are merged into one roster:

    * accepted admins — derived from the EXACT (admin, institution, this id)
      grant tuple, so a Super Admin or another institution's admin can never
      appear here;
    * invitations — every non-accepted invitation, shown with its real status.

    Only email, lifecycle status, opaque ids and the expiry are exposed. No
    password, token, name record, student data or unrelated user information is
    present in the response model at all.
    """
    client = get_admin_client()
    _require_institution(client, institution_id)

    user_ids = platform_repo.list_institution_admin_user_ids(client, institution_id)
    users = platform_repo.list_users_by_ids(client, user_ids)
    admins = [
        AdminRosterEntry(
            user_id=UUID(user_id),
            email=str(users.get(user_id, {}).get("email", "")),
            status=str(users.get(user_id, {}).get("status", "unknown")),
            kind="admin",
            institution_id=institution_id,
        )
        for user_id in user_ids
        if users.get(user_id)
    ]
    admins.sort(key=lambda entry: entry.email)

    pending = [
        AdminRosterEntry(
            invitation_id=UUID(str(row["invitation_id"])),
            email=str(row["email"]),
            status=str(row.get("status", invite_repo.STATUS_INVITED)),
            kind="invitation",
            institution_id=institution_id,
            expires_at=row.get("expires_at"),
            email_delivery_status=str(row.get("email_delivery_status") or "pending"),
            email_delivery_attempts=int(row.get("email_delivery_attempts") or 0),
            email_verified=bool(row.get("email_verified_at")),
            resend_count=int(row.get("resend_count") or 0),
        )
        for row in invite_repo.list_invitations(client, institution_id)
        if str(row.get("status")) != invite_repo.STATUS_ACCEPTED
    ]
    return AdminRosterResponse(
        institution_id=institution_id,
        admins=admins,
        pending_invitations=pending,
        admin_count=len(admins),
    )


def expire_pending_admin_invitations(
    *, limit: int = invite_repo.SWEEP_PAGE_MAX
) -> AdminInvitationExpirySweepResult:
    """Transition elapsed pending invitations to ``expired`` (Phase 7.15 sweep).

    What this IS: housekeeping. It finds rows where
    ``status = 'invited' AND expires_at <= now()`` and moves them to
    ``expired`` so the roster and the audit trail stop showing a permanently
    "invited" invitation that can no longer be used.

    What this is NOT: the security boundary. Expiry is enforced by
    ``claim_invitation``, whose single conditional statement re-checks
    ``expires_at > now()`` at the exact moment of consumption. An invitation
    the sweep has not reached — because it has never run, or runs hourly, or
    the process was down — is still refused at acceptance time and transitions
    to ``expired`` there instead. Nothing about security depends on this
    function running.

    Idempotency: the candidate query filters on ``status = 'invited'`` and the
    transition is itself conditional on ``status = 'invited'``, so a second run
    finds nothing to do and reports ``expired=0``. Accepted, cancelled and
    already-expired rows are never selected and never modified.

    Scheduling: this deployment runs one Uvicorn process with no worker or
    scheduler, so there is NO running background process here. The function is
    a reusable service call with a safe execution boundary (the Super Admin
    ``/platform/admin-invitations/expire-sweep`` route, plus direct invocation
    from local development or a test). Wiring it to cron, a queue worker or a
    platform scheduler is a DEPLOYMENT concern for a later phase and is not
    claimed here.

    Audit: each transition writes ``institution_admin_invitation_expired``. The
    actor is the invitation's original issuing Super Admin (``created_by``)
    rather than a fabricated service identity, because the audit table's
    ``actor_user_id`` is a non-nullable users FK and the sweep is attributable
    to the invitation that is expiring. No token, hash, password or credential
    is recorded.
    """
    client = get_admin_client()
    candidates = invite_repo.list_expiring_pending_invitations(client, limit=limit)
    expired = 0
    for invitation in candidates:
        invitation_id = invitation["invitation_id"]
        if not invite_repo.expire_invitation(client, invitation_id):
            # Lost a race (accepted or cancelled between the query and the
            # write). Nothing was changed and nothing is recorded.
            continue
        expired += 1
        try:
            platform_repo.record_institution_audit(
                client,
                actor_user_id=invitation["created_by"],
                action=platform_repo.AUDIT_ADMIN_INVITATION_EXPIRED,
                institution_id=invitation["institution_id"],
                details={
                    "email": invitation.get("email"),
                    "expired_by": "expiry_sweep",
                },
            )
        except Exception:  # noqa: BLE001 - one bad audit must not stop the sweep
            logger.warning("event=admin_invitation_expiry_audit_failed")

    logger.info(
        "event=admin_invitation_expiry_sweep scanned=%d expired=%d",
        len(candidates),
        expired,
    )
    return AdminInvitationExpirySweepResult(
        scanned=len(candidates),
        expired=expired,
        already_terminal=len(candidates) - expired,
    )


def revoke_admin(
    actor: dict[str, Any], institution_id: UUID, user_id: UUID
) -> AdminRevocationResponse:
    """Revoke one institution-scoped University Admin grant.

    Safety chain, verified in this exact order before anything is mutated:

        target user -> institution -> admin role -> institution scope

    * the institution must exist;
    * the user must hold the EXACT (admin, institution, this id) grant — a user
      who is only a Super Admin, only an admin elsewhere, or simply unrelated
      does not match and is refused;
    * an account that ALSO holds a platform ``super_admin`` grant is refused
      outright, so a Super Admin's platform authority can never be stripped by
      an operator who meant to remove a tenant grant.

    Only that single ``user_roles`` row is deleted. The Auth account, the
    ``public.users`` row and every other role the person holds are preserved, so
    a tenant admin who is also that tenant's faculty member loses only the admin
    grant. Because all tenant authorization re-reads ``user_roles`` per request,
    the revoked admin loses institution-admin access on their very next request.
    """
    actor_user_id = _actor_user_id(actor)
    client = get_admin_client()
    _require_institution(client, institution_id)

    grant = platform_repo.find_institution_admin_grant(
        client, user_id=user_id, institution_id=institution_id
    )
    if grant is None:
        # Distinguish "no such user" from "not an admin here" only to keep the
        # operator's error actionable; neither reveals anything cross-tenant,
        # because both paths require an already-authorized Super Admin.
        user = platform_repo.get_user_by_id(client, user_id)
        if user is None:
            raise AppError(
                "Account not found", status_code=404, code="USER_NOT_FOUND"
            )
        platform_repo.record_institution_audit(
            client,
            actor_user_id=actor_user_id,
            action=platform_repo.AUDIT_ADMIN_REVOKED,
            institution_id=institution_id,
            target_user_id=user_id,
            result=platform_repo.AUDIT_RESULT_ALREADY_APPLIED,
            details={"email": user.get("email")},
        )
        return AdminRevocationResponse(
            institution_id=institution_id,
            user_id=user_id,
            revoked=False,
            already_revoked=True,
            message=NOT_INSTITUTION_ADMIN_MESSAGE,
        )

    if platform_repo.has_platform_super_admin_grant(client, user_id):
        raise AppError(
            "This account also holds platform administrator authority and "
            "cannot be revoked as an institution admin.",
            status_code=409,
            code="PLATFORM_ROLE_PRESERVED",
        )

    removed = platform_repo.revoke_institution_admin_grant(
        client, user_id=user_id, institution_id=institution_id
    )
    user = platform_repo.get_user_by_id(client, user_id)
    platform_repo.record_institution_audit(
        client,
        actor_user_id=actor_user_id,
        action=platform_repo.AUDIT_ADMIN_REVOKED,
        institution_id=institution_id,
        target_user_id=user_id,
        result=(
            platform_repo.AUDIT_RESULT_SUCCESS
            if removed
            else platform_repo.AUDIT_RESULT_ALREADY_APPLIED
        ),
        details={"email": user.get("email") if user else None},
    )
    return AdminRevocationResponse(
        institution_id=institution_id,
        user_id=user_id,
        revoked=removed,
        already_revoked=not removed,
        message=REVOCATION_MESSAGE,
    )


def _institution_name_index(client, institution_ids: set) -> list[dict[str, Any]]:
    """Fetch name rows for a bounded set of institution ids (no N+1)."""
    ids = [str(value) for value in institution_ids if value is not None]
    if not ids:
        return []
    response = (
        client.table("institutions")
        .select("institution_id, name")
        .in_("institution_id", ids)
        .execute()
    )
    return list(response.data or [])
def list_platform_audit(
    *,
    institution_id: UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = platform_repo.AUDIT_PAGE_SIZE_DEFAULT,
    offset: int = 0,
) -> PlatformAuditListResponse:
    """Return one read-only page of the platform audit ledger.

    Every caller reaches this through a route that declares
    ``Depends(require_super_admin)``, so the audit view can never become an
    institution-admin surface: anonymous callers get 401 and every tenant role —
    including a University Admin — gets 403 before this function runs.

    Actor emails and institution names are resolved server-side so the operator
    can see WHO acted and WHERE (which identifies which of several Super Admins
    performed the action) without exposing any tenant-owned data. There is
    deliberately no mutation counterpart to this function and no route for one.
    """
    client = get_admin_client()
    # Bounded page size, applied server-side so a caller cannot request an
    # unbounded dump of the ledger.
    safe_limit = max(1, min(int(limit), platform_repo.AUDIT_PAGE_SIZE_MAX))
    safe_offset = max(0, int(offset))

    rows = platform_repo.list_audit_entries(
        client,
        institution_id=institution_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=safe_limit,
        offset=safe_offset,
    )

    # Resolve display names with two bounded lookups instead of one query per
    # audit entry (no N+1) and without a PostgREST relationship embed.
    institution_names = {
        str(row["institution_id"]): row.get("name")
        for row in _institution_name_index(
            client, {r.get("institution_id") for r in rows}
        )
    }
    actors = platform_repo.list_users_by_ids(
        client, [str(r["actor_user_id"]) for r in rows if r.get("actor_user_id")]
    )

    entries = [
        PlatformAuditEntry(
            audit_id=UUID(str(row["audit_id"])),
            actor_user_id=(
                UUID(str(row["actor_user_id"])) if row.get("actor_user_id") else None
            ),
            actor_email=(
                str(actors[str(row["actor_user_id"])]["email"])
                if row.get("actor_user_id")
                and str(row["actor_user_id"]) in actors
                else None
            ),
            action=str(row.get("action")),
            institution_id=UUID(str(row["institution_id"])),
            institution_name=institution_names.get(str(row["institution_id"])),
            target_user_id=(
                UUID(str(row["target_user_id"])) if row.get("target_user_id") else None
            ),
            result=str(row.get("result", "success")),
            details=row.get("details") or {},
            performed_at=row.get("performed_at"),
        )
        for row in rows
    ]
    total = platform_repo.count_audit_entries(
        client, institution_id=institution_id, action=action
    )
    return PlatformAuditListResponse(
        entries=entries,
        total=total,
        limit=safe_limit,
        offset=safe_offset,
    )