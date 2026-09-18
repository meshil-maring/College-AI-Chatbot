"""Phase 6.13.4 — Organization & Institution APPROVAL WORKFLOW tests.

Covers the required security matrix:

    1.  authorized organization approval (platform admin)
    2.  unauthorized organization approval (org admin self-approval, others)
    3.  organization rejection
    4.  repeated organization decision (idempotent-safe 422)
    5.  pending organization access denied
    6.  authorized institution approval (owning org admin)
    7.  unauthorized institution approval (institution admin, other roles)
    8.  institution rejection
    9.  repeated join-request decision (422)
    10. pending institution access denied
    11. approved institution access allowed
    12. cross-organization approval attempt denied
    13. institution admin receives ONLY institution scope
    14. institution admin cannot access another institution
    15. organization admin scope behavior
    16. Phase 6.13.1-6.13.3 regression markers

The Supabase service-role PostgREST client, the authorization-context source
rows (user_roles) and the GoTrue client are all mocked — no live services.
The server-side authorization chain (``resolve_authorization_context`` and the
``assert_*`` guards) runs FOR REAL against the mocked role rows, exactly like
the Phase 6.13.1 tenancy tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.repositories import tenancy as tenancy_repo
from app.services import authorization as authz
from app.services import student_registration as student_svc
from app.services import tenancy as tenancy_svc

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Stable identifiers
# ---------------------------------------------------------------------------

ORG_A = "a0000000-0000-0000-0000-00000000000a"
ORG_B = "a0000000-0000-0000-0000-00000000000b"
INST_A1 = "b0000000-0000-0000-0000-0000000000a1"
INST_B1 = "b0000000-0000-0000-0000-0000000000b1"
JR_A1 = "d0000000-0000-0000-0000-000000000001"
JR_B1 = "d0000000-0000-0000-0000-000000000002"
PLATFORM_USER = "c0000000-0000-0000-0000-000000000001"
ORG_A_ADMIN = "c0000000-0000-0000-0000-000000000002"
ORG_B_ADMIN = "c0000000-0000-0000-0000-000000000003"
INST_A1_ADMIN = "c0000000-0000-0000-0000-000000000004"
STAFF_USER = "c0000000-0000-0000-0000-000000000005"
ROLE_ID = "e0000000-0000-0000-0000-000000000001"
AUTH_ID = "f0000000-0000-0000-0000-000000000001"
MEMBERSHIP_REQUEST_ID = "e1000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Fake service-role PostgREST client (stateful, per-table)
# ---------------------------------------------------------------------------


class _Table:
    """Chainable query builder answering reads/writes from ``state``."""

    def __init__(self, state: dict, name: str):
        self._state = state
        self._name = name
        self._filters: list[tuple[str, object]] = []
        self._single = False

    # -- builder ------------------------------------------------------------
    def select(self, *a, **k):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def ilike(self, column, pattern):
        # Normalize comparison the same way real Supabase does:
        # lowercase both sides and use a simple equality match for the fake.
        self._filters.append((column, pattern.strip().lower()))
        return self

    def order(self, *a, **k):
        return self

    def maybe_single(self):
        self._single = True
        return self

    def update(self, payload):
        self._payload = payload
        return self

    def insert(self, payload):
        self._payload = payload
        return self

    # -- execution ----------------------------------------------------------
    def _rows(self):
        rows = self._state.get(self._name, {})
        if isinstance(rows, dict):
            rows = list(rows.values())
        matched = [
            row
            for row in rows
            if all(
                str(row.get(column, "")).lower() == str(value).lower()
                for column, value in self._filters
            )
        ]
        return matched

    def execute(self):
        table = self._name
        payload = getattr(self, "_payload", None)
        if payload is not None:
            rows = self._rows()
            if rows:
                # UPDATE: modify every row matching the current filters.
                updated = []
                for row in rows:
                    row.update(payload)
                    # Emulate the trg_phase613_institutions_status trigger:
                    # is_active is derived from status on every write.
                    if table == "institutions":
                        row["is_active"] = row.get("status") == "active"
                    self._state.setdefault("updates", []).append((table, dict(row)))
                    updated.append(row)
                return SimpleNamespace(data=updated)
            # INSERT (new row, no existing rows matched): id injected by the fake.
            created = dict(payload)
            if table == "users":
                created.setdefault("user_id", STAFF_USER)
            elif table == "institution_membership_requests":
                created.setdefault("request_id", MEMBERSHIP_REQUEST_ID)
            self._state.setdefault(table, []).append(created)
            return SimpleNamespace(data=[created])
        rows = self._rows()
        if self._single:
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)


def _db(state: dict):
    db = MagicMock()
    db.table.side_effect = lambda name: _Table(state, name)
    return db


def _org_row(org_id=ORG_A, status="pending"):
    return {
        "organization_id": org_id,
        "name": "Acme Org" if org_id == ORG_A else "Beta Org",
        "organization_code": "ACME" if org_id == ORG_A else "BETA",
        "official_email": "info@acme.example.com",
        "contact_information": "contact@acme.example.com",
        "status": status,
        "join_code": None,
        "created_at": "2026-09-17T00:00:00Z",
        "updated_at": "2026-09-17T00:00:00Z",
    }


def _inst_row(inst_id=INST_A1, org_id=ORG_A, status="pending", is_active=False):
    return {
        "institution_id": inst_id,
        "organization_id": org_id,
        "name": "Imphal College",
        "code": "IMPHAL" if inst_id == INST_A1 else "BETACOLLEGE",
        "email": None,
        "address": None,
        "city": None,
        "state": None,
        "country": None,
        "status": status,
        "is_active": is_active,
        "created_at": "2026-09-17T00:00:00Z",
        "updated_at": "2026-09-17T00:00:00Z",
    }


def _jr_row(join_request_id=JR_A1, org_id=ORG_A, inst_id=INST_A1, status="pending"):
    return {
        "join_request_id": join_request_id,
        "organization_id": org_id,
        "institution_id": inst_id,
        "requested_institution_code": "IMPHAL",
        "requested_by_user_id": INST_A1_ADMIN,
        "status": status,
        "decision_reason": None,
        "decided_by_user_id": None,
        "decided_at": None,
        "created_at": "2026-09-17T00:00:00Z",
        "updated_at": "2026-09-17T00:00:00Z",
    }


def _base_state():
    return {
        "organizations": {ORG_A: _org_row()},
        "institutions": {INST_A1: _inst_row()},
        "institution_join_requests": {JR_A1: _jr_row()},
        "users": [],
        "institution_membership_requests": [],
        "updates": [],
    }


# ---------------------------------------------------------------------------
# Authorization context: server-side resolution against mocked user_roles
# ---------------------------------------------------------------------------


def _role_rows(scope_type, scope_id, org_id, role="admin"):
    return [
        {
            "role_id": ROLE_ID,
            "role_name": role,
            "is_active": True,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "scope_organization_id": org_id,
        }
    ]


def _authz_patches(user_id: str, rows: list):
    """Resolve the authorization context FOR REAL from the mocked role rows."""
    return (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    )


PLATFORM_ROWS = _role_rows("platform", None, None)
ORG_A_ADMIN_ROWS = _role_rows("organization", ORG_A, ORG_A)
ORG_B_ADMIN_ROWS = _role_rows("organization", ORG_B, ORG_B)
INST_A1_ADMIN_ROWS = _role_rows("institution", INST_A1, ORG_A)
FACULTY_ROWS = _role_rows("institution", INST_A1, ORG_A, role="faculty")


def _login(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": user_id,
        "auth_user_id": AUTH_ID,
        "email": "user@example.com",
        "roles": ["admin"],
        "institution_id": None,
    }


def _logout():
    app.dependency_overrides.pop(get_current_user, None)


def _decision(decision: str, reason: str | None = None) -> dict:
    body: dict = {"decision": decision}
    if reason:
        body["reason"] = reason
    return body


# ===========================================================================
# 1-5. ORGANIZATION approval lifecycle (platform authority only)
# ===========================================================================


def test_1_authorized_organization_approval():
    """Platform admin approves a pending organization -> 'active' + cascade."""
    state = _base_state()
    state["institution_join_requests"][JR_B1] = _jr_row(JR_B1, ORG_A, INST_B1)
    state["institutions"][INST_B1] = _inst_row(INST_B1, ORG_A)
    _login(PLATFORM_USER)
    patches = _authz_patches(PLATFORM_USER, PLATFORM_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/organizations/{ORG_A}/decision", json=_decision("approve")
        )
    _logout()
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approve"
    # Row status uses the DB vocabulary (NOT the raw decision literal).
    assert state["organizations"][ORG_A]["status"] == "active"
    joined = state["institution_join_requests"]
    assert joined[JR_A1]["status"] == "approved"
    assert joined[JR_B1]["status"] == "approved"
    # Institutions activated (trigger-derived is_active emulated).
    assert state["institutions"][INST_A1]["status"] == "active"
    assert state["institutions"][INST_A1]["is_active"] is True
    assert state["institutions"][INST_B1]["is_active"] is True


def test_2_unauthorized_organization_approval():
    """Organization admin can NEVER self-approve; institution admin neither."""
    for user_id, rows in (
        (ORG_A_ADMIN, ORG_A_ADMIN_ROWS),
        (INST_A1_ADMIN, INST_A1_ADMIN_ROWS),
    ):
        state = _base_state()
        _login(user_id)
        patches = _authz_patches(user_id, rows)
        with (
            patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
            patches[0],
            patches[1],
            patches[2],
        ):
            resp = client.post(
                f"/api/v1/organizations/{ORG_A}/decision", json=_decision("approve")
            )
        _logout()
        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["code"] == "FORBIDDEN"
        # Nothing changed.
        assert state["organizations"][ORG_A]["status"] == "pending"
        assert state["updates"] == []


def test_2b_non_admin_role_cannot_approve_organization():
    state = _base_state()
    _login(STAFF_USER)
    patches = _authz_patches(STAFF_USER, FACULTY_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/organizations/{ORG_A}/decision", json=_decision("approve")
        )
    _logout()
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_2c_decision_endpoints_are_never_public():
    """No token -> 401 (authenticated endpoints only)."""
    _logout()
    for url in (
        f"/api/v1/organizations/{ORG_A}/decision",
        f"/api/v1/institutions/join-requests/{JR_A1}/decision",
    ):
        resp = client.post(url, json=_decision("approve"))
        assert resp.status_code == 401, url
        assert resp.json()["error"]["code"] == "AUTH_REQUIRED"


def test_3_organization_rejection():
    """Platform admin rejects -> org 'rejected'; pending joins rejected too."""
    state = _base_state()
    _login(PLATFORM_USER)
    patches = _authz_patches(PLATFORM_USER, PLATFORM_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/organizations/{ORG_A}/decision",
            json=_decision("reject", reason="Incomplete documentation"),
        )
    _logout()
    assert resp.status_code == 200, resp.text
    assert state["organizations"][ORG_A]["status"] == "rejected"
    assert state["institution_join_requests"][JR_A1]["status"] == "rejected"
    assert state["institutions"][INST_A1]["status"] == "rejected"
    assert state["institutions"][INST_A1]["is_active"] is False


def test_4_repeated_organization_decision_is_safe():
    """A second decision on a decided organization fails with 422 (no rewrite)."""
    state = _base_state()
    state["organizations"][ORG_A]["status"] = "active"
    _login(PLATFORM_USER)
    patches = _authz_patches(PLATFORM_USER, PLATFORM_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/organizations/{ORG_A}/decision", json=_decision("reject")
        )
    _logout()
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_NOT_PENDING"
    # The active state was NOT rewritten to rejected.
    assert state["organizations"][ORG_A]["status"] == "active"


def test_5_pending_organization_access_denied():
    """A pending organization accepts no institution join requests."""
    from app.schemas.tenancy import InstitutionRegistrationRequest

    state = _base_state()  # organization ORG_A is 'pending'
    payload = InstitutionRegistrationRequest(
        name="Imphal College",
        institution_code="IMPHAL",
        organization_code="ACME",
        official_email="office@imphal.example.com",
        admin_email="admin@imphal.example.com",
        admin_password="secret123",
        admin_first_name="Imphal",
        admin_last_name="Admin",
    )
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            tenancy_svc.register_institution(payload)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "ORGANIZATION_NOT_ACCEPTING_REQUESTS"


# ===========================================================================
# 6-9, 12. INSTITUTION join-request lifecycle (owning org admin only)
# ===========================================================================


def test_6_authorized_institution_approval():
    """The owning organization's admin approves -> join 'approved', inst active."""
    state = _base_state()
    _login(ORG_A_ADMIN)
    patches = _authz_patches(ORG_A_ADMIN, ORG_A_ADMIN_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A1}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 200, resp.text
    # Join-request status uses the DB vocabulary 'approved' (never 'approve').
    assert state["institution_join_requests"][JR_A1]["status"] == "approved"
    assert state["institutions"][INST_A1]["status"] == "active"
    assert state["institutions"][INST_A1]["is_active"] is True


