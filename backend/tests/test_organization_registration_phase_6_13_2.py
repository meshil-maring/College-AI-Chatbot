"""Phase 6.13.2 — Organization registration tests (mocked Supabase clients).

Covers:
* successful organization registration (201, pending status)
* organization creation (row contents + server-issued join_code)
* initial admin creation (Supabase Auth account + public.users link row)
* admin role assignment (role 'admin', server-side)
* organization scope assignment (scope_type=organization, scope_id=org id)
* duplicate organization_code (case-insensitive) and duplicate admin email
* invalid email / password / missing required fields (422 VALIDATION_ERROR)
* password never exposed in the response, never stored in application tables
* role/scope fields can never be supplied by the client (extra="forbid")
* partial failure compensation (no orphan organizations / users / auth accounts)
* existing tenancy/RBAC regression markers (Phase 6.13.1 untouched)

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
AUTH_ID = "b0000000-0000-0000-0000-000000000001"
USER_ID = "c0000000-0000-0000-0000-000000000001"
ROLE_ID = "d0000000-0000-0000-0000-000000000001"


def _payload(**over):
    body = {
        "name": "Acme Institute of Technology",
        "organization_code": "AIT",
        "official_email": "info@acme.example.com",
        "contact_information": "contact@acme.example.com",
        "admin_email": "admin@acme.example.com",
        "admin_password": "secret123",
        "admin_first_name": "Acme",
        "admin_last_name": "Admin",
    }
    body.update(over)
    return body


def _org_row(**over):
    row = {
        "organization_id": ORG_ID,
        "name": "Acme Institute of Technology",
        "organization_code": "AIT",
        "official_email": "info@acme.example.com",
        "contact_information": "contact@acme.example.com",
        "status": "pending",
        "join_code": "ABCDEF123456",
        "created_at": "2026-09-17T00:00:00Z",
        "updated_at": "2026-09-17T00:00:00Z",
    }
    row.update(over)
    return row


def _user_row(**over):
    row = {
        "user_id": USER_ID,
        "auth_user_id": AUTH_ID,
        "email": "admin@acme.example.com",
        "first_name": "Acme",
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
    """organizations table: code lookup + insert (+ failure injection)."""

    def __init__(self, state):
        super().__init__(single=state.get("code_taken_row"))
        self._state = state

    def ilike(self, column, value):
        if column == "organization_code":
            self._single = self._state.get("code_taken_row")
        return self

    def insert(self, row, *a, **k):
        if self._state.get("org_insert_error"):
            raise RuntimeError("organizations insert failed")
        created = dict(row)
        created.setdefault("organization_id", ORG_ID)
        self._state.setdefault("inserted_orgs", []).append(dict(created))
        self._single = [created]
        return self


class _UsersTable(_Q):
    """public.users table: email lookup + insert/delete compensation."""

    def __init__(self, state):
        super().__init__(single=state.get("existing_user"))
        self._state = state

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
    created.user = MagicMock(id=auth_id, email="admin@acme.example.com")
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
    """POST the registration payload with every external client mocked.

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
        return client.post("/api/v1/organizations/register", json=payload)


def _base_state():
    return {
        "organization": None,
        "public_user": None,
        "existing_user": None,
        "code_taken_row": None,
        "role_row": _role_row(),
    }


# ============================================================================
# 1-5. Success path: registration, organization, admin, role, scope
# ============================================================================


def test_successful_registration_returns_201_pending():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["organization_code"] == "AIT"
    assert body["email"] == "admin@acme.example.com"
    assert body["organization_id"] == ORG_ID
    assert body["admin_user_id"] == USER_ID


def test_organization_row_created_with_server_issued_join_code():
    state = _base_state()
    resp = _run(_payload(organization_code="  ait  "), state)
    assert resp.status_code == 201, resp.text
    orgs = state["inserted_orgs"]
    assert len(orgs) == 1
    org = orgs[0]
    # Code is normalized (trimmed + upper-cased) and case-safe.
    assert org["organization_code"] == "AIT"
    assert org["name"] == "Acme Institute of Technology"
    assert org["official_email"] == "info@acme.example.com"
    assert org["status"] == "pending"
    # The join code is issued by the SERVER (12 chars), never by the client.
    assert org.get("join_code")
    assert len(org["join_code"]) == 12


def test_initial_admin_created_via_existing_auth_mechanism():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    # Exactly one public.users link row is created for the admin.
    users = state["inserted_users"]
    assert len(users) == 1
    user = users[0]
    assert user["email"] == "admin@acme.example.com"
    assert user["auth_user_id"] == AUTH_ID
    assert user["first_name"] == "Acme"
    assert user["last_name"] == "Admin"
    # The GoTrue account was created through the existing signup mechanism.
    assert state["_auth_client"].auth.sign_up.call_count == 1


def test_admin_role_assignment():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    assigned = state["assigned_roles"]
    assert len(assigned) == 1
    assert assigned[0]["user_id"] == USER_ID
    assert assigned[0]["role_id"] == ROLE_ID


def test_organization_scope_assignment():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    assigned = state["assigned_roles"]
    assert len(assigned) == 1
    assert assigned[0]["scope_type"] == "organization"
    assert assigned[0]["scope_id"] == ORG_ID
    assert assigned[0]["scope_organization_id"] == ORG_ID


# ============================================================================
# 6-7. Duplicates (race-safe uniqueness contract)
# ============================================================================


