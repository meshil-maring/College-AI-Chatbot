"""Phase 6.13 — Organization / institution tenancy repository.

Data access for the organization → institution hierarchy introduced by the
Phase 6.13 migration:

    organizations                     (NEW)
        |  organization_id
    institutions                      (EXTENDED: +organization_id, +status)
        |  institution_id             (still the one and only tenant key)
    institution_join_requests         (NEW — institution → organization joining)
    institution_membership_requests   (NEW — staff/faculty onboarding ledger)
    user_roles                        (EXTENDED: +scope_type/scope_id/scope_organization_id)

Conventions follow the existing repositories (``admin_knowledge.py``,
``admin_academics.py``): every function takes an already-created Supabase
``Client`` as its first argument and contains NO authorization logic —
authorization lives in ``app.services.authorization``.

This repository NEVER assigns roles. Role grants are performed exclusively by
the approval services through ``assign_user_role_scope`` (server-side writes to
the existing ``user_roles`` table).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from supabase import Client

# ============================================================================
# Column projections
# ============================================================================

ORGANIZATION_COLUMNS = (
    "organization_id, name, organization_code, official_email, "
    "contact_information, status, join_code, created_at, updated_at"
)

# Public projection: never exposes join_code.
ORGANIZATION_PUBLIC_COLUMNS = (
    "organization_id, name, organization_code, official_email, "
    "contact_information, status, created_at, updated_at"
)

INSTITUTION_COLUMNS = (
    "institution_id, organization_id, name, code, email, address, city, "
    "state, country, status, is_active, created_at, updated_at"
)

JOIN_REQUEST_COLUMNS = (
    "join_request_id, organization_id, institution_id, "
    "requested_institution_code, requested_by_user_id, status, "
    "decision_reason, decided_by_user_id, decided_at, created_at, updated_at"
)

MEMBERSHIP_REQUEST_COLUMNS = (
    "request_id, institution_id, organization_id, user_id, requested_role, "
    "official_email, full_name, designation, department, status, "
    "decision_reason, decided_by_user_id, decided_at, created_at, updated_at"
)

# ============================================================================
# Organizations
# ============================================================================


def get_organization_by_id(client: Client, organization_id: UUID | str) -> dict | None:
    """Return one organization row, or None when it does not exist."""
    response = (
        client.table("organizations")
        .select(ORGANIZATION_COLUMNS)
        .eq("organization_id", str(organization_id))
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def get_organization_by_code(client: Client, organization_code: str) -> dict | None:
    """Return the organization with this PUBLIC code (case-insensitive), or None.

    The organization code is the human-usable handle typed at registration and
    institution-join time. Internal uuids are never used as codes.
    """
    response = (
        client.table("organizations")
        .select(ORGANIZATION_COLUMNS)
        .ilike("organization_code", organization_code.strip())
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def organization_code_exists(client: Client, organization_code: str) -> bool:
    """True when any organization already uses this code (case-insensitive)."""
    response = (
        client.table("organizations")
        .select("organization_id")
        .ilike("organization_code", organization_code.strip())
        .maybe_single()
        .execute()
    )
    return bool(response and response.data)


def insert_organization(
    client: Client,
    *,
    name: str,
    organization_code: str,
    official_email: str,
    contact_information: str,
    status: str = "pending",
    join_code: str | None = None,
) -> dict:
    """Insert one organization row and return it."""
    payload: dict = {
        "name": name.strip(),
        "organization_code": organization_code.strip().upper(),
        "official_email": official_email.strip().lower(),
        "contact_information": contact_information.strip(),
        "status": status,
    }
    if join_code is not None:
        payload["join_code"] = join_code
    response = client.table("organizations").insert(payload).execute()
    rows = response.data if isinstance(response.data, list) else [response.data]
    if not rows or not rows[0].get("organization_id"):
        raise RuntimeError("organizations insert did not return organization_id")
    return rows[0]


def update_organization_status(
    client: Client, organization_id: UUID | str, status: str
) -> dict | None:
    """Set an organization's lifecycle status; returns the updated row."""
    response = (
        client.table("organizations")
        .update({"status": status})
        .eq("organization_id", str(organization_id))
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


def set_organization_join_code(
    client: Client, organization_id: UUID | str, join_code: str | None
) -> dict | None:
    """Set or clear the organization-issued institution join code."""
    response = (
        client.table("organizations")
        .update({"join_code": join_code})
        .eq("organization_id", str(organization_id))
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


# ============================================================================
# Institutions
# ============================================================================


def get_institution_by_id(client: Client, institution_id: UUID | str) -> dict | None:
    """Return one institution row (with organization + status), or None."""
    response = (
        client.table("institutions")
        .select(INSTITUTION_COLUMNS)
        .eq("institution_id", str(institution_id))
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def get_institution_by_code(client: Client, code: str) -> dict | None:
    """Return the institution with this public code (globally unique), or None."""
    response = (
        client.table("institutions")
        .select(INSTITUTION_COLUMNS)
        .eq("code", code.strip().upper())
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def institution_code_exists(client: Client, code: str) -> bool:
    """True when any institution already uses this code."""
    response = (
        client.table("institutions")
        .select("institution_id")
        .eq("code", code.strip().upper())
        .maybe_single()
        .execute()
    )
    return bool(response and response.data)


def list_institutions_for_organization(
    client: Client, organization_id: UUID | str
) -> list[dict]:
    """List all institutions of one organization (any status)."""
    response = (
        client.table("institutions")
        .select(INSTITUTION_COLUMNS)
        .eq("organization_id", str(organization_id))
        .order("name")
        .execute()
    )
    return response.data or []


def insert_institution(
    client: Client,
    *,
    organization_id: UUID | str,
    name: str,
    code: str,
    email: str | None,
    address: str | None,
) -> dict:
    """Insert one institution row in PENDING state; returns the row.

    The Phase 6.13 trigger ``trg_phase613_institutions_status`` derives
    ``is_active`` from ``status`` on every write, so the pending institution is
    structurally unavailable (no registrations, no logins) until approval.
    """
    payload: dict = {
        "organization_id": str(organization_id),
        "name": name.strip(),
        "code": code.strip().upper(),
        "status": "pending",
        "is_active": False,
    }
    if email is not None:
        payload["email"] = email.strip().lower()
    if address is not None:
        payload["address"] = address.strip()
    response = client.table("institutions").insert(payload).execute()
    rows = response.data if isinstance(response.data, list) else [response.data]
    if not rows or not rows[0].get("institution_id"):
        raise RuntimeError("institutions insert did not return institution_id")
    return rows[0]


def update_institution_status(
    client: Client, institution_id: UUID | str, status: str
) -> dict | None:
    """Set an institution's lifecycle status (is_active is trigger-derived)."""
    response = (
        client.table("institutions")
        .update({"status": status})
        .eq("institution_id", str(institution_id))
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


def get_institution_organization(
    client: Client, institution_id: UUID | str
) -> UUID | None:
    """Return the owning organization_id of one institution, or None."""
    response = (
        client.table("institutions")
        .select("organization_id")
        .eq("institution_id", str(institution_id))
        .maybe_single()
        .execute()
    )
    row = response.data if response and response.data else None
    if row is None or row.get("organization_id") is None:
        return None
    return UUID(str(row["organization_id"]))


# ============================================================================
# Roles + user_roles (role + scope grants — server-side writes ONLY)
# ============================================================================


def get_role_by_name(client: Client, name: str) -> dict | None:
    """Return the roles row for one role name (admin / staff / faculty / student)."""
    response = (
        client.table("roles")
        .select("role_id, name, is_active")
        .eq("name", name)
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def get_user_role_scope_rows(client: Client, user_id: UUID | str) -> list[dict]:
    """Return the user's role rows WITH Phase 6.13 scope columns.

    Each row: {role_id, role_name, is_active, scope_type, scope_id,
    scope_organization_id}. The authorization service (not this repository)
    interprets them.
    """
    response = (
        client.table("user_roles")
        .select("role_id, roles(name), scope_type, scope_id, scope_organization_id")
        .eq("user_id", str(user_id))
        .execute()
    )
    rows = response.data or []
    normalized: list[dict] = []
    for row in rows:
        roles = row.get("roles")
        normalized.append(
            {
                "role_id": row.get("role_id"),
                "role_name": roles.get("name") if isinstance(roles, dict) else None,
                "is_active": bool(roles.get("is_active", True))
                if isinstance(roles, dict)
                else True,
                "scope_type": row.get("scope_type"),
                "scope_id": row.get("scope_id"),
                "scope_organization_id": row.get("scope_organization_id"),
            }
        )
    return normalized


def assign_user_role_scope(
    client: Client,
    *,
    user_id: UUID | str,
    role_id: UUID | str,
    scope_type: str,
    scope_id: UUID | str | None,
    scope_organization_id: UUID | str | None,
) -> dict:
    """Grant one role with its Phase 6.13 scope (server-side write).

    Idempotent on the existing (user_id, role_id) primary key; re-approval
    refreshes the scope columns. The Phase 6.13 trigger
    ``trg_phase613_user_roles_scope`` validates institution scopes against the
    institution's organization, so a cross-organization grant is structurally
    impossible.
    """
    payload: dict = {
        "user_id": str(user_id),
        "role_id": str(role_id),
        "scope_type": scope_type,
        "scope_id": str(scope_id) if scope_id is not None else None,
        "scope_organization_id": str(scope_organization_id)
        if scope_organization_id is not None
        else None,
    }
    response = (
        client.table("user_roles")
        .upsert(
            payload,
            on_conflict="user_id,role_id",
        )
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else payload


# ============================================================================
# institution_join_requests
# ============================================================================


def insert_join_request(
    client: Client,
    *,
    organization_id: UUID | str,
    institution_id: UUID | str,
    requested_institution_code: str,
    requested_by_user_id: UUID | str,
    status: str = "pending",
) -> dict:
    """Insert one institution → organization join request (pending)."""
    payload = {
        "organization_id": str(organization_id),
        "institution_id": str(institution_id),
        "requested_institution_code": requested_institution_code.strip().upper(),
        "requested_by_user_id": str(requested_by_user_id),
        "status": status,
    }
    response = client.table("institution_join_requests").insert(payload).execute()
    rows = response.data if isinstance(response.data, list) else [response.data]
    if not rows or not rows[0].get("join_request_id"):
        raise RuntimeError("institution_join_requests insert did not return id")
    return rows[0]


def get_join_request(client: Client, join_request_id: UUID | str) -> dict | None:
    """Return one join request row, or None."""
    response = (
        client.table("institution_join_requests")
        .select(JOIN_REQUEST_COLUMNS)
        .eq("join_request_id", str(join_request_id))
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def get_open_join_request_for_institution(
    client: Client, institution_id: UUID | str
) -> dict | None:
    """Return the institution's single open (pending) join request, or None."""
    response = (
        client.table("institution_join_requests")
        .select(JOIN_REQUEST_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("status", "pending")
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def list_join_requests(
    client: Client,
    organization_id: UUID | str,
    status: str | None = None,
) -> list[dict]:
    """List join requests of one organization (optionally by status)."""
    query = (
        client.table("institution_join_requests")
        .select(JOIN_REQUEST_COLUMNS)
        .eq("organization_id", str(organization_id))
    )
    if status is not None:
        query = query.eq("status", status)
    response = query.order("created_at", desc=True).execute()
    return response.data or []


def decide_join_request(
    client: Client,
    join_request_id: UUID | str,
    *,
    status: str,
    decided_by_user_id: UUID | str,
    decision_reason: str | None,
) -> dict | None:
    """Move one join request to approved/rejected with decision attribution.

    The conditional update (status = 'pending') makes a double-decision race a
    no-op returning None, which the service turns into 409.
    """
    response = (
        client.table("institution_join_requests")
        .update(
            {
                "status": status,
                "decided_by_user_id": str(decided_by_user_id),
                "decided_at": datetime.now(timezone.utc).isoformat(),
                "decision_reason": decision_reason,
            }
        )
        .eq("join_request_id", str(join_request_id))
        .eq("status", "pending")
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


# ============================================================================
# institution_membership_requests
# ============================================================================


def insert_membership_request(
    client: Client,
    *,
    institution_id: UUID | str,
    organization_id: UUID | str,
    user_id: UUID | str,
    requested_role: str,
    official_email: str,
    full_name: str,
    designation: str | None,
    department: str | None,
    status: str = "pending",
) -> dict:
    """Insert one staff/faculty onboarding request (pending; NO role granted)."""
    payload = {
        "institution_id": str(institution_id),
        "organization_id": str(organization_id),
        "user_id": str(user_id),
        "requested_role": requested_role,
        "official_email": official_email.strip().lower(),
        "full_name": full_name.strip(),
        "status": status,
    }
    if designation is not None:
        payload["designation"] = designation.strip()
    if department is not None:
        payload["department"] = department.strip()
    response = client.table("institution_membership_requests").insert(payload).execute()
    rows = response.data if isinstance(response.data, list) else [response.data]
    if not rows or not rows[0].get("request_id"):
        raise RuntimeError("institution_membership_requests insert did not return id")
    return rows[0]


def get_membership_request(client: Client, request_id: UUID | str) -> dict | None:
    """Return one membership request row, or None."""
    response = (
        client.table("institution_membership_requests")
        .select(MEMBERSHIP_REQUEST_COLUMNS)
        .eq("request_id", str(request_id))
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def list_membership_requests(
    client: Client,
    institution_id: UUID | str,
    status: str | None = None,
) -> list[dict]:
    """List membership requests of one institution (optionally by status)."""
    query = (
        client.table("institution_membership_requests")
        .select(MEMBERSHIP_REQUEST_COLUMNS)
        .eq("institution_id", str(institution_id))
    )
    if status is not None:
        query = query.eq("status", status)
    response = query.order("created_at", desc=True).execute()
    return response.data or []


def decide_membership_request(
    client: Client,
    request_id: UUID | str,
    *,
    status: str,
    decided_by_user_id: UUID | str,
    decision_reason: str | None,
) -> dict | None:
    """Move one membership request to approved/rejected with attribution.

    The conditional update (status = 'pending') makes a double-decision race a
    no-op returning None, which the service turns into 409.
    """
    response = (
        client.table("institution_membership_requests")
        .update(
            {
                "status": status,
                "decided_by_user_id": str(decided_by_user_id),
                "decided_at": datetime.now(timezone.utc).isoformat(),
                "decision_reason": decision_reason,
            }
        )
        .eq("request_id", str(request_id))
        .eq("status", "pending")
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


# ============================================================================
# public.users lookups
# ============================================================================


def get_user_by_email(client: Client, email: str) -> dict | None:
    """Resolve an existing public.users row by account email (globally unique)."""
    response = (
        client.table("users")
        .select("user_id, auth_user_id, email")
        .eq("email", email.strip().lower())
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


# ============================================================================
# Phase 6.13 decision helpers (status writes + role assignment)
# ============================================================================

# DB status vocabulary used by decision cascade functions in this module.
# mirrors the vocabulary in app.services.tenancy so that repository-level
# join-request updates use the same enum strings as the service layer.
JOIN_REQUEST_DECISION_STATUS = {"approve": "approved", "reject": "rejected"}
INSTITUTION_DECISION_STATUS = {"approve": "active", "reject": "rejected"}

JOIN_REQUEST_BY_ID_COLUMNS = (
    "join_request_id, organization_id, institution_id, "
    "requested_institution_code, requested_by_user_id, status, "
    "decision_reason, decided_by_user_id, decided_at, created_at, updated_at"
)


def get_join_request_by_id(client: Client, join_request_id: UUID | str) -> dict | None:
    """Return one institution_join_requests row by its request_id."""
    response = (
        client.table("institution_join_requests")
        .select(JOIN_REQUEST_BY_ID_COLUMNS)
        .eq("join_request_id", str(join_request_id))
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def update_join_request_status(
    client: Client, join_request_id: UUID | str, status: str
) -> dict | None:
    """Set the status of one join request. Returns the updated row."""
    response = (
        client.table("institution_join_requests")
        .update({"status": status})
        .eq("join_request_id", str(join_request_id))
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


def update_institution_status_for_join(
    client: Client, institution_id: UUID | str, status: str
) -> dict | None:
    """Set the status of the institution that belongs to one join request."""
    return update_institution_status(client, institution_id, status)


def update_institution_status(
    client: Client, institution_id: UUID | str, status: str
) -> dict | None:
    """Set an institution's status. Returns the updated row."""
    response = (
        client.table("institutions")
        .update({"status": status})
        .eq("institution_id", str(institution_id))
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None

def update_join_requests_for_organization(
    client: Client, organization_id: UUID | str, decision: str
) -> list[dict]:
    """Decide every STILL-PENDING join request of one organization (cascade).

    Used by ``decide_organization`` (Phase 6.13.4): when the organization
    itself is approved or rejected, all of its pending institution join
    requests are decided the same way — using the DB status vocabulary
    (``approved`` / ``rejected`` per ``institution_join_requests_status_check``)
    — and each affected institution's lifecycle status is set accordingly
    (``active`` / ``rejected``; ``is_active`` stays trigger-derived).

    Rows that were already decided (e.g. by a concurrent organization-admin
    decision) are left untouched: the cascade only moves ``pending`` rows.
    """
    join_status = JOIN_REQUEST_DECISION_STATUS.get(decision)
    institution_status = INSTITUTION_DECISION_STATUS.get(decision)
    if join_status is None or institution_status is None:
        raise ValueError(f"Unknown organization decision: {decision!r}")
    pending = list_join_requests(client, organization_id, status="pending")
    updated: list[dict] = []
    for request in pending:
        row = update_join_request_status(client, request["join_request_id"], join_status)
        if row is not None:
            updated.append(row)
        update_institution_status_for_join(
            client, request["institution_id"], institution_status
        )
    return updated


MEMBERSHIP_REQUEST_BY_ID_COLUMNS = (
    "request_id, institution_id, organization_id, user_id, requested_role, "
    "official_email, full_name, designation, department, status, "
    "decision_reason, decided_by_user_id, decided_at, created_at, updated_at"
)


def get_membership_request_by_id(
    client: Client, request_id: UUID | str
) -> dict | None:
    """Return one institution_membership_requests row by its request_id."""
    response = (
        client.table("institution_membership_requests")
        .select(MEMBERSHIP_REQUEST_BY_ID_COLUMNS)
        .eq("request_id", str(request_id))
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def update_membership_request_status(
    client: Client, request_id: UUID | str, status: str
) -> dict | None:
    """Set the status of one membership request. Returns the updated row."""
    response = (
        client.table("institution_membership_requests")
        .update({"status": status})
        .eq("request_id", str(request_id))
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    return rows[0] if rows else None


def assign_membership_role(
    client: Client,
    *,
    user_id: UUID | str,
    role_name: str,
    institution_id: UUID | str,
    organization_id: UUID | str,
) -> dict:
    """Server-side role grant for an approved staff/faculty onboarding.

    The write is performed through the existing ``assign_user_role_scope``
    repository so that Phase 6.13 span/integrity policies (the
    ``user_roles`` trigger) remain authoritative. This function is intentionally
    a thin delegation to that repo.
    """
    db_role = get_role_by_name(client, role_name)
    if db_role is None:
        raise RuntimeError(f"Role '{role_name}' is not configured")
    return assign_user_role_scope(
        client,
        user_id=str(user_id),
        role_id=db_role["role_id"],
        scope_type="institution",
        scope_id=str(institution_id),
        scope_organization_id=str(organization_id),
    )


def remove_membership_on_reject(
    client: Client,
    *,
    user_id: UUID | str,
    institution_id: UUID | str,
) -> None:
    """Best-effort cleanup when a request is rejected.

    The institution-scoped grant lives in the EXISTING ``user_roles`` scope
    columns (``scope_type`` / ``scope_id``) — ``user_roles`` has no
    ``institution_id`` column — so the delete is scoped with the Phase 6.13
    vocabulary that the approval path writes.

    The repository intentionally keeps this simple and fails silently-ish so
    that a reject never blocks the approval flow with a non-critical cleanup
    error. The primary accountability trail is the request row itself.
    """
    response = (
        client.table("user_roles")
        .delete()
        .eq("user_id", str(user_id))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .execute()
    )
    return None