def test_7_unauthorized_institution_approval():
    """The requesting institution's own admin can NEVER decide its join request."""
    state = _base_state()
    _login(INST_A1_ADMIN)
    patches = _authz_patches(INST_A1_ADMIN, INST_A1_ADMIN_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A1}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_MISMATCH"
    assert state["institution_join_requests"][JR_A1]["status"] == "pending"
    assert state["institutions"][INST_A1]["status"] == "pending"


def test_7b_non_admin_role_cannot_decide_join_request():
    state = _base_state()
    _login(STAFF_USER)
    patches = _authz_patches(STAFF_USER, FACULTY_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A1}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_8_institution_rejection():
    """Org admin rejects -> join 'rejected', institution 'rejected' (inactive)."""
    state = _base_state()
    _login(ORG_A_ADMIN)
    patches = _authz_patches(ORG_A_ADMIN, ORG_A_ADMIN_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A1}/decision",
            json=_decision("reject", reason="Duplicate institution"),
        )
    _logout()
    assert resp.status_code == 200, resp.text
    assert state["institution_join_requests"][JR_A1]["status"] == "rejected"
    assert state["institutions"][INST_A1]["status"] == "rejected"
    assert state["institutions"][INST_A1]["is_active"] is False


def test_9_repeated_join_request_decision_is_safe():
    """Second decision on a decided join request -> 422 JOIN_REQUEST_NOT_PENDING."""
    state = _base_state()
    state["institution_join_requests"][JR_A1]["status"] = "approved"
    _login(ORG_A_ADMIN)
    patches = _authz_patches(ORG_A_ADMIN, ORG_A_ADMIN_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A1}/decision",
            json=_decision("reject"),
        )
    _logout()
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "JOIN_REQUEST_NOT_PENDING"
    assert state["institution_join_requests"][JR_A1]["status"] == "approved"