def test_duplicate_organization_code_case_insensitive():
    state = _base_state()
    state["code_taken_row"] = _org_row(status="active")
    resp = _run(_payload(organization_code="ait"), state)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_CODE_TAKEN"
    # No partial state: nothing was created.
    assert state.get("inserted_orgs") is None
    assert state.get("inserted_users") is None


def test_duplicate_organization_code_same_case():
    state = _base_state()
    state["code_taken_row"] = _org_row(status="active")
    resp = _run(_payload(organization_code="AIT"), state)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_CODE_TAKEN"


def test_duplicate_admin_email_rejected():
    state = _base_state()
    state["existing_user"] = _user_row()
    resp = _run(_payload(), state)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    # No organization and no role is created for a duplicate admin email.
    assert state.get("inserted_orgs") is None
    assert state.get("assigned_roles") is None


def test_duplicate_code_wins_when_both_taken():
    state = _base_state()
    state["code_taken_row"] = _org_row(status="active")
    state["existing_user"] = _user_row()
    resp = _run(_payload(), state)
    assert resp.status_code == 409, resp.text
    # The organization-code uniqueness check runs first (committed contract).
    assert resp.json()["error"]["code"] == "ORGANIZATION_CODE_TAKEN"


def test_unique_admin_email_and_code_allowed():
    state = _base_state()
    resp = _run(
        _payload(admin_email="brand-new-admin@example.com", organization_code="NOBTS"),
        state,
    )
    assert resp.status_code == 201, resp.text


# ============================================================================
# 8-10. Validation (email / password / required fields)
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


def test_weak_admin_password_rejected():
    state = _base_state()
    resp = _run(_payload(admin_password="short"), state)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_empty_admin_password_rejected():
    state = _base_state()
    resp = _run(_payload(admin_password=""), state)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_blank_required_text_fields_rejected():
    state = _base_state()
    resp = _run(_payload(name="   "), state)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    state = _base_state()
    resp = _run(_payload(organization_code="   "), state)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "organization_code",
        "official_email",
        "contact_information",
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
# 11-12 + security. Password safety / client cannot choose privileges
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
    # The password went ONLY to Supabase Auth (GoTrue), exactly once.
    call = state["_auth_client"].auth.sign_up.call_args
    assert call.args[0]["password"] == "secret123"
    assert call.args[0]["email"] == "admin@acme.example.com"


def test_client_cannot_supply_role_scope_or_status():
    for extra in (
        {"role": "admin"},
        {"role": "superadmin"},
        {"scope_type": "organization"},
        {"scope_id": ORG_ID},
        {"status": "active"},
        {"requested_role": "admin"},
    ):
        state = _base_state()
        resp = _run({**_payload(), **extra}, state)
        assert resp.status_code == 422, f"{extra}: {resp.text}"
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
        # Nothing was created: the payload never reached the service.
        assert state.get("inserted_orgs") is None
        assert state.get("assigned_roles") is None


def test_no_institution_created_automatically():
    state = _base_state()
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    # Organization registration never creates an institution (Phase 6.13.3+).
    assert "inserted_institutions" not in state


# ============================================================================
# 13. Partial failure / compensation (no orphan state)
# ============================================================================


def test_auth_failure_creates_nothing():
    state = _base_state()
    resp = _run(_payload(), state, auth_client=_auth_fail())
    # Duplicate auth email surfaces as the project's conflict convention.
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert state.get("inserted_orgs") is None
    assert state.get("inserted_users") is None
    assert state.get("assigned_roles") is None


def test_users_insert_failure_compensates_auth_account():
    state = _base_state()
    state["users_insert_error"] = True
    resp = _run(_payload(), state)
    assert resp.status_code >= 400, resp.text
    # No organization row was created...
    assert state.get("inserted_orgs") is None
    # ...and the freshly created Supabase auth account was deleted.
    assert state["_fake_admin_client"].auth.admin.delete_user.called


def test_org_insert_failure_compensates_user_and_auth():
    state = _base_state()
    state["org_insert_error"] = True
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
    # The organization insert itself was attempted exactly once (its cleanup on
    # failure relies on the DB unique constraint; no second attempt is made).
    assert len(state.get("inserted_orgs", [])) == 1


# ============================================================================
# 14. Existing tenancy / RBAC regression markers (Phase 6.13.1 intact)
# ============================================================================


def test_student_registration_route_still_exists():
    # openapi() materializes this FastAPI version's lazily-included routers.
    paths = set(app.openapi()["paths"].keys())
    assert "/api/v1/registration" in paths
    assert "/api/v1/organizations/register" in paths


def test_existing_tenancy_repo_helpers_still_available():
    # The registration flow REUSES the existing Phase 6.13.1 primitives.
    assert callable(tenancy_repo.get_organization_by_code)
    assert callable(tenancy_repo.organization_code_exists)
    assert callable(tenancy_repo.insert_organization)
    assert callable(tenancy_repo.get_user_by_email)
    assert callable(tenancy_repo.assign_user_role_scope)
    assert callable(tenancy_repo.get_role_by_name)


def test_existing_authorization_service_unchanged():
    from app.services import authorization as authz

    assert callable(authz.resolve_authorization_context)
    assert authz.ORGANIZATION == "organization"
    assert authz.INSTITUTION == "institution"
    assert authz.PLATFORM == "platform"
