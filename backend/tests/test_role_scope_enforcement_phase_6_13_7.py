"""Phase 6.13.7 — Role + Scope Enforcement tests.

Server-side authorization is determined ONLY by the trusted chain:

    JWT sub -> users.user_id -> user_roles(role, scope_type, scope_id,
    scope_organization_id) [+ students.institution_id for tenant-bound
    accounts] -> tenant lifecycle (institutions/organizations.status)

Covered areas (mapped to the phase brief):

      1. organization-scoped admin access
      2. organization admin cannot access another organization
      3. institution-scoped admin access
      4. institution admin cannot access another institution
      5. student institution isolation
      6. faculty institution isolation
      7. staff institution isolation
      8. correct role enforcement
      9. unauthorized role denied
     10. client role injection denied
     11. client scope injection denied
     12. client institution ID substitution denied
     13. client organization ID substitution denied
     14. missing role denied
     15. missing scope denied
     16. invalid scope denied
     17. inactive institution denied
     18. pending institution denied
     19. rejected institution denied
     20. inactive/rejected organization denied
     21. cross-tenant resource access denied
     22. valid same-tenant resource access allowed
     23. existing Phase 6 RBAC regression
     24. Phase 6.13.1-6.13.6 regression

All Supabase/GoTrue clients are mocked — no live services. Protected
ENDPOINTS are exercised (admin, ingestion pipeline, chat, student /me,
tenancy decisions), not only helper functions.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.admin import _ADMIN, _APPROVAL
from app.api.ingestion import _INGEST_ALLOWED
from app.core.errors import AppError
from app.core.security import (
    assert_tenant_object,
    get_current_user,
    require_roles,
    scope_tenant,
)
from app.main import app
from app.repositories import tenancy as tenancy_repo
from app.services import authorization as authz
from app.services import tenancy as tenancy_svc
from app.services.student_auth import SafeAuthFailure

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Stable identifiers
# ---------------------------------------------------------------------------

ORG_A = "a0000000-0000-0000-0000-00000000000a"
ORG_B = "a0000000-0000-0000-0000-00000000000b"
INST_A = "b0000000-0000-0000-0000-00000000000a"
INST_B = "b0000000-0000-0000-0000-00000000000b"
TENANT_A = INST_A  # institution A is tenant A for the academic endpoints
TENANT_B = INST_B
JR_A = "d0000000-0000-0000-0000-000000000001"
MR_A = "e1000000-0000-0000-0000-000000000001"
KS_A = "40000000-0000-0000-0000-00000000000a"
KS_B = "40000000-0000-0000-0000-00000000000b"
RUN_ID = "a0000000-0000-0000-0000-0000000000f1"
DV_ID = "d0000000-0000-0000-0000-0000000000f1"
STUDENT_A = "30000000-0000-0000-0000-000000000151"
ROLE_ID = "e0000000-0000-0000-0000-000000000001"
USER_ADMIN = "c0000000-0000-0000-0000-000000000001"
ORG_ADMIN = "c0000000-0000-0000-0000-000000000002"
INST_ADMIN = "c0000000-0000-0000-0000-000000000003"

# ---------------------------------------------------------------------------
# current_user fixtures (shape locked by get_current_user)
# ---------------------------------------------------------------------------


def _user(tenant=None, roles=("admin",), user_id=None):
    return {
        "user_id": user_id or str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "phase6137@example.com",
        "roles": list(roles),
        "institution_id": tenant,
    }


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Authorization-context resolution against mocked user_roles rows
# ---------------------------------------------------------------------------


def _role_row(scope_type, scope_id, org_id, role="admin"):
    return {
        "role_id": ROLE_ID,
        "role_name": role,
        "is_active": True,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "scope_organization_id": org_id,
    }


def _resolve(rows, current_user=None):
    """Run resolve_authorization_context for real against mocked role rows."""
    cu = current_user or {"user_id": USER_ADMIN, "institution_id": None}
    with (
        patch(
            "app.services.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo,
            "get_institution_organization",
            return_value=UUID(ORG_A),
        ),
    ):
        return authz.resolve_authorization_context(cu)


def _authz_patches(user_id: str, rows: list):
    """Mock the authorization-context sources (same seams as Phase 6.13.4)."""
    return (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo,
            "get_institution_organization",
            return_value=UUID(ORG_A),
        ),
    )


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
        self._payload = None
        self._deleting = False

    def select(self, *a, **k):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
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

    def upsert(self, payload, on_conflict=None):
        # Emulate PostgREST upsert: update matching rows, else insert.
        self._payload = payload
        self._upserting = True
        return self

    def delete(self):
        self._deleting = True
        return self

    def _rows(self):
        rows = self._state.get(self._name, {})
        if isinstance(rows, dict):
            rows = list(rows.values())
        return [
            row
            for row in rows
            if all(
                str(row.get(column, "")).lower() == str(value).lower()
                for column, value in self._filters
            )
        ]

    def execute(self):
        if self._deleting:
            for row in self._rows():
                table = self._state.setdefault(self._name, {})
                for key, value in list(table.items()):
                    if value is row:
                        table.pop(key, None)
            return SimpleNamespace(data=[])
        if self._payload is not None:
            updated = []
            for row in self._rows():
                row.update(self._payload)
                if self._name == "institutions":
                    # Emulate the trg_phase613_institutions_status trigger.
                    row["is_active"] = row.get("status") == "active"
                self._state.setdefault("updates", []).append(
                    (self._name, dict(row))
                )
                updated.append(row)
            if updated:
                return SimpleNamespace(data=updated)
            if getattr(self, "_upserting", False) or self._filters == []:
                # Upsert with no matching row (or unfiltered insert): create it.
                created = dict(self._payload)
                table = self._state.setdefault(self._name, {})
                if isinstance(table, list):
                    table.append(created)
                else:
                    table.setdefault(created.get("user_id", str(uuid4())), created)
                return SimpleNamespace(data=[created])
            return SimpleNamespace(data=[])
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
        "name": "Acme Org",
        "organization_code": "ACME" if org_id == ORG_A else "BETA",
        "official_email": "info@acme.example.com",
        "contact_information": "contact@acme.example.com",
        "status": status,
        "join_code": None,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z",
    }


def _inst_row(inst_id=INST_A, org_id=ORG_A, status="pending", is_active=False):
    return {
        "institution_id": inst_id,
        "organization_id": org_id,
        "name": "Imphal College",
        "code": "IMPHAL" if inst_id == INST_A else "BETACOLLEGE",
        "email": None,
        "address": None,
        "city": None,
        "state": None,
        "country": None,
        "status": status,
        "is_active": is_active,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z",
    }


def _jr_row(join_request_id=JR_A, org_id=ORG_A, inst_id=INST_A, status="pending"):
    return {
        "join_request_id": join_request_id,
        "organization_id": org_id,
        "institution_id": inst_id,
        "requested_institution_code": "IMPHAL",
        "requested_by_user_id": INST_ADMIN,
        "status": status,
        "decision_reason": None,
        "decided_by_user_id": None,
        "decided_at": None,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z",
    }


def _mr_row(request_id=MR_A, inst_id=INST_A, org_id=ORG_A, status="pending"):
    return {
        "request_id": request_id,
        "institution_id": inst_id,
        "organization_id": org_id,
        "user_id": str(uuid4()),
        "requested_role": "staff",
        "official_email": "staff@imphal.example.com",
        "full_name": "Staff Member",
        "designation": None,
        "department": None,
        "status": status,
        "decision_reason": None,
        "decided_by_user_id": None,
        "decided_at": None,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z",
    }


def _base_state(org_status="pending", inst_status="pending", inst_active=False):
    return {
        "organizations": {ORG_A: _org_row(status=org_status)},
        "institutions": {
            INST_A: _inst_row(status=inst_status, is_active=inst_active)
        },
        "institution_join_requests": {JR_A: _jr_row()},
        "institution_membership_requests": {MR_A: _mr_row()},
        "roles": {ROLE_ID: {"role_id": ROLE_ID, "name": "staff", "is_active": True}},
        "users": [],
        "user_roles": [],
        "updates": [],
    }


# ===========================================================================
# 1-4. Organization / institution scope behavior
# ===========================================================================


def _org_ctx():
    return _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])


def _inst_ctx():
    return _resolve([_role_row(authz.INSTITUTION, INST_A, ORG_A)])


def test_01_organization_scoped_admin_access():
    """Org-scoped admin of Org A manages Org A and its institutions."""
    ctx = _org_ctx()
    assert ctx["scope_type"] == authz.ORGANIZATION
    assert ctx["organization_id"] == ORG_A
    assert ctx["roles"] == ["admin"]
    # Institution A belongs to Org A -> manageable (the institution's
    # organization is resolved server-side).
    with patch.object(
        tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
    ):
        authz.assert_can_manage_institution(_user(), ctx, INST_A)
    authz.assert_can_manage_organization(_user(), ctx, ORG_A)


def test_02_organization_admin_cannot_access_another_organization():
    """Org A admin can never reach Org B (scope is server-side)."""
    ctx = _org_ctx()
    with pytest.raises(AppError) as org_err:
        authz.assert_can_manage_organization(_user(), ctx, ORG_B)
    assert org_err.value.status_code == 403
    assert org_err.value.code == "ORGANIZATION_MISMATCH"
    with pytest.raises(AppError) as jr_err:
        authz.assert_can_decide_join_request(ctx, {"organization_id": ORG_B})
    assert jr_err.value.code == "ORGANIZATION_MISMATCH"


def test_03_institution_scoped_admin_access():
    """Institution-scoped admin manages THEIR institution only."""
    ctx = _inst_ctx()
    assert ctx["scope_type"] == authz.INSTITUTION
    assert ctx["scope_id"] == INST_A
    assert ctx["institution_id"] == INST_A
    assert ctx["organization_id"] == ORG_A
    authz.assert_can_manage_institution(_user(), ctx, INST_A)
    # Never organization-wide authority.
    with pytest.raises(AppError) as org_err:
        authz.assert_can_manage_organization(_user(), ctx, ORG_A)
    assert org_err.value.code == "FORBIDDEN"


def test_04_institution_admin_cannot_access_another_institution():
    """Institution A admin cannot touch Institution B (TENANT_MISMATCH)."""
    ctx = _inst_ctx()
    with pytest.raises(AppError) as excinfo:
        authz.assert_can_manage_institution(_user(), ctx, INST_B)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_MISMATCH"


# ===========================================================================
# 14-16. Missing / invalid / orphaned scope (fail closed)
# ===========================================================================


def test_14_missing_role_and_scope_denied():
    """A user with no active role rows and no tenant has no scope at all."""
    ctx = _resolve([])
    assert ctx["roles"] == []
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(_user(), ctx)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "SCOPE_MISSING"


def test_15_missing_role_denied_on_protected_endpoint():
    """No role -> 403 FORBIDDEN on the admin boundary."""
    _as(_user(roles=()))
    try:
        with patch("app.api.admin.admin_dashboard.get_dashboard_summary") as svc:
            resp = client.get("/api/v1/admin/dashboard")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    svc.assert_not_called()


def test_16_invalid_scope_denied():
    """Unknown scope_type values fail closed (SCOPE_INCONSISTENT)."""
    ctx = _resolve([_role_row("galaxy", INST_A, ORG_A)])
    assert ctx["scope_type"] == "galaxy"
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(_user(), ctx)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


def test_16b_orphaned_organization_scope_denied():
    """An organization-scoped role row naming NO tenant is rejected."""
    ctx = _resolve([_role_row(authz.ORGANIZATION, None, None)])
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(_user(), ctx)
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


def test_16c_orphaned_institution_scope_denied():
    """An institution-scoped role row naming NO institution is rejected."""
    ctx = _resolve([_role_row(authz.INSTITUTION, None, ORG_A)])
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(_user(), ctx)
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


def test_16d_scope_pointing_at_another_tenant_than_the_profile_denied():
    """Tenant-bound user whose scope names a DIFFERENT institution is rejected."""
    current_user = {"user_id": INST_ADMIN, "institution_id": INST_A}
    ctx = _resolve(
        [_role_row(authz.INSTITUTION, INST_B, ORG_B)], current_user=current_user
    )
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(current_user, ctx)
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


def test_16e_platform_scope_on_tenant_bound_account_denied():
    """A tenant-bound account can never hold platform (unrestricted) scope."""
    ctx = {
        "user_id": INST_ADMIN,
        "roles": ["admin"],
        "scope_type": authz.PLATFORM,
        "scope_id": None,
        "organization_id": None,
        "institution_id": INST_A,
    }
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(
            {"user_id": INST_ADMIN, "institution_id": INST_A}, ctx
        )
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


# ===========================================================================
# 17-20. Tenant lifecycle (fail closed)
# ===========================================================================


def test_17_inactive_institution_denied():
    """Suspended (is_active=False) institution -> TENANT_INACTIVE."""
    ctx = _inst_ctx()
    current_user = {"user_id": INST_ADMIN, "institution_id": None}
    state = _base_state(inst_status="suspended")
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(), current_user, ctx
            )
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_INACTIVE"


def test_18_pending_institution_denied():
    """Pending institution (is_active=False) -> TENANT_INACTIVE."""
    ctx = _inst_ctx()
    current_user = {"user_id": INST_ADMIN, "institution_id": None}
    state = _base_state(inst_status="pending")
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(), current_user, ctx
            )
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_INACTIVE"


def test_19_rejected_institution_denied():
    """Rejected institution -> TENANT_INACTIVE."""
    ctx = _inst_ctx()
    current_user = {"user_id": INST_ADMIN, "institution_id": None}
    state = _base_state(inst_status="rejected")
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(), current_user, ctx
            )
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_INACTIVE"


def test_19b_missing_institution_row_denied():
    """An institution-scoped user whose institution row vanished fails closed."""
    ctx = _inst_ctx()
    state = _base_state()
    state["institutions"] = {}  # orphaned scope: institution row gone
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(),
                {"user_id": INST_ADMIN, "institution_id": None},
                ctx,
            )
    assert excinfo.value.code == "TENANT_INACTIVE"


def test_20_rejected_organization_denied():
    """A rejected/suspended organization's admin can no longer act."""
    ctx = _org_ctx()
    current_user = {"user_id": ORG_ADMIN, "institution_id": None}
    for status in ("rejected", "suspended"):
        state = _base_state(org_status=status)
        with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
            with pytest.raises(AppError) as excinfo:
                authz.assert_active_tenant_context(
                    tenancy_svc.get_admin_client(), current_user, ctx
                )
        assert excinfo.value.status_code == 403
        assert excinfo.value.code == "ORGANIZATION_INACTIVE"