def test_12_cross_organization_approval_attempt_denied():
    """Organization B's admin can never decide organization A's join request."""
    state = _base_state()
    _login(ORG_B_ADMIN)
    patches = _authz_patches(ORG_B_ADMIN, ORG_B_ADMIN_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A1}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_MISMATCH"
    assert state["institution_join_requests"][JR_A1]["status"] == "pending"
    assert state["institutions"][INST_A1]["status"] == "pending"


def test_12b_unknown_join_request_is_404():
    state = _base_state()
    _login(ORG_A_ADMIN)
    patches = _authz_patches(ORG_A_ADMIN, ORG_A_ADMIN_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_B1}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "JOIN_REQUEST_NOT_FOUND"


# ===========================================================================
# 10-11. Pending vs approved institution access (fail-closed / open-on-active)
# ===========================================================================


def _staff_payload(institution_code: str):
    from app.schemas.tenancy import StaffFacultyRegistrationRequest

    return StaffFacultyRegistrationRequest(
        institution_code=institution_code,
        email="staff@imphal.example.com",
        password="secret123",
        first_name="Staff",
        last_name="Member",
        requested_role="staff",
    )


def _run_staff_registration(state: dict):
    """Run register_staff_or_faculty with every external client mocked."""
    auth = MagicMock()
    # _create_auth_account expects response.user.id (dict-like response).
    auth.auth.sign_up.return_value = MagicMock(user=MagicMock(id=AUTH_ID))
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patch.object(student_svc, "get_admin_client", return_value=MagicMock()),
        patch.object(student_svc, "create_supabase_client", return_value=auth),
    ):
        return tenancy_svc.register_staff_or_faculty(_staff_payload("IMPHAL"))


