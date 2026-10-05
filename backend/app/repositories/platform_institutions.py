"""Phase 7.13 — Super Admin institution-management repository.

Data access for the platform-scoped institution boundary. Follows the existing
repository convention (see ``app/repositories/tenancy.py``): every function takes
an already-created Supabase ``Client`` as its first argument and contains NO
authorization logic. Authorization lives exclusively in the API layer's
``require_super_admin`` dependency, so an institution id in a URL is always only
a *resource* identifier and never an authorization credential.

This module deliberately EXTENDS the canonical ``public.institutions`` tenant
rather than introducing a second university/college/tenant model. The Phase 7.13
migration added only optional branding columns to that same table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client

# Platform list/detail projection. Explicitly selects only the columns the
# Super Admin UI needs. Organization linkage, contact details and join codes are
# intentionally NOT selected, so they cannot leak through this boundary even by
# accident.
PLATFORM_INSTITUTION_COLUMNS = (
    "institution_id, name, code, display_name, logo_url, primary_color, "
    "secondary_color, welcome_message, status, is_active, created_at, updated_at"
)

# Columns a Super Admin may change. ``institution_id`` and ``organization_id``
# are structurally absent, so no update path can rewrite a primary key or
# reassign a tenant.
MUTABLE_INSTITUTION_FIELDS = frozenset(
    {
        "name",
        "code",
        "display_name",
        "logo_url",
        "primary_color",
        "secondary_color",
        "welcome_message",
        "email",
        "address",
        "city",
        "country",
    }
)

# Audit action vocabulary - kept in sync with the Phase 7.13 migration CHECK
# constraint so a repository write can never produce an unrepresentable value.
AUDIT_INSTITUTION_CREATED = "institution_created"
AUDIT_INSTITUTION_UPDATED = "institution_updated"
AUDIT_INSTITUTION_SUSPENDED = "institution_suspended"
AUDIT_INSTITUTION_ACTIVATED = "institution_activated"
AUDIT_ADMIN_ASSIGNED = "admin_assigned"

# Phase 7.14 University Admin lifecycle. Kept in sync with the extended CHECK
# constraint in the Phase 7.14 migration so a repository write can never produce
# an unrepresentable action value.
AUDIT_ADMIN_INVITED = "institution_admin_invited"
AUDIT_ADMIN_INVITATION_ACCEPTED = "institution_admin_invitation_accepted"
AUDIT_ADMIN_INVITATION_EXPIRED = "institution_admin_invitation_expired"
AUDIT_ADMIN_INVITATION_CANCELLED = "institution_admin_invitation_cancelled"
AUDIT_ADMIN_REVOKED = "institution_admin_revoked"

# Phase 7.15 invitation delivery / email verification. These are ADDITIONAL
# events for actions the Phase 7.14 vocabulary has no word for; they never
# replace one of the lifecycle events above, so no action is double-counted.
# ``institution_admin_invited`` still fires exactly once per invitation issue
# (including a resend's reissue is recorded separately as ``..._resent``), and
# ``..._accepted`` still fires exactly once per successful acceptance.
AUDIT_ADMIN_INVITATION_EMAIL_SENT = "institution_admin_invitation_email_sent"
AUDIT_ADMIN_INVITATION_EMAIL_FAILED = "institution_admin_invitation_email_failed"
AUDIT_ADMIN_INVITATION_RESENT = "institution_admin_invitation_resent"
AUDIT_ADMIN_INVITATION_VERIFIED = "institution_admin_invitation_verified"

AUDIT_RESULT_SUCCESS = "success"
AUDIT_RESULT_ALREADY_APPLIED = "already_applied"
AUDIT_RESULT_DENIED = "denied"
# Phase 7.15: an operation was attempted and the system/provider failed to
# complete it (e.g. email delivery). Distinct from ``denied``, which means an
# authorization refusal, so a delivery outage is never misread as a security
# event.
AUDIT_RESULT_FAILED = "failed"

PLATFORM_ORGANIZATION_CODE = "COLLEGE-AI-PLATFORM"


def list_platform_institutions(client: Client) -> list[dict[str, Any]]:
    """Return every institution with its platform-safe columns, name-ordered."""
    response = (
        client.table("institutions")
        .select(PLATFORM_INSTITUTION_COLUMNS)
        .order("name")
        .execute()
    )
    return response.data or []


def get_platform_institution(
    client: Client, institution_id: UUID | str
) -> dict[str, Any] | None:
    """Return one institution platform-safe row, or None when it does not exist."""
    response = (
        client.table("institutions")
        .select(PLATFORM_INSTITUTION_COLUMNS)
        .eq("institution_id", str(institution_id))
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def institution_code_taken(
    client: Client, code: str, *, excluding_institution_id: UUID | str | None = None
) -> bool:
    """True when another institution already uses this routing code.

    ``excluding_institution_id`` lets an update keep its own code without a
    false duplicate.
    """
    response = (
        client.table("institutions")
        .select("institution_id")
        .eq("code", code.strip().upper())
        .execute()
    )
    for row in response.data or []:
        if (
            excluding_institution_id is not None
            and str(row.get("institution_id")) == str(excluding_institution_id)
        ):
            continue
        return True
    return False


def get_platform_organization_id(client: Client) -> str | None:
    """Resolve the reserved platform parent organization id.

    Created by the Phase 7.13 migration. Returning None means the migration has
    not been applied, and the service layer fails closed rather than inventing
    a parent.
    """
    response = (
        client.table("organizations")
        .select("organization_id")
        .eq("organization_code", PLATFORM_ORGANIZATION_CODE)
        .maybe_single()
        .execute()
    )
    row = response.data if response and response.data else None
    if row is None or row.get("organization_id") is None:
        return None
    return str(row["organization_id"])


def insert_platform_institution(
    client: Client,
    *,
    organization_id: UUID | str,
    name: str,
    code: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Insert one institution in ACTIVE state and return the created row.

    The institution is created ACTIVE because a Super Admin explicitly
    provisioned it at the platform level; the Phase 6.13 status trigger derives
    ``is_active = true`` from that status, so no separate flag is written here
    and the institution is immediately usable for public AI.

    ``fields`` is filtered against ``MUTABLE_INSTITUTION_FIELDS`` so no caller can
    smuggle an identity, scope or lifecycle column into the insert.
    """
    payload: dict[str, Any] = {
        "organization_id": str(organization_id),
        "name": name,
        "code": code,
        "status": "active",
    }
    for key, value in fields.items():
        if key in MUTABLE_INSTITUTION_FIELDS:
            payload[key] = value
    response = client.table("institutions").insert(payload).execute()
    rows = response.data if isinstance(response.data, list) else [response.data]
    if not rows or not rows[0].get("institution_id"):
        raise RuntimeError("institutions insert did not return institution_id")
    return rows[0]