def test_20b_missing_organization_row_denied():
    """An org-scoped user whose organization row vanished fails closed."""
    ctx = _org_ctx()
    state = _base_state()
    state["organizations"] = {}
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(),
                {"user_id": ORG_ADMIN, "institution_id": None},
                ctx,
            )
    assert excinfo.value.code == "ORGANIZATION_INACTIVE"


def test_20c_pending_organization_still_manageable():
    """A pending organization's admin may still act while awaiting platform review."""
    ctx = _org_ctx()
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(_base_state())):
        authz.assert_active_tenant_context(
            tenancy_svc.get_admin_client(),
            {"user_id": ORG_ADMIN, "institution_id": None},
            ctx,
        )


# ===========================================================================
# 5-7, 21-22. Tenant isolation on PROTECTED ENDPOINTS
# ===========================================================================


def test_05_student_isolation_on_admin_and_chat_and_own_data():
    """A student never reaches admin data, foreign tenants, or foreign rows."""
    student = _user(TENANT_A, roles=("student",))
    # Admin boundary closed.
    _as(student)
    try:
        with patch("app.api.admin.admin_academics.list_students") as list_students:
            resp = client.get(f"/api/v1/admin/students?institution_id={TENANT_A}")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
        list_students.assert_not_called()

        # Chat: client-supplied foreign institution rejected server-side.
        with patch("app.main.process_chat_request") as process:
            resp = client.post(
                "/api/v1/generation/chat",
                json={"user_query": "hi", "institution_id": TENANT_B},
            )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        process.assert_not_called()

        # Own-profile read whose row points at ANOTHER tenant fails closed.
        foreign_profile = {
            "student_id": STUDENT_A,
            "user_id": student["user_id"],
            "institution_id": TENANT_B,
        }
        db = MagicMock()
        (
            db.table.return_value.select.return_value.eq.return_value.maybe_single
            .return_value.execute
        ).return_value = MagicMock(data=foreign_profile)
        with patch(
            "app.services.student_data.get_admin_client", return_value=db
        ):
            resp = client.get("/api/v1/students/me/profile")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    finally:
        _clear()