def test_10_pending_institution_access_denied():
    """A pending institution is not accepting registrations (fail closed)."""
    state = _base_state()  # institution INST_A1 is 'pending'
    with pytest.raises(AppError) as excinfo:
        _run_staff_registration(state)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"
    # No onboarding request and no auth account were created.
    assert state["institution_membership_requests"] == []


def test_11_approved_institution_access_allowed():
    """After approval the institution is ACTIVE and accepts registrations."""
    state = _base_state()
    # Emulate the approval decision having been applied.
    state["institution_join_requests"][JR_A1]["status"] = "approved"
    state["institutions"][INST_A1]["status"] = "active"
    state["institutions"][INST_A1]["is_active"] = True
    response = _run_staff_registration(state)
    assert response.requested_role == "staff"
    assert len(state["institution_membership_requests"]) == 1


# ===========================================================================
# 13-15. Role / scope behavior (institution-only scope for institution admins)
# ===========================================================================


def test_13_institution_admin_receives_only_institution_scope():
    """The institution admin's scope resolves to THEIR institution only —
    never an organization-wide scope, and never an approval authority."""
    patches = _authz_patches(INST_A1_ADMIN, INST_A1_ADMIN_ROWS)
    with patches[0], patches[1], patches[2]:
        context = authz.resolve_authorization_context(
            {"user_id": INST_A1_ADMIN, "institution_id": None}
        )
    assert context["scope_type"] == authz.INSTITUTION
    assert context["scope_id"] == INST_A1
    assert context["institution_id"] == INST_A1
    assert context["organization_id"] == ORG_A
    assert context["roles"] == ["admin"]
    # No organization-management authority (and therefore no self-approval).
    with pytest.raises(AppError) as org_err:
        authz.assert_can_manage_organization({"user_id": INST_A1_ADMIN}, context, ORG_A)
    assert org_err.value.code == "FORBIDDEN"
    # No join-request decision authority either.
    with pytest.raises(AppError) as jr_err:
        authz.assert_can_decide_join_request(context, {"organization_id": ORG_A})
    assert jr_err.value.code == "ORGANIZATION_MISMATCH"


