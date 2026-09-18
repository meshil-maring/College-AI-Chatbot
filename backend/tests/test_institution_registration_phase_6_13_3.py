"""Phase 6.13.3 — Institution registration / join request tests (mocked Supabase clients).

Covers:
* successful institution registration (201, pending institution + pending join request)
* existing-organization resolution (case-insensitive public code)
* nonexistent organization (404) / pending organization (403) / join code (403)
* institution creation (status='pending', is_active=False) + join request (pending)
* initial institution admin (GoTrue account + public.users + role 'admin')
* institution-scoped role grant — NO organization-wide scope; access fails closed
* duplicate institution code (case-insensitive; global unique constraint) and
  duplicate admin email
* invalid email / password / missing required fields (422 VALIDATION_ERROR)
* password never exposed in the response, never stored in application tables
* role/scope/organization-id fields can never be supplied by the client
  (extra="forbid") — the resolved organization cannot be overridden
* partial failure compensation (no orphan users / auth accounts)
* Phase 6.13.1 / 6.13.2 regression markers (existing endpoints, repo helpers,
  authorization constants untouched)

The Supabase Auth (GoTrue) client and the service-role PostgREST client are
mocked; no live database or auth service is contacted.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import tenancy as tenancy_repo
from app.services import student_registration as student_svc
from app.services import tenancy as tenancy_svc

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Stable identifiers
# ---------------------------------------------------------------------------

ORG_ID = "a0000000-0000-0000-0000-000000000001"
INST_ID = "e0000000-0000-0000-0000-000000000001"
JR_ID = "f0000000-0000-0000-0000-000000000001"
AUTH_ID = "b0000000-0000-0000-0000-000000000001"
USER_ID = "c0000000-0000-0000-0000-000000000001"
ROLE_ID = "d0000000-0000-0000-0000-000000000001"


def _payload(**over):
    body = {
        "name": "Imphal Polytechnic",
        "institution_code": "IMPHAL",
        "organization_code": "ACMEORG",
        "join_code": "ORGJOBCODE12",
        "official_email": "info@imphal.example.com",
        "location": "Imphal",
        "admin_email": "admin@imphal.example.com",
        "admin_password": "secret123",
        "admin_first_name": "Imphal",
        "admin_last_name": "Admin",
    }
    body.update(over)
    return body


def _org_row(**over):
    row = {
        "organization_id": ORG_ID,
        "name": "Acme Education Group",
        "organization_code": "ACMEORG",
        "official_email": "org@acme.example.com",
        "contact_information": "contact@acme.example.com",
        "status": "active",
        "join_code": "ORGJOBCODE12",
        "created_at": "2026-09-17T00:00:00Z",
        "updated_at": "2026-09-17T00:00:00Z",
    }
    row.update(over)
    return row


def _inst_row(**over):
    row = {
        "institution_id": INST_ID,
        "organization_id": ORG_ID,
        "name": "Imphal Polytechnic",
        "code": "IMPHAL",
        "email": "info@imphal.example.com",
        "status": "active",
        "is_active": True,
    }
    row.update(over)
    return row


def _user_row(**over):
    row = {
        "user_id": USER_ID,
        "auth_user_id": AUTH_ID,
        "email": "admin@imphal.example.com",
        "first_name": "Imphal",
        "last_name": "Admin",
    }
    row.update(over)
    return row


def _role_row():
    return {"role_id": ROLE_ID, "name": "admin"}


# ---------------------------------------------------------------------------
# Fake service-role client (per-table reads/writes answered from state)
# ---------------------------------------------------------------------------


class _Q:
    """Minimal chainable query builder returning canned rows."""

    def __init__(self, single=None, rows=None):
        self._single = single
        self._rows = rows if rows is not None else []

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def ilike(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def maybe_single(self):
        return self

    def insert(self, *a, **k):
        return self

    def update(self, *a, **k):
        return self

    def upsert(self, *a, **k):
        return self

    def delete(self, *a, **k):
        return self

    def execute(self):
        return MagicMock(data=self._single)


class _OrganizationsTable(_Q):
    """organizations table: case-insensitive code lookup (no insert needed)."""

    def __init__(self, state):
        super().__init__(single=state.get("organization"))
        self._state = state

    def ilike(self, column, value):
        if column == "organization_code":
            org = self._state.get("organization")
            if org is not None and str(value).strip().lower() == str(
                org.get("organization_code", "")
            ).strip().lower():
                self._single = org
            else:
                self._single = None
        return self


class _InstitutionsTable(_Q):
    """institutions table: code-exists lookup + pending insert (+ failure)."""

    def __init__(self, state):
        super().__init__(single=state.get("institution_code_taken_row"))
        self._state = state

    def eq(self, column, value):
        if column == "code":
            self._single = self._state.get("institution_code_taken_row")
        return self

    def insert(self, row, *a, **k):
        if self._state.get("institution_insert_error"):
            raise RuntimeError("institutions insert failed")
        created = dict(row)
        created.setdefault("institution_id", INST_ID)
        self._state.setdefault("inserted_institutions", []).append(dict(created))
        self._single = [created]
        return self


class _JoinRequestsTable(_Q):
    """institution_join_requests table: pending join request insert (+ failure)."""

    def __init__(self, state):
        super().__init__(single=state.get("existing_join_request"))
        self._state = state

    def insert(self, row, *a, **k):
        if self._state.get("join_request_insert_error"):
            raise RuntimeError("institution_join_requests insert failed")
        created = dict(row)
        created.setdefault("join_request_id", JR_ID)
        self._state.setdefault("inserted_join_requests", []).append(dict(created))
        self._single = [created]
        return self


class _UsersTable(_Q):
    """public.users table: email lookup + insert/delete compensation."""

    def __init__(self, state):
        super().__init__(single=state.get("existing_user"))
        self._state = state

    def eq(self, column, value):
        if column == "email":
            existing = self._state.get("existing_user")
            if existing is not None and str(value).strip().lower() == str(
                existing.get("email", "")
            ).strip().lower():
                self._single = existing
            else:
                self._single = None
        return self

    def insert(self, row, *a, **k):
        if self._state.get("users_insert_error"):
            raise RuntimeError("users insert failed")
        created = dict(row)
        created.setdefault("user_id", USER_ID)
        self._state.setdefault("inserted_users", []).append(dict(created))
        self._single = [created]
        return self

    def delete(self, *a, **k):
        self._state["deleted_users"] = self._state.get("deleted_users", 0) + 1
        return self


class _UserRolesTable(_Q):
    """user_roles table: role + scope assignment (+ failure injection)."""

    def __init__(self, state):
        super().__init__(single=state.get("user_roles_row"))
        self._state = state

    def upsert(self, row, *a, **k):
        if self._state.get("user_roles_insert_error"):
            raise RuntimeError("user_roles insert failed")
        created = dict(row)
        self._state.setdefault("assigned_roles", []).append(dict(created))
        self._single = [created]
        return self


class _RolesTable(_Q):
    """roles lookup table."""

    def __init__(self, state):
        super().__init__(single=state.get("role_row"))
        self._state = state

    def eq(self, column, value):
        if column == "name":
            self._single = self._state.get("role_row")
        return self


def _db(state):
    """Fake service-role client answering per-table reads/writes from state."""
    db = MagicMock()

    def table(name):
        if name == "organizations":
            return _OrganizationsTable(state)
        if name == "institutions":
            return _InstitutionsTable(state)
        if name == "institution_join_requests":
            return _JoinRequestsTable(state)
        if name == "users":
            return _UsersTable(state)
        if name == "user_roles":
            return _UserRolesTable(state)
        if name == "roles":
            return _RolesTable(state)
        return _Q(single=None)

    db.table.side_effect = table
    return db


# ---------------------------------------------------------------------------
# Fake Supabase Auth (GoTrue) clients + request runner
# ---------------------------------------------------------------------------


def _auth_ok(auth_id=AUTH_ID):
    """Successful sign_up response."""
    created = MagicMock()
    created.user = MagicMock(id=auth_id, email="admin@imphal.example.com")
    anon = MagicMock()
    anon.auth.sign_up.return_value = created
    return anon


def _auth_fail():
    """sign_up raises AuthApiError (duplicate auth email)."""
    from supabase_auth.errors import AuthApiError

    anon = MagicMock()
    anon.auth.sign_up.side_effect = AuthApiError(
        "Email already registered", 400, "email_exists"
    )
    return anon


def _run(payload, state, auth_client=None):
    """POST the institution registration payload with every external client mocked.

    * tenancy service ``get_admin_client`` -> fake PostgREST client
    * student_registration ``create_supabase_client`` -> fake GoTrue client
      (recorded on the state as ``_auth_client`` for signup assertions)
    * student_registration ``get_admin_client`` -> MagicMock (used only by the
      best-effort ``_try_delete_auth_user`` compensation; recorded so tests can
      assert the auth account was deleted)
    """
    fake_admin = MagicMock()
    state["_fake_admin_client"] = fake_admin
    auth = auth_client or _auth_ok()
    state["_auth_client"] = auth
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patch.object(student_svc, "get_admin_client", return_value=fake_admin),
        patch.object(student_svc, "create_supabase_client", return_value=auth),
    ):
        return client.post("/api/v1/institutions/register", json=payload)


def _base_state():
    return {
        "organization": _org_row(),
        "existing_user": None,
        "institution_code_taken_row": None,
        "role_row": _role_row(),
    }


# ============================================================================
# 1-2. Success path + existing-organization resolution
# ============================================================================


def test_successful_registration_returns_201_pending():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["institution_code"] == "IMPHAL"
    assert body["organization_id"] == ORG_ID
    assert body["institution_id"] == INST_ID
    assert body["admin_user_id"] == USER_ID
    assert body["email"] == "admin@imphal.example.com"


def test_institution_bound_to_server_resolved_organization():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    insts = state["inserted_institutions"]
    assert len(insts) == 1
    # The organization id comes from the SERVER-RESOLVED row, never the client.
    assert insts[0]["organization_id"] == ORG_ID


def test_case_insensitive_organization_code_resolution():
    state = _base_state()
    resp = _run(_payload(organization_code="  acmeorg  "), state)
    assert resp.status_code == 201, resp.text
    assert state["inserted_institutions"][0]["organization_id"] == ORG_ID


def test_case_variants_of_same_organization_code_resolve():
    for variant in ("AcmeOrg", "ACMEORG", "acmeorg"):
        state = _base_state()
        resp = _run(_payload(organization_code=variant), state)
        assert resp.status_code == 201, f"{variant}: {resp.text}"
        assert state["inserted_institutions"][0]["organization_id"] == ORG_ID


def test_pending_institution_row_created():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    inst = state["inserted_institutions"][0]
    assert inst["status"] == "pending"
    assert inst["is_active"] is False
    assert inst["code"] == "IMPHAL"


def test_pending_join_request_created():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    jrs = state["inserted_join_requests"]
    assert len(jrs) == 1
    assert jrs[0]["status"] == "pending"
    assert jrs[0]["organization_id"] == ORG_ID
    assert jrs[0]["institution_id"] == INST_ID
    assert jrs[0]["requested_institution_code"] == "IMPHAL"
    assert jrs[0]["requested_by_user_id"] == USER_ID


# ============================================================================
# 3-4. Organization resolution failures
# ============================================================================


def test_nonexistent_organization_rejected():
    state = _base_state()
    state["organization"] = None
    resp = _run(_payload(), state)
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_NOT_FOUND"
    # Nothing was created: no users row, no auth account, no institution.
    assert state.get("inserted_users") is None
    assert state.get("inserted_institutions") is None
    assert state.get("assigned_roles") is None
    assert state["_auth_client"].auth.sign_up.called is False


def test_pending_organization_not_accepting_institution_requests():
    state = _base_state()
    state["organization"] = _org_row(status="pending")
    resp = _run(_payload(), state)
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_NOT_ACCEPTING_REQUESTS"
    assert state.get("inserted_institutions") is None


def test_wrong_join_code_rejected():
    state = _base_state()
    resp = _run(_payload(join_code="WRONGCODE9999"), state)
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "INVALID_JOIN_CODE"
    assert state.get("inserted_users") is None
    assert state.get("inserted_institutions") is None


def test_missing_join_code_when_required_rejected():
    state = _base_state()
    payload = _payload()
    del payload["join_code"]
    resp = _run(payload, state)
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "INVALID_JOIN_CODE"


def test_correct_join_code_accepted_with_surrounding_whitespace():
    # The join code is server-issued and compared exactly (constant-time);
    # surrounding whitespace is stripped, case must match.
    state = _base_state()
    resp = _run(_payload(join_code=" ORGJOBCODE12 "), state)
    assert resp.status_code == 201, resp.text


def test_join_code_not_required_when_organization_has_none():
    state = _base_state()
    state["organization"] = _org_row(join_code=None)
    payload = _payload()
    del payload["join_code"]
    resp = _run(payload, state)
    assert resp.status_code == 201, resp.text


# ============================================================================
# 5-7. Initial institution admin + pending access boundary
# ============================================================================


def test_initial_admin_created_via_supabase_auth():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    # Exactly one GoTrue signup and one public.users link row.
    assert state["_auth_client"].auth.sign_up.call_count == 1
    users = state["inserted_users"]
    assert len(users) == 1
    assert users[0]["email"] == "admin@imphal.example.com"
    assert users[0]["first_name"] == "Imphal"
    assert users[0]["last_name"] == "Admin"


def test_admin_role_assigned_institution_scoped_server_side():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    assigned = state["assigned_roles"]
    assert len(assigned) == 1
    assert assigned[0]["role_id"] == ROLE_ID
    # INSTITUTION scope (not organization-wide), bound to the resolved org.
    assert assigned[0]["scope_type"] == "institution"
    assert assigned[0]["scope_id"] == INST_ID
    assert assigned[0]["scope_organization_id"] == ORG_ID


def test_pending_institution_access_fails_closed():
    # The pending institution is structurally unavailable: the existing
    # activation guard rejects anything that is not ACTIVE + is_active, so the
    # institution admin has no usable institution access before approval.
    with pytest.raises(Exception) as excinfo:
        tenancy_svc._assert_institution_active(
            {"status": "pending", "is_active": False}
        )
    assert getattr(excinfo.value, "code", None) == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"


# ============================================================================
# 8-10. Duplicates (race-safe uniqueness contract)
# ============================================================================


def test_duplicate_institution_code_rejected_case_insensitive():
    state = _base_state()
    state["institution_code_taken_row"] = _inst_row()
    resp = _run(_payload(institution_code="imphal"), state)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "INSTITUTION_CODE_TAKEN"
    assert state.get("inserted_users") is None
    assert state.get("inserted_institutions") is None


def test_duplicate_institution_code_within_same_organization():
    state = _base_state()
    # The same organization already has this institution code.
    state["institution_code_taken_row"] = _inst_row(organization_id=ORG_ID)
    resp = _run(_payload(), state)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "INSTITUTION_CODE_TAKEN"


def test_institution_code_globally_unique_across_organizations():
    # The existing schema (institutions_code_key UNIQUE (code)) is GLOBAL:
    # Organization A + IMPHAL and Organization B + IMPHAL cannot both exist.
    # The service enforces this via the existing global code-exists check.
    state = _base_state()
    other_org = "b1000000-0000-0000-0000-000000000002"
    state["institution_code_taken_row"] = _inst_row(organization_id=other_org)
    resp = _run(_payload(), state)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "INSTITUTION_CODE_TAKEN"


def test_duplicate_institution_code_wins_over_duplicate_email():
    state = _base_state()
    state["institution_code_taken_row"] = _inst_row()
    state["existing_user"] = _user_row()
    resp = _run(_payload(), state)
    assert resp.status_code == 409, resp.text
    # The institution-code uniqueness check runs first (committed contract).
    assert resp.json()["error"]["code"] == "INSTITUTION_CODE_TAKEN"


def test_duplicate_admin_email_rejected():
    state = _base_state()
    state["existing_user"] = _user_row()
    resp = _run(_payload(), state)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert state.get("inserted_institutions") is None
    assert state.get("assigned_roles") is None
    assert state.get("inserted_join_requests") is None


def test_duplicate_email_detected_case_insensitively():
    state = _base_state()
    state["existing_user"] = _user_row(email="ADMIN@IMPHAL.example.com")
    resp = _run(_payload(admin_email="admin@IMPHAL.example.com"), state)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_duplicate_admin_email_rejected_by_gotrue_race():
    # Pre-check passes, but GoTrue reports the email exists (race window):
    # surfaces as the project's conflict convention with no partial state.
    state = _base_state()
    resp = _run(_payload(), state, auth_client=_auth_fail())
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert state.get("inserted_users") is None
    assert state.get("inserted_institutions") is None


# ============================================================================
# 11-13. Validation (email / password / required fields)
# ============================================================================


def test_invalid_admin_email_rejected():
    state = _base_state()
    resp = _run(_payload(admin_email="not-an-email"), state)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_official_email_rejected():
    state = _base_state()
    resp = _run(_payload(official_email="no-at-sign"), state)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_short_password_rejected():
    state = _base_state()
    resp = _run(_payload(admin_password="short"), state)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_empty_password_rejected():
    state = _base_state()
    resp = _run(_payload(admin_password=""), state)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_blank_required_text_fields_rejected():
    for field in ("name", "institution_code", "organization_code"):
        state = _base_state()
        resp = _run(_payload(**{field: "   "}), state)
        assert resp.status_code == 422, f"{field}: {resp.text}"
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "institution_code",
        "organization_code",
        "official_email",
        "admin_email",
        "admin_password",
        "admin_first_name",
        "admin_last_name",
    ],
)
def test_missing_required_fields(field):
    payload = _payload()
    del payload[field]
    state = _base_state()
    resp = _run(payload, state)
    assert resp.status_code == 422, f"missing {field}: {resp.text}"
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ============================================================================
# 14 + security. Password safety / client cannot choose privileges
# ============================================================================


def test_password_not_exposed_in_response():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    assert "secret123" not in resp.text
    body = resp.json()
    assert "password" not in body
    assert "access_token" not in body
    assert "token" not in body


def test_password_never_stored_in_application_tables():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    # The public.users row carries no credential material.
    for user in state["inserted_users"]:
        assert "password" not in user
    for inst in state["inserted_institutions"]:
        assert "password" not in inst
    for jr in state["inserted_join_requests"]:
        assert "password" not in jr
    # The password went ONLY to Supabase Auth (GoTrue), exactly once.
    call = state["_auth_client"].auth.sign_up.call_args
    assert call.args[0]["password"] == "secret123"
    assert call.args[0]["email"] == "admin@imphal.example.com"


def test_client_cannot_supply_role_scope_or_status():
    for extra in (
        {"role": "admin"},
        {"scope_type": "organization"},
        {"scope_id": ORG_ID},
        {"status": "active"},
        {"is_active": True},
        {"requested_role": "admin"},
    ):
        state = _base_state()
        resp = _run({**_payload(), **extra}, state)
        assert resp.status_code == 422, f"{extra}: {resp.text}"
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
        # Nothing was created: the payload never reached the service.
        assert state.get("inserted_institutions") is None
        assert state.get("assigned_roles") is None


def test_client_cannot_override_resolved_organization_id():
    # The payload has no organization-id field at all: an attempt to bind the
    # institution to a different organization is rejected before the service.
    state = _base_state()
    resp = _run(
        {**_payload(), "organization_id": "b2000000-0000-0000-0000-000000000009"},
        state,
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert state.get("inserted_institutions") is None


# ============================================================================
# 15. Partial failure / compensation (no orphan state)
# ============================================================================


def test_auth_failure_creates_nothing():
    state = _base_state()
    resp = _run(_payload(), state, auth_client=_auth_fail())
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert state.get("inserted_users") is None
    assert state.get("inserted_institutions") is None
    assert state.get("inserted_join_requests") is None
    assert state.get("assigned_roles") is None


def test_users_insert_failure_compensates_auth_account():
    state = _base_state()
    state["users_insert_error"] = True
    resp = _run(_payload(), state)
    assert resp.status_code >= 400, resp.text
    # No institution row was created...
    assert state.get("inserted_institutions") is None
    # ...and the freshly created Supabase auth account was deleted.
    assert state["_fake_admin_client"].auth.admin.delete_user.called


def test_institution_insert_failure_compensates_user_and_auth():
    state = _base_state()
    state["institution_insert_error"] = True
    resp = _run(_payload(), state)
    assert resp.status_code >= 400, resp.text
    # The public.users row was compensated (deleted)...
    assert state.get("deleted_users", 0) >= 1
    # ...and the auth account was deleted.
    assert state["_fake_admin_client"].auth.admin.delete_user.called
    # No role was granted on a failed registration.
    assert state.get("assigned_roles") is None


def test_role_assignment_failure_compensates_user_and_auth():
    state = _base_state()
    state["user_roles_insert_error"] = True
    resp = _run(_payload(), state)
    assert resp.status_code >= 400, resp.text
    # The user was rolled back: no registered user without a role lingers.
    assert state.get("deleted_users", 0) >= 1
    assert state["_fake_admin_client"].auth.admin.delete_user.called
    # The institution insert itself was attempted exactly once (its cleanup on
    # failure relies on the DB unique constraint / admin tooling; no second
    # attempt is made — same compensation boundary as Phase 6.13.2).
    assert len(state.get("inserted_institutions", [])) == 1


def test_join_request_insert_failure_compensates_user_and_auth():
    state = _base_state()
    state["join_request_insert_error"] = True
    resp = _run(_payload(), state)
    assert resp.status_code >= 400, resp.text
    assert state.get("deleted_users", 0) >= 1
    assert state["_fake_admin_client"].auth.admin.delete_user.called


# ============================================================================
# 16-17. Tenant isolation + Phase 6.13.1 / 6.13.2 regression markers
# ============================================================================


def test_tenant_isolation_scope_shape():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    # The institution is tenant-bound to exactly one organization and the role
    # grant is institution-scoped inside that organization — never org-wide,
    # never platform, never client-chosen.
    inst = state["inserted_institutions"][0]
    role = state["assigned_roles"][0]
    assert inst["organization_id"] == ORG_ID
    assert role["scope_type"] == "institution"
    assert role["scope_organization_id"] == ORG_ID
    assert role["scope_id"] == inst["institution_id"]


def test_phase_6_13_1_and_6_13_2_endpoints_still_exist():
    # openapi() materializes this FastAPI version's lazily-included routers.
    paths = set(app.openapi()["paths"].keys())
    assert "/api/v1/registration" in paths  # Phase 6.3 student registration
    assert "/api/v1/organizations/register" in paths  # Phase 6.13.2
    assert "/api/v1/institutions/register" in paths  # Phase 6.13.3 (new)


def test_existing_tenancy_repo_helpers_still_available():
    # The registration flow REUSES the existing Phase 6.13.1 primitives.
    assert callable(tenancy_repo.get_organization_by_code)
    assert callable(tenancy_repo.institution_code_exists)
    assert callable(tenancy_repo.insert_institution)
    assert callable(tenancy_repo.insert_join_request)
    assert callable(tenancy_repo.get_user_by_email)
    assert callable(tenancy_repo.assign_user_role_scope)
    assert callable(tenancy_repo.get_role_by_name)


def test_existing_authorization_service_unchanged():
    from app.services import authorization as authz

    assert callable(authz.resolve_authorization_context)
    assert authz.ORGANIZATION == "organization"
    assert authz.INSTITUTION == "institution"
    assert authz.PLATFORM == "platform"