def test_05b_student_same_tenant_data_allowed():
    """A student of Institution A reads their own Institution A profile."""
    student = _user(TENANT_A, roles=("student",))
    own_profile = {
        "student_id": STUDENT_A,
        "user_id": student["user_id"],
        "institution_id": TENANT_A,
    }
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single
        .return_value.execute
    ).return_value = MagicMock(data=own_profile)
    _as(student)
    try:
        with patch("app.services.student_data.get_admin_client", return_value=db):
            resp = client.get("/api/v1/students/me/profile")
    finally:
        _clear()
    assert resp.status_code == 200
    assert resp.json()["institution_id"] == TENANT_A


def test_06_faculty_isolation_on_ingestion_pipeline():
    """A faculty of Institution A cannot ingest/extract for Institution B."""
    faculty = _user(TENANT_A, roles=("faculty",))
    _as(faculty)
    try:
        # /documents/ingest against a foreign knowledge source -> 403.
        with (
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch(
                "app.api.ingestion.get_knowledge_source",
                return_value={
                    "knowledge_source_id": KS_B,
                    "institution_id": TENANT_B,
                },
            ),
            patch("app.api.ingestion.ingest_document") as ingest,
        ):
            resp = client.post(
                "/api/v1/documents/ingest",
                files={"file": ("doc.txt", b"hello", "text/plain")},
                data={"knowledge_source_id": KS_B},
            )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        ingest.assert_not_called()

        # NEW Phase 6.13.7 guard: extract for a run whose knowledge source
        # belongs to Institution B is rejected even though the run id is valid.
        run = {
            "processing_run_id": RUN_ID,
            "status": "queued",
            "document_version_id": DV_ID,
            "document_versions": {
                "document_version_id": DV_ID,
                "storage_bucket": "bucket",
                "storage_object_key": "key",
                "file_type": "txt",
                "knowledge_source_id": KS_B,
            },
        }
        with (
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch(
                "app.api.ingestion.get_processing_run_with_version",
                return_value=run,
            ),
            patch(
                "app.api.ingestion.knowledge_repo.get_knowledge_source_detail",
                return_value={"institution_id": TENANT_B},
            ),
            patch("app.api.ingestion.update_run_status") as update_status,
        ):
            resp = client.post(f"/api/v1/documents/{RUN_ID}/extract")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        update_status.assert_not_called()

        # Same-tenant run flows through (guard passes).
        run_same = {
            **run,
            "document_versions": {
                **run["document_versions"],
                "knowledge_source_id": KS_A,
            },
        }
        with (
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch(
                "app.api.ingestion.get_processing_run_with_version",
                return_value=run_same,
            ),
            patch(
                "app.api.ingestion.knowledge_repo.get_knowledge_source_detail",
                return_value={"institution_id": TENANT_A},
            ),
            patch("app.api.ingestion.update_run_status"),
            patch("app.api.ingestion.store_extracted_text"),
            patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
            patch("app.api.ingestion.download_file", return_value=b"text"),
            patch("app.api.ingestion.extract_text", return_value="text"),
        ):
            resp = client.post(f"/api/v1/documents/{RUN_ID}/extract")
        assert resp.status_code == 200, resp.text
    finally:
        _clear()