def test_14_institution_admin_cannot_access_another_institution():
    context = {
        "user_id": INST_A1_ADMIN,
        "roles": ["admin"],
        "scope_type": authz.INSTITUTION,
        "scope_id": INST_A1,
        "organization_id": ORG_A,
        "institution_id": INST_A1,
    }
    authz.assert_can_manage_institution({"user_id": INST_A1_ADMIN}, context, INST_A1)
    with pytest.raises(AppError) as excinfo:
        authz.assert_can_manage_institution({"user_id": INST_A1_ADMIN}, context, INST_B1)
    assert excinfo.value.code == "TENANT_MISMATCH"
    assert excinfo.value.status_code == 403


def test_15_organization_admin_scope_behavior():
    """Org admin decides ONLY their own organization's joins — but platform
    approval of their own pending organization stays exclusive to the platform
    authority. Institution admin scope is institution-only, never organization."""
    context_a = {
        "user_id": ORG_A_ADMIN,
        "roles": ["admin"],
        "scope_type": authz.ORGANIZATION,
        "scope_id": ORG_A,
        "organization_id": ORG_A,
        "institution_id": None,
    }
    # Own join requests: decidable (org admin can decide their org's joins).
    authz.assert_can_decide_join_request(context_a, {"organization_id": ORG_A})
    # Another organization's join request: never.
    with pytest.raises(AppError) as cross:
        authz.assert_can_decide_join_request(context_a, {"organization_id": ORG_B})
    assert cross.value.code == "ORGANIZATION_MISMATCH"
    # Self-approval of the pending organization: structurally impossible.
    with pytest.raises(AppError) as self_approve:
        tenancy_svc._assert_platform_authority(context_a)
    assert self_approve.value.code == "FORBIDDEN"
    # ...while the platform authority passes the same gate.
    platform_context = {
        "user_id": PLATFORM_USER,
        "roles": ["admin"],
        "scope_type": authz.PLATFORM,
        "scope_id": None,
        "organization_id": None,
        "institution_id": None,
    }
    tenancy_svc._assert_platform_authority(platform_context)
    # Institution-scoped admin context: institution_id is set, organization_id is
    # NOT — the org admin scope does NOT leak organization-wide authority down to
    # institution scope. (The full DB-backed institution-management check is
    # covered by test_13/test_14; here we verify the context shape.)
    inst_context = {
        "user_id": INST_A1_ADMIN,
        "roles": ["admin"],
        "scope_type": authz.INSTITUTION,
        "scope_id": INST_A1,
        "organization_id": None,
        "institution_id": INST_A1,
    }
    # An institution-scoped admin cannot decide ANY join request.
    with pytest.raises(AppError) as inst_join:
        authz.assert_can_decide_join_request(inst_context, {"organization_id": ORG_A})
    assert inst_join.value.code == "ORGANIZATION_MISMATCH"
    # An institution-scoped admin cannot approve/reject ANY organization.
    with pytest.raises(AppError) as inst_org:
        tenancy_svc._assert_platform_authority(inst_context)
    assert inst_org.value.code == "FORBIDDEN"