def update_platform_institution(
    client: Client, institution_id: UUID | str, fields: dict[str, Any]
) -> dict[str, Any] | None:
    """Update only mutable platform configuration columns for one institution.

    ``institution_id`` and ``organization_id`` can never appear in ``fields``, so
    this can never rewrite a primary key, move an institution between parents,
    or reassign any student/knowledge/document row.
    """
    payload = {
        key: value for key, value in fields.items() if key in MUTABLE_INSTITUTION_FIELDS
    }
    if not payload:
        return get_platform_institution(client, institution_id)
    response = (
        client.table("institutions")
        .update(payload)
        .eq("institution_id", str(institution_id))
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


def set_institution_status(
    client: Client, institution_id: UUID | str, status: str
) -> dict[str, Any] | None:
    """Set an institution lifecycle status.

    ``is_active`` is derived by the existing Phase 6.13 status trigger, so this
    writes ONLY ``status`` and there is exactly one source of truth for tenant
    availability. No related row is touched: suspension retains students,
    faculty, staff, admins, knowledge and documents.
    """
    response = (
        client.table("institutions")
        .update({"status": status})
        .eq("institution_id", str(institution_id))
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


def _admin_role(client: Client) -> dict[str, Any] | None:
    """Resolve the canonical 'admin' role row (the tenant-scoped admin role).

    NOTE: the roles primary key column is ``id`` (``user_roles.role_id`` is the
    foreign key that references it), so the projection must alias it explicitly.
    """
    response = (
        client.table("roles")
        .select("id, name, is_active")
        .eq("name", "admin")
        .maybe_single()
        .execute()
    )
    role = response.data if response and response.data else None
    if role is None or not role.get("is_active", True):
        return None
    return role


def count_institution_admins(client: Client, institution_id: UUID | str) -> int:
    """Count University Admins (role admin, institution scope) for one tenant."""
    role = _admin_role(client)
    if role is None:
        return 0
    response = (
        client.table("user_roles")
        .select("user_id")
        .eq("role_id", str(role["id"]))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .execute()
    )
    return len(response.data or [])


def list_institution_admin_counts(client: Client) -> dict[str, int]:
    """Return ``{institution_id: admin_count}`` for the whole platform.

    One bounded read of the admin-scoped user_roles rows so the institution list
    can show an admin count without an N+1 query per row.
    """
    role = _admin_role(client)
    if role is None:
        return {}
    response = (
        client.table("user_roles")
        .select("scope_id")
        .eq("role_id", str(role["id"]))
        .eq("scope_type", "institution")
        .execute()
    )
    counts: dict[str, int] = {}
    for row in response.data or []:
        scope_id = row.get("scope_id")
        if scope_id is None:
            continue
        counts[str(scope_id)] = counts.get(str(scope_id), 0) + 1
    return counts


def get_user_by_email(client: Client, email: str) -> dict[str, Any] | None:
    """Resolve an existing ``public.users`` row by account email.

    Used by the assignment flow so an already-provisioned account can receive an
    institution-scoped admin grant. No Auth account is ever created here.
    """
    response = (
        client.table("users")
        .select("id, email, status")
        .eq("email", email.strip().lower())
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def has_institution_admin_grant(
    client: Client, user_id: UUID | str, institution_id: UUID | str
) -> bool:
    """True when this account already holds the institution admin grant."""
    role = _admin_role(client)
    if role is None:
        return False
    response = (
        client.table("user_roles")
        .select("user_id")
        .eq("user_id", str(user_id))
        .eq("role_id", str(role["id"]))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .maybe_single()
        .execute()
    )
    return bool(response.data)


def assign_institution_admin(
    client: Client,
    *,
    actor_user_id: UUID | str,
    user_id: UUID | str,
    institution_id: UUID | str,
    organization_id: UUID | str | None = None,
) -> dict[str, Any]:
    """Grant the institution-scoped ``admin`` role to an existing account.

    The database operation is atomic with its institution-scoped audit event.
    The function derives the organization from the institution and independently
    validates platform authority or invitation acceptance.
    """
    response = client.rpc(
        "phase81_assign_institution_role_audited",
        {
            "p_actor_user_id": str(actor_user_id),
            "p_target_user_id": str(user_id),
            "p_institution_id": str(institution_id),
            "p_role_name": 'admin',
        },
    ).execute()
    return {"changed": bool(response.data)}


def record_institution_audit(
    client: Client,
    *,
    actor_user_id: UUID | str,
    action: str,
    institution_id: UUID | str,
    result: str = AUDIT_RESULT_SUCCESS,
    target_user_id: UUID | str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append one auditable entry for an institution management action.

    ``details`` must contain only non-sensitive summary data (changed field
    names, resulting status). Passwords, tokens and service-role credentials are
    never accepted by this signature.
    """
    client.table("platform_institution_audit_log").insert(
        {
            "actor_user_id": str(actor_user_id),
            "action": action,
            "institution_id": str(institution_id),
            "target_user_id": str(target_user_id) if target_user_id else None,
            "result": result,
            "details": details or {},
        }
    ).execute()


# ---------------------------------------------------------------------------
# Phase 7.14 — admin roster and scoped revocation
# ---------------------------------------------------------------------------

# Minimal projection for a roster row. Only the application identity and its
# lifecycle status; never a name, credential, token or student record.
ROSTER_USER_COLUMNS = "id, email, status"


def list_institution_admin_user_ids(
    client: Client, institution_id: UUID | str
) -> list[str]:
    """Return the user ids holding the institution-scoped ``admin`` grant.

    Only the exact tuple (role=admin, scope_type=institution,
    scope_id=<this institution>) is selected. A user who is a Super Admin, or an
    admin of a different institution, is never returned by this query and can
    therefore never appear in this institution's roster.
    """
    role = _admin_role(client)
    if role is None:
        return []
    response = (
        client.table("user_roles")
        .select("user_id")
        .eq("role_id", str(role["id"]))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .execute()
    )
    return [str(row["user_id"]) for row in (response.data or []) if row.get("user_id")]


def list_users_by_ids(
    client: Client, user_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Return ``{user_id: {email, status}}`` for a bounded set of ids."""
    if not user_ids:
        return {}
    response = (
        client.table("users").select(ROSTER_USER_COLUMNS).in_("id", user_ids).execute()
    )
    return {str(row["id"]): row for row in (response.data or []) if row.get("id")}


def get_user_by_id(client: Client, user_id: UUID | str) -> dict[str, Any] | None:
    """Return one ``public.users`` row by primary key, or None."""
    response = (
        client.table("users")
        .select(ROSTER_USER_COLUMNS)
        .eq("id", str(user_id))
        .maybe_single()
        .execute()
    )
    return response.data if response is not None and response.data else None


def _super_admin_role_id(client: Client) -> str | None:
    response = (
        client.table("roles")
        .select("id")
        .eq("name", "super_admin")
        .maybe_single()
        .execute()
    )
    row = response.data if response is not None and response.data else None
    return str(row["id"]) if row and row.get("id") else None


def has_platform_super_admin_grant(client: Client, user_id: UUID | str) -> bool:
    """True when the account ALSO holds a platform-scoped ``super_admin`` grant.

    Revocation refuses such an account outright rather than removing one of its
    roles, so an operator can never accidentally strip platform authority while
    intending to remove a tenant admin grant.
    """
    role_id = _super_admin_role_id(client)
    if role_id is None:
        return False
    response = (
        client.table("user_roles")
        .select("user_id")
        .eq("user_id", str(user_id))
        .eq("role_id", role_id)
        .eq("scope_type", "platform")
        .execute()
    )
    return bool(response.data)


def find_institution_admin_grant(
    client: Client, *, user_id: UUID | str, institution_id: UUID | str
) -> dict[str, Any] | None:
    """Return the exact institution-scoped admin ``user_roles`` row, or None.

    Revocation safety depends on this being an EXACT tuple match. It can only
    ever match a grant that is already ``admin`` + ``institution`` + this exact
    institution, so deleting what it returns can never remove a ``super_admin``
    grant, another institution's admin grant, or any unrelated role.
    """
    role = _admin_role(client)
    if role is None:
        return None
    response = (
        client.table("user_roles")
        .select("user_id, role_id, scope_type, scope_id, scope_organization_id")
        .eq("user_id", str(user_id))
        .eq("role_id", str(role["id"]))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .maybe_single()
        .execute()
    )
    return response.data if response is not None and response.data else None


def revoke_institution_admin_grant(
    client: Client, *, user_id: UUID | str, institution_id: UUID | str
) -> bool:
    """Delete exactly one institution-scoped admin grant. True when removed.

    The DELETE re-asserts every component of the match (user, role, scope type,
    scope id) rather than trusting a previously fetched row, so even a stale or
    tampered intermediate result cannot widen the deletion to another role or
    another tenant. The Auth account and every other ``user_roles`` row of that
    user are untouched.
    """
    role = _admin_role(client)
    if role is None:
        return False
    response = (
        client.table("user_roles")
        .delete()
        .eq("user_id", str(user_id))
        .eq("role_id", str(role["id"]))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .execute()
    )
    return bool(response.data)


# ---------------------------------------------------------------------------
# Phase 7.14 — read-only platform audit query
# ---------------------------------------------------------------------------

# The ledger has no credential column of any kind: actor, action, institution,
# optional target, result, a bounded jsonb summary and a timestamp. `details` is
# written by the server and is asserted in tests to be free of tokens/passwords.
AUDIT_VIEW_COLUMNS = (
    "audit_id, actor_user_id, action, institution_id, target_user_id, "
    "result, details, performed_at"
)

AUDIT_PAGE_SIZE_DEFAULT = 50
AUDIT_PAGE_SIZE_MAX = 200


def _audit_query(
    client: Client,
    *,
    institution_id: UUID | str | None,
    action: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
):
    """Build the shared, fully parameterized audit query."""
    query = client.table("platform_institution_audit_log").select(AUDIT_VIEW_COLUMNS)
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    if action:
        query = query.eq("action", action)
    if date_from is not None:
        query = query.gte("performed_at", date_from.isoformat())
    if date_to is not None:
        query = query.lte("performed_at", date_to.isoformat())
    return query


def list_audit_entries(
    client: Client,
    *,
    institution_id: UUID | str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = AUDIT_PAGE_SIZE_DEFAULT,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return one bounded page of the platform audit ledger, newest first.

    Every filter is optional; with none supplied this is simply the newest page
    of the whole ledger. Callers apply ``require_super_admin`` before reaching
    here, and there is deliberately no mutation counterpart to this function.
    """
    query = _audit_query(
        client,
        institution_id=institution_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )
    response = (
        query.order("performed_at", desc=True).range(offset, offset + limit).execute()
    )
    return response.data or []


def count_audit_entries(
    client: Client,
    *,
    institution_id: UUID | str | None = None,
    action: str | None = None,
) -> int:
    """Count the audit rows matching the identity filters (for pagination)."""
    query = _audit_query(
        client,
        institution_id=institution_id,
        action=action,
        date_from=None,
        date_to=None,
    ).select("audit_id", count="exact")
    response = query.execute()
    return int(getattr(response, "count", 0) or 0)