def test_06b_embed_guard_denies_foreign_tenant_run():
    """The embed route resolves the run server-side; foreign tenant -> 403."""
    faculty = _user(TENANT_A, roles=("faculty",))
    run = {
        "processing_run_id": RUN_ID,
        "status": "ready",
        "document_versions": {
            "document_version_id": DV_ID,
            "knowledge_source_id": KS_B,
        },
    }
    _as(faculty)
    try:
        with (
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch(
                "app.api.ingestion.get_processing_run_with_version",
                return_value=run,
            ),
            patch(
                "app.api.ingestion.knowledge_repo.get_knowledge_source_detail",
                return_value={"institution_id": TENANT_B},
            ),
            patch("app.api.ingestion.embed_processing_run") as embed,
        ):
            resp = client.post(f"/api/v1/documents/{RUN_ID}/embed")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    embed.assert_not_called()


def test_07_staff_isolation_on_approval_queue():
    """A staff of Institution A is scoped to A and denied B."""
    staff = _user(TENANT_A, roles=("staff",))
    _as(staff)
    try:
        with patch("app.api.admin.admin_academics.list_pending_approvals") as svc:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_B}"
            )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        svc.assert_not_called()

        # Own tenant: forced to A even when A is requested.
        with patch(
            "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as svc:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_A}"
            )
        assert resp.status_code == 200
        assert str(svc.call_args.args[0]) == TENANT_A
    finally:
        _clear()