# ===========================================================================
# 16. Phase 6.13.1-6.13.3 regression
# ===========================================================================


def test_16_registration_endpoints_and_repositories_unchanged():
    """Public registration endpoints still exist; decision endpoints are new,
    separate routes; the 6.13.1-6.13.3 service/repository surface is intact."""
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]
    assert "/api/v1/organizations/register" in paths
    assert "/api/v1/institutions/register" in paths
    assert "/api/v1/organizations/{organization_id}/decision" in paths
    assert "/api/v1/institutions/join-requests/{join_request_id}/decision" in paths
    # Existing repository/service surface reused (not rewritten).
    for fn in (
        tenancy_repo.update_organization_status,
        tenancy_repo.update_join_request_status,
        tenancy_repo.update_institution_status_for_join,
        tenancy_repo.update_join_requests_for_organization,
        tenancy_repo.get_organization_by_id,
        tenancy_repo.get_join_request_by_id,
        tenancy_svc.decide_organization,
        tenancy_svc.decide_join_request,
        tenancy_svc.register_organization,
        tenancy_svc.register_institution,
    ):
        assert callable(fn)
    # The status-vocabulary mapping respects the DB CHECK constraints.
    assert tenancy_svc.ORGANIZATION_DECISION_STATUS == {
        "approve": "active",
        "reject": "rejected",
    }
    assert tenancy_svc.JOIN_REQUEST_DECISION_STATUS == {
        "approve": "approved",
        "reject": "rejected",
    }
    assert tenancy_svc.INSTITUTION_DECISION_STATUS == {
        "approve": "active",
        "reject": "rejected",
    }


def test_16b_decision_schema_rejects_spoofed_fields():
    """extra='forbid': no client can inject status / scope / role fields."""
    state = _base_state()
    _login(ORG_A_ADMIN)
    patches = _authz_patches(ORG_A_ADMIN, ORG_A_ADMIN_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A1}/decision",
            json={"decision": "approve", "status": "approved", "scope_type": "platform"},
        )
    _logout()
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert state["institution_join_requests"][JR_A1]["status"] == "pending"


def test_16c_decision_literal_is_enforced():
    state = _base_state()
    _login(ORG_A_ADMIN)
    patches = _authz_patches(ORG_A_ADMIN, ORG_A_ADMIN_ROWS)
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A1}/decision",
            json={"decision": "self-approve"},
        )
    _logout()
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