def test_07b_staff_cannot_access_admin_only_operations():
    """Staff is denied the admin-only boundary (no escalation)."""
    staff = _user(TENANT_A, roles=("staff",))
    _as(staff)
    try:
        r1 = client.get("/api/v1/admin/me")
        r2 = client.get("/api/v1/admin/audit-logs")
    finally:
        _clear()
    assert r1.status_code == 403
    assert r2.status_code == 403


def test_12_client_institution_id_substitution_denied():
    """A tenant-bound admin cannot substitute another institution id."""
    admin = _user(TENANT_A, roles=("admin",))
    _as(admin)
    try:
        with patch("app.api.admin.admin_academics.list_students") as list_students:
            resp = client.get(f"/api/v1/admin/students?institution_id={TENANT_B}")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    list_students.assert_not_called()


def test_13_client_organization_id_substitution_denied():
    """Org A admin cannot manage an institution belonging to Org B.

    The institution's organization is resolved SERVER-SIDE (the client can
    never substitute it) — even against a foreign institution id, the guard
    compares the resolved organization with the caller's scope.
    """
    ctx = _org_ctx()
    with patch.object(
        tenancy_repo, "get_institution_organization", return_value=UUID(ORG_B)
    ):
        with pytest.raises(AppError) as excinfo:
            authz.assert_can_manage_institution(_user(), ctx, INST_B)
    assert excinfo.value.code == "ORGANIZATION_MISMATCH"


def test_21_cross_tenant_resource_access_denied():
    """Direct object access: a tenant-bound admin cannot read a foreign row."""
    admin = _user(TENANT_A, roles=("admin",))
    foreign = {"student_id": STUDENT_A, "institution_id": TENANT_B}
    _as(admin)
    try:
        with patch(
            "app.api.admin.admin_academics.get_student", return_value=foreign
        ):
            resp = client.get(f"/api/v1/admin/students/{STUDENT_A}")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"


def test_22_valid_same_tenant_resource_access_allowed():
    """Same-tenant reads succeed and are forced to the caller's institution."""
    admin = _user(TENANT_A, roles=("admin",))
    _as(admin)
    try:
        with patch(
            "app.api.admin.admin_academics.list_students", return_value=[]
        ) as list_students:
            resp = client.get(f"/api/v1/admin/students?institution_id={TENANT_A}")
    finally:
        _clear()
    assert resp.status_code == 200
    assert str(list_students.call_args.args[0]) == TENANT_A


def test_22b_platform_account_behavior_preserved():
    """Platform-level accounts keep the previous passthrough behaviour."""
    assert scope_tenant(_user(None), TENANT_B) == UUID(TENANT_B)
    assert_tenant_object(_user(None), TENANT_B)  # no-op


# ===========================================================================
# Tenancy decision ENDPOINTS (org/institution scope + lifecycle, server-side)
# ===========================================================================


def _login(user):
    _as(user)


def _logout():
    _clear()


def _decision(decision: str, reason: str | None = None):
    body = {"decision": decision}
    if reason is not None:
        body["decision_reason"] = reason
    return body


def test_01b_org_scoped_admin_decides_own_join_request_endpoint():
    """Org A admin (server-resolved scope) approves its own join request."""
    state = _base_state()  # ORG_A pending (allowed), join request pending
    _login(_user(None, roles=("admin",), user_id=ORG_ADMIN))
    patches = _authz_patches(ORG_ADMIN, [_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 200, resp.text
    assert state["institution_join_requests"][JR_A]["status"] == "approved"
    assert state["institutions"][INST_A]["status"] == "active"
    assert state["institutions"][INST_A]["is_active"] is True


def test_02b_org_admin_cannot_decide_another_orgs_join_request_endpoint():
    """Org B admin cannot decide Org A's join request (ID substitution)."""
    state = _base_state()
    _login(_user(None, roles=("admin",), user_id=ORG_ADMIN))
    patches = _authz_patches(ORG_ADMIN, [_role_row(authz.ORGANIZATION, ORG_B, ORG_B)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_MISMATCH"
    assert state["institution_join_requests"][JR_A]["status"] == "pending"


def test_20d_rejected_org_admin_denied_on_decision_endpoint():
    """A rejected organization's admin cannot act through the endpoint either."""
    state = _base_state(org_status="rejected")
    _login(_user(None, roles=("admin",), user_id=ORG_ADMIN))
    patches = _authz_patches(ORG_ADMIN, [_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_INACTIVE"
    assert state["institution_join_requests"][JR_A]["status"] == "pending"


def test_01c_platform_admin_approves_pending_organization():
    """Platform admin keeps the previous authority; the new guard is a no-op."""
    state = _base_state()  # ORG_A pending
    _login(_user(None, roles=("admin",), user_id=USER_ADMIN))
    patches = _authz_patches(USER_ADMIN, [_role_row(authz.PLATFORM, None, None)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/organizations/{ORG_A}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 200, resp.text
    assert state["organizations"][ORG_A]["status"] == "active"


def test_03b_institution_admin_membership_decision_lifecycle():
    """Institution admin: ACTIVE institution allows, PENDING denies (service)."""
    from app.schemas.tenancy import ApprovalDecisionRequest

    current_user = {"user_id": INST_ADMIN, "institution_id": None}
    ctx = _inst_ctx()

    # ACTIVE institution: membership approval succeeds and grants the role.
    state = _base_state(inst_status="active", inst_active=True)
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        response = tenancy_svc.decide_membership_request(
            current_user,
            ctx,
            MR_A,
            ApprovalDecisionRequest(decision="approve"),
        )
    assert response.status == "approve"
    assert state["institution_membership_requests"][MR_A]["status"] == "approve"
    assert len(state["user_roles"]) == 1  # role granted server-side

    # PENDING institution: fail closed BEFORE any write.
    state_pending = _base_state(inst_status="pending")
    with patch.object(
        tenancy_svc, "get_admin_client", return_value=_db(state_pending)
    ):
        with pytest.raises(AppError) as excinfo:
            tenancy_svc.decide_membership_request(
                current_user,
                ctx,
                MR_A,
                ApprovalDecisionRequest(decision="approve"),
            )
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_INACTIVE"
    assert (
        state_pending["institution_membership_requests"][MR_A]["status"]
        == "pending"
    )
    assert state_pending["user_roles"] == []


# ===========================================================================
# 8-11. Role enforcement + client injection
# ===========================================================================


def test_08_correct_role_enforcement_matrix():
    """admin / staff / faculty / student pass their authorized boundaries."""
    # admin passes the admin boundary.
    admin = _user(TENANT_A, roles=("admin",))
    assert asyncio.run(require_roles("admin")(current_user=admin)) is admin
    # staff passes the approval boundary (admin + staff).
    staff = _user(TENANT_A, roles=("staff",))
    assert asyncio.run(require_roles("admin", "staff")(current_user=staff)) is staff
    # faculty passes the ingestion boundary (admin + staff + faculty).
    faculty = _user(TENANT_A, roles=("faculty",))
    assert (
        asyncio.run(require_roles("admin", "staff", "faculty")(current_user=faculty))
        is faculty
    )
    # student passes the student-only boundary and nothing above it.
    student = _user(TENANT_A, roles=("student",))
    assert asyncio.run(require_roles("student")(current_user=student)) is student
    with pytest.raises(AppError) as admin_err:
        asyncio.run(require_roles("admin")(current_user=student))
    assert admin_err.value.code == "FORBIDDEN"


def test_09_unauthorized_role_denied():
    """Faculty cannot reach admin-only operations (403 FORBIDDEN)."""
    faculty = _user(TENANT_A, roles=("faculty",))
    _as(faculty)
    try:
        with patch("app.api.admin.admin_academics.list_students") as list_students:
            resp = client.get("/api/v1/admin/me")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
        list_students.assert_not_called()
    finally:
        _clear()


def test_10_client_role_injection_denied():
    """Login / registration schemas forbid client-supplied role fields."""
    base_login = {"email": "user@example.com", "password": "secret123"}
    for extra in ({"role": "admin"}, {"roles": ["admin"]}, {"scope_type": "platform"}):
        resp = client.post("/api/v1/auth/login", json={**base_login, **extra})
        assert resp.status_code == 422, (extra, resp.text)

    base_student_login = {"identifier": "student@college.edu", "password": "pw"}
    for extra in (
        {"role": "admin"},
        {"institution_id": TENANT_A},
        {"scope_id": TENANT_A},
    ):
        resp = client.post(
            "/api/v1/auth/student/login", json={**base_student_login, **extra}
        )
        assert resp.status_code == 422, (extra, resp.text)

    base_registration = {
        "institution_id": TENANT_A,
        "email": "new@college.edu",
        "password": "secret123",
        "first_name": "New",
        "last_name": "Student",
        "register_number": "REG137",
    }
    for extra in (
        {"role": "admin"},
        {"roles": ["admin"]},
        {"approval_status": "approved"},
    ):
        resp = client.post(
            "/api/v1/registration", json={**base_registration, **extra}
        )
        assert resp.status_code == 422, (extra, resp.text)


def test_11_client_scope_injection_denied():
    """Decision bodies cannot carry scope/status fields (extra='forbid')."""
    state = _base_state()
    _login(_user(None, roles=("admin",), user_id=ORG_ADMIN))
    patches = _authz_patches(ORG_ADMIN, [_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        for extra in (
            {"status": "approved", "scope_type": "platform"},
            {"role": "admin", "scope_id": ORG_B},
            {"organization_id": ORG_B},
        ):
            resp = client.post(
                f"/api/v1/institutions/join-requests/{JR_A}/decision",
                json={"decision": "approve", **extra},
            )
            assert resp.status_code == 422, (extra, resp.text)
            assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    _logout()
    assert state["institution_join_requests"][JR_A]["status"] == "pending"


# ===========================================================================
# 23-24. Regression markers
# ===========================================================================


def test_23_phase_6_rbac_regression():
    """Existing RBAC primitives are unchanged by Phase 6.13.7."""
    # Role-based RBAC still passes an institution-scoped admin...
    admin = {
        "user_id": INST_ADMIN,
        "auth_user_id": str(uuid4()),
        "email": "inst-admin@example.com",
        "roles": ["admin"],
        "institution_id": TENANT_A,
    }
    assert asyncio.run(require_roles("admin")(current_user=admin)) is admin
    # ...while narrowing stays with the scope layer, not require_roles().
    with pytest.raises(AppError) as excinfo:
        asyncio.run(require_roles("admin")(current_user=_user(roles=("staff",))))
    assert excinfo.value.code == "FORBIDDEN"
    # Unauthenticated requests still get 401 from get_current_user.
    _clear()
    resp = client.get("/api/v1/admin/me")
    assert resp.status_code == 401
    # Tenant primitives keep their locked semantics.
    with pytest.raises(AppError) as tenant_err:
        scope_tenant(_user(TENANT_A), TENANT_B)
    assert tenant_err.value.code == "TENANT_MISMATCH"
    with pytest.raises(AppError) as row_err:
        assert_tenant_object(_user(TENANT_A), TENANT_B)
    assert row_err.value.code == "TENANT_MISMATCH"


def test_24_phase_6_13_1_to_6_13_6_regression():
    """Legacy scope resolution, sign-in guard, and schemas stay locked."""
    # Legacy tenant-bound unscoped row stays INSTITUTION (never widened).
    legacy_tenant_row = {
        "role_id": ROLE_ID,
        "role_name": "student",
        "is_active": True,
        "scope_type": None,
        "scope_id": None,
        "scope_organization_id": None,
    }
    ctx = _resolve(
        [legacy_tenant_row],
        current_user={"user_id": INST_ADMIN, "institution_id": INST_A},
    )
    assert ctx["scope_type"] == authz.INSTITUTION
    assert ctx["institution_id"] == INST_A
    # Legacy tenant-less unscoped row stays PLATFORM.
    ctx_platform = _resolve([legacy_tenant_row])
    assert ctx_platform["scope_type"] == authz.PLATFORM
    # Sign-in guard: missing account and non-active user fail closed.
    from app.services.sign_in import assert_sign_in_allowed

    with pytest.raises(SafeAuthFailure):
        assert_sign_in_allowed(MagicMock(), None)
    with pytest.raises(SafeAuthFailure):
        assert_sign_in_allowed(
            MagicMock(),
            {
                "user_id": USER_ADMIN,
                "status": "inactive",
                "institution_id": None,
                "approval_status": None,
                "student_is_active": None,
            },
        )
    assert (
        assert_sign_in_allowed(
            MagicMock(),
            {
                "user_id": USER_ADMIN,
                "status": "active",
                "institution_id": None,
                "approval_status": None,
                "student_is_active": None,
            },
        )
        is None
    )
    # Decision vocabulary and schema locks are untouched.
    assert tenancy_svc.ORGANIZATION_DECISION_STATUS == {
        "approve": "active",
        "reject": "rejected",
    }
    from app.schemas.tenancy import ApprovalDecisionRequest

    with pytest.raises(Exception):
        ApprovalDecisionRequest.model_validate(
            {"decision": "approve", "scope_type": "platform"}
        )
