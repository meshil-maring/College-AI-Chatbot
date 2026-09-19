"""Phase 6.13.9 — Security + Final Validation tests.

Final security / integration validation for the Phase 6.13 organization and
multi-tenant architecture (Phases 6.13.1–6.13.8).  This suite adds NO product
feature; it exercises the EXISTING trusted chain end to end and asserts that
every manipulated client input fails closed:

    JWT sub -> public.users -> user_roles(role, scope_type, scope_id,
    scope_organization_id) -> organizations / institutions (lifecycle)
    -> resource/data -> AI/RAG context

Covered areas (mapped to the phase brief):

     2. organization isolation (Org A vs Org B, inst B1, users, knowledge, data)
     3. institution isolation (student / faculty / staff / institution admin,
        organization-scoped admin behaviour)
     4. role + scope escalation denial (role, scope_type, scope_id,
        organization_id, institution_id, student_id, user_id)
     5. registration security (org / institution / student / faculty / staff)
     6. approval security (platform / organization authority, lifecycle)
     7. authentication security (valid/invalid, lifecycle, identifiers)
     8. public AI security (server-side tenant, public-only retrieval boundary)
     9. protected AI security (role + scope + own-data only)
    10. lifecycle security (PENDING -> ACTIVE -> REJECTED / INACTIVE)
    11. data integrity (DB constraints/triggers + application guards)
    12. regression markers (Phase 6.3 / 6.5 / 6.6 / 6.13.1-6.13.8)

All Supabase/GoTrue clients are mocked — no live services.  Protected
ENDPOINTS and the actual retrieval/context boundary are exercised, not only
prompt instructions or helper functions.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.core.security import (
    PUBLIC_USER_ID,
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
# Stable identifiers — Organization A {Institution A1, Institution A2},
# Organization B {Institution B1}
# ---------------------------------------------------------------------------

ORG_A = "a0000000-0000-0000-0000-00000000000a"
ORG_B = "b0000000-0000-0000-0000-00000000000b"
INST_A1 = "10000000-0000-0000-0000-0000000000a1"
INST_A2 = "10000000-0000-0000-0000-0000000000a2"
INST_B1 = "10000000-0000-0000-0000-0000000000b1"

KS_FAQ_A1 = "20000000-0000-0000-0000-0000000000a1"
KS_PRIVATE_A1 = "20000000-0000-0000-0000-0000000000a2"
KS_FAQ_B1 = "20000000-0000-0000-0000-0000000000b1"

RUN_FAQ_A1 = "30000000-0000-0000-0000-0000000000a1"
RUN_PRIVATE_A1 = "30000000-0000-0000-0000-0000000000a2"
RUN_FAQ_B1 = "30000000-0000-0000-0000-0000000000b1"

CHUNK_FAQ_A1 = "40000000-0000-0000-0000-0000000000a1"
CHUNK_PRIVATE_A1 = "40000000-0000-0000-0000-0000000000a2"
CHUNK_FAQ_B1 = "40000000-0000-0000-0000-0000000000b1"

SESSION_ID = "00000000-0000-0000-0000-000000000999"
CONVERSATION_ID = "50000000-0000-0000-0000-000000000001"
MESSAGE_ID = "50000000-0000-0000-0000-000000000002"

ROLE_ID = "e0000000-0000-0000-0000-000000000001"
USER_PLATFORM = "c0000000-0000-0000-0000-000000000001"
USER_ORG_A = "c0000000-0000-0000-0000-000000000002"
USER_ORG_B = "c0000000-0000-0000-0000-000000000003"
USER_INST_A1 = "c0000000-0000-0000-0000-000000000004"
USER_STUDENT_A1 = "c0000000-0000-0000-0000-000000000005"
USER_FACULTY_A1 = "c0000000-0000-0000-0000-000000000006"
USER_STAFF_A1 = "c0000000-0000-0000-0000-000000000007"
STUDENT_ID_A1 = "d0000000-0000-0000-0000-000000000001"
STUDENT_ID_B1 = "d0000000-0000-0000-0000-000000000002"
JR_A = "60000000-0000-0000-0000-000000000001"
JR_B = "60000000-0000-0000-0000-000000000002"
MR_A = "70000000-0000-0000-0000-000000000001"

MR_A = "70000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# current_user fixtures (shape locked by get_current_user)
# ---------------------------------------------------------------------------


def _user(tenant=None, roles=("admin",), user_id=None):
    return {
        "user_id": user_id or str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "phase6139@example.com",
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
    cu = current_user or {"user_id": USER_PLATFORM, "institution_id": None}
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        return authz.resolve_authorization_context(cu)


# ---------------------------------------------------------------------------
# Fake service-role PostgREST client (stateful, per-table)
# ---------------------------------------------------------------------------


class _Table:
    """Chainable query builder answering reads/writes from ``state``."""

    def __init__(self, state: dict, name: str):
        self._state = state
        self._name = name
        self._filters: list[tuple] = []
        self._single = False
        self._payload = None
        self._mode = None
        self._in_filter = None

    def select(self, *a, **k):
        self._state.setdefault("accesses", [])
        if self._name not in self._state["accesses"]:
            self._state["accesses"].append(self._name)
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def ilike(self, column, value):
        self._filters.append((column, value, "ilike"))
        return self

    def in_(self, column, values):
        self._in_filter = (column, [str(v) for v in values])
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def maybe_single(self):
        self._single = True
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self._mode = "upsert"
        self._payload = payload
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def _rows(self):
        rows = self._state.get(self._name, [])
        if isinstance(rows, dict):
            rows = list(rows.values())

        def match(row):
            for f in self._filters:
                if len(f) == 3:
                    col, value, _ = f
                    if str(row.get(col, "")).lower() != str(value).lower():
                        return False
                else:
                    col, value = f
                    if str(row.get(col, "")) != str(value):
                        return False
            if self._in_filter:
                col, values = self._in_filter
                if str(row.get(col, "")) not in values:
                    return False
            return True

        return [row for row in rows if match(row)]

    def execute(self):
        if self._mode == "delete":
            doomed = self._rows()
            table = self._state.get(self._name, [])
            if isinstance(table, list):
                self._state[self._name] = [r for r in table if r not in doomed]
            return SimpleNamespace(data=[])
        if self._mode in ("insert", "upsert"):
            row = dict(self._payload)
            if self._mode == "upsert":
                existing = self._rows()
                if existing:
                    existing[0].update(row)
                    return SimpleNamespace(data=[existing[0]])
            defaults = {
                "students": ("student_id", STUDENT_ID_A1),
                "institution_membership_requests": ("request_id", MR_A),
                "institutions": ("institution_id", INST_A1),
                "organizations": ("organization_id", ORG_A),
                "institution_join_requests": ("join_request_id", JR_A),
            }
            if self._name in defaults:
                key, value = defaults[self._name]
                row.setdefault(key, value)
            table = self._state.setdefault(self._name, [])
            if isinstance(table, dict):
                table.setdefault(str(row.get("user_id", uuid4())), row)
            else:
                table.append(row)
            return SimpleNamespace(data=[row])
        if self._mode == "update":
            updated = self._rows()
            for row in updated:
                row.update(self._payload)
                if self._name == "institutions":
                    # Emulate trg_phase613_institutions_status.
                    row["is_active"] = row.get("status") == "active"
            return SimpleNamespace(data=updated)
        rows = self._rows()
        if self._single:
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)


class _FakeClient:
    """Permissive fake Supabase client for the whole request pipeline."""

    def __init__(self, tables=None):
        self.state: dict = {"accesses": []}
        if tables:
            self.state.update(tables)

    def table(self, name):
        return _Table(self.state, name)


def _org_row(org_id=ORG_A, status="active"):
    return {
        "organization_id": org_id,
        "name": "Acme Org" if org_id == ORG_A else "Beta Org",
        "organization_code": "ACME" if org_id == ORG_A else "BETA",
        "official_email": "info@acme.example.com",
        "contact_information": "contact@acme.example.com",
        "status": status,
        "join_code": None,
        "created_at": "2026-09-19T00:00:00Z",
        "updated_at": "2026-09-19T00:00:00Z",
    }


def _inst_row(inst_id=INST_A1, org_id=ORG_A, status="active"):
    codes = {INST_A1: "IMPHAL", INST_A2: "CHURACHANDPUR", INST_B1: "BETACOLLEGE"}
    return {
        "institution_id": inst_id,
        "organization_id": org_id,
        "name": "Campus",
        "code": codes[inst_id],
        "email": None,
        "address": None,
        "city": None,
        "state": None,
        "country": None,
        "status": status,
        "is_active": status == "active",
        "created_at": "2026-09-19T00:00:00Z",
        "updated_at": "2026-09-19T00:00:00Z",
    }


def _ks_row(ks_id, inst_id, source_type="faq", lifecycle="published"):
    return {
        "knowledge_source_id": ks_id,
        "institution_id": inst_id,
        "source_type": source_type,
        "title": f"Source {source_type}",
        "description": None,
        "authority_level": "official",
        "lifecycle_status": lifecycle,
        "effective_from": None,
        "effective_until": None,
        "created_at": "2026-09-19T00:00:00Z",
        "updated_at": "2026-09-19T00:00:00Z",
    }


def _run_row(run_id, ks_id):
    return {
        "processing_run_id": run_id,
        "document_versions": {"knowledge_source_id": ks_id},
    }


def _base_state():
    """Org A {Inst A1, Inst A2}, Org B {Inst B1} — all ACTIVE."""
    return {
        "organizations": [
            _org_row(ORG_A, "active"),
            _org_row(ORG_B, "active"),
        ],
        "institutions": [
            _inst_row(INST_A1, ORG_A, "active"),
            _inst_row(INST_A2, ORG_A, "active"),
            _inst_row(INST_B1, ORG_B, "active"),
        ],
        "knowledge_sources": [
            _ks_row(KS_FAQ_A1, INST_A1, "faq"),
            _ks_row(KS_PRIVATE_A1, INST_A1, "private"),
            _ks_row(KS_FAQ_B1, INST_B1, "faq"),
        ],
        "document_processing_runs": [
            _run_row(RUN_FAQ_A1, KS_FAQ_A1),
            _run_row(RUN_PRIVATE_A1, KS_PRIVATE_A1),
            _run_row(RUN_FAQ_B1, KS_FAQ_B1),
        ],
    }


# ---------------------------------------------------------------------------
# Public AI full-pipeline harness
# ---------------------------------------------------------------------------


class _CapturingProvider:
    """GenerationProvider that records the AIContext it receives."""

    def __init__(self):
        self.contexts = []

    def generate(self, context, *, answer_model=None):
        from app.services.generation_provider import GenerationResult

        self.contexts.append(context)
        return GenerationResult(
            answer="Public answer",
            model_used="test-model",
            status="success",
            metadata={"usage": {"prompt_tokens": 1, "completion_tokens": 1}},
        )


def _chat_request(
    query="What are the college fees?",
    institution_id=INST_A1,
    knowledge_source_id=None,
    retrieved_chunks=None,
):
    from app.schemas.chat import ChatRequest

    return ChatRequest(
        user_query=query,
        institution_id=institution_id,
        session_id=SESSION_ID,
        knowledge_source_id=knowledge_source_id,
        retrieved_chunks=retrieved_chunks or [],
    )


def _retrieved_chunk(chunk_id, run_id, text):
    from app.schemas.generation import RetrievedChunk

    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        similarity_score=0.9,
        metadata={"processing_run_id": run_id},
    )


def _run_public_chat(fake, request):
    """Run the real public chat pipeline against the fake client.

    Only the persistence seams (conversation/message reads/writes and the
    background writer) are stubbed; tenant validation and the public-only
    retrieval filter run for real against ``fake``.
    """
    from app.schemas.session import SessionContext
    from app.services import public_chat

    provider = _CapturingProvider()
    with (
        patch.object(public_chat, "get_admin_client", return_value=fake),
        patch.object(
            public_chat,
            "get_conversation",
            return_value={"conversation_id": CONVERSATION_ID},
        ),
        patch.object(public_chat, "get_conversation_messages", return_value=[]),
        patch.object(public_chat, "get_next_message_sequence", return_value=1),
        patch.object(
            public_chat, "create_message", return_value={"message_id": MESSAGE_ID}
        ),
        patch.object(public_chat, "_start_background_persistence", return_value=None),
    ):
        response = public_chat.process_chat_request(
            request, SessionContext(session_id=UUID(SESSION_ID)), provider
        )
    return response, provider

# ===========================================================================
# 2. Organization isolation
# ===========================================================================


class TestOrganizationIsolation:
    """A user of Org A can never reach Org B — normal or manipulated ids."""

    def test_org_a_admin_cannot_manage_org_b(self):
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_organization(_user(user_id=USER_ORG_A), ctx, ORG_B)
        assert exc.value.status_code == 403
        assert exc.value.code == "ORGANIZATION_MISMATCH"

    def test_org_a_admin_manages_own_org(self):
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        authz.assert_can_manage_organization(_user(user_id=USER_ORG_A), ctx, ORG_A)

    def test_org_a_admin_cannot_manage_org_b_institution(self):
        """The institution's organization is resolved server-side."""
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_B)
        ):
            with pytest.raises(AppError) as exc:
                authz.assert_can_manage_institution(_user(user_id=USER_ORG_A), ctx, INST_B1)
        assert exc.value.code == "ORGANIZATION_MISMATCH"

    def test_org_a_admin_manages_all_institutions_of_own_org(self):
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        for inst in (INST_A1, INST_A2):
            with patch.object(
                tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
            ):
                authz.assert_can_manage_institution(_user(user_id=USER_ORG_A), ctx, inst)

    def test_org_a_knowledge_not_visible_to_org_b_institution(self):
        from app.services import public_chat

        fake = _FakeClient(_base_state())
        assert public_chat._knowledge_source_is_public(fake, KS_FAQ_A1, UUID(INST_A1))
        # The same source is NOT public for institution B1.
        assert not public_chat._knowledge_source_is_public(fake, KS_FAQ_A1, UUID(INST_B1))

    def test_org_a_request_never_gets_org_b_knowledge(self):
        from app.services import public_chat

        fake = _FakeClient(_base_state())
        allowed = public_chat._build_allowed_public_knowledge_source_ids(
            fake, UUID(INST_A1), None
        )
        assert KS_FAQ_B1 not in allowed
        assert allowed == {KS_FAQ_A1}

    def test_org_a_cannot_explicitly_select_org_b_source(self):
        from app.services import public_chat

        fake = _FakeClient(_base_state())
        with pytest.raises(AppError) as exc:
            public_chat._build_allowed_public_knowledge_source_ids(
                fake, UUID(INST_A1), KS_FAQ_B1
            )
        assert exc.value.status_code == 403
        assert exc.value.code == "KNOWLEDGE_SOURCE_NOT_PUBLIC"

    def test_org_b_chunk_never_reaches_org_a_llm_context(self):
        """Full pipeline: a manipulated Org B chunk is filtered out."""
        fake = _FakeClient(_base_state())
        request = _chat_request(
            retrieved_chunks=[
                _retrieved_chunk(CHUNK_FAQ_A1, RUN_FAQ_A1, "Org A public fact"),
                _retrieved_chunk(CHUNK_FAQ_B1, RUN_FAQ_B1, "Org B secret fact"),
            ]
        )
        _, provider = _run_public_chat(fake, request)
        texts = [c.text for c in provider.contexts[0].retrieved_knowledge]
        assert "Org A public fact" in texts
        assert "Org B secret fact" not in texts

    def test_org_a_admin_decision_on_org_b_join_request_denied(self):
        from app.schemas.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["institution_join_requests"] = [
            {
                "join_request_id": JR_B,
                "organization_id": ORG_B,
                "institution_id": INST_B1,
                "status": "pending",
            }
        ]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_join_request(
                    _user(user_id=USER_ORG_A),
                    ctx,
                    JR_B,
                    ApprovalDecisionRequest(decision="approve"),
                )
        assert exc.value.code == "ORGANIZATION_MISMATCH"
        assert state["institution_join_requests"][0]["status"] == "pending"

    def test_org_a_cannot_read_org_b_academic_data_endpoint(self):
        """Org B student row is unreachable from an Org A tenant-bound admin."""
        admin = _user(INST_A1, roles=("admin",))
        foreign_student = {"student_id": STUDENT_ID_B1, "institution_id": INST_B1}
        _as(admin)
        try:
            with patch(
                "app.api.admin.admin_academics.get_student", return_value=foreign_student
            ):
                resp = client.get(f"/api/v1/admin/students/{STUDENT_ID_B1}")
        finally:
            _clear()
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"



# ===========================================================================
# 3. Institution isolation (student / faculty / staff / institution admin)
# ===========================================================================


class TestInstitutionIsolation:
    """A user scoped to Institution A cannot access Institution B."""

    def test_student_a_cannot_read_institution_b_profile_row(self):
        student = _user(INST_A1, roles=("student",), user_id=USER_STUDENT_A1)
        foreign_profile = {
            "student_id": STUDENT_ID_A1,
            "user_id": student["user_id"],
            "institution_id": INST_B1,
        }
        db = MagicMock()
        (
            db.table.return_value.select.return_value.eq.return_value.maybe_single
            .return_value.execute
        ).return_value = MagicMock(data=foreign_profile)
        _as(student)
        try:
            with patch("app.services.student_data.get_admin_client", return_value=db):
                resp = client.get("/api/v1/students/me/profile")
        finally:
            _clear()
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"

    def test_student_a_reads_own_institution_a_profile(self):
        student = _user(INST_A1, roles=("student",), user_id=USER_STUDENT_A1)
        own_profile = {
            "student_id": STUDENT_ID_A1,
            "user_id": student["user_id"],
            "institution_id": INST_A1,
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
        assert resp.json()["institution_id"] == INST_A1

    def test_faculty_a_cannot_ingest_for_institution_b(self):
        faculty = _user(INST_A1, roles=("faculty",), user_id=USER_FACULTY_A1)
        _as(faculty)
        try:
            with (
                patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
                patch(
                    "app.api.ingestion.get_knowledge_source",
                    return_value={
                        "knowledge_source_id": KS_FAQ_B1,
                        "institution_id": INST_B1,
                    },
                ),
                patch("app.api.ingestion.ingest_document") as ingest,
            ):
                resp = client.post(
                    "/api/v1/documents/ingest",
                    files={"file": ("doc.txt", b"hello", "text/plain")},
                    data={"knowledge_source_id": KS_FAQ_B1},
                )
        finally:
            _clear()
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        ingest.assert_not_called()

    def test_staff_a_cannot_read_institution_b_approval_queue(self):
        staff = _user(INST_A1, roles=("staff",), user_id=USER_STAFF_A1)
        _as(staff)
        try:
            with patch("app.api.admin.admin_academics.list_pending_approvals") as svc:
                resp = client.get(
                    f"/api/v1/admin/students/pending?institution_id={INST_B1}"
                )
        finally:
            _clear()
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        svc.assert_not_called()

    def test_institution_admin_a_cannot_manage_institution_b(self):
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_institution(
                _user(user_id=USER_INST_A1), ctx, INST_B1
            )
        assert exc.value.status_code == 403
        assert exc.value.code == "TENANT_MISMATCH"

    def test_institution_admin_a_cannot_manage_its_organization(self):
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_organization(
                _user(user_id=USER_INST_A1), ctx, ORG_A
            )
        assert exc.value.code == "FORBIDDEN"

    def test_institution_admin_a_cannot_decide_org_b_join_request(self):
        from app.schemas.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["institution_join_requests"] = [
            {
                "join_request_id": JR_A,
                "organization_id": ORG_A,
                "institution_id": INST_A1,
                "status": "pending",
            }
        ]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_join_request(
                    _user(INST_A1, user_id=USER_INST_A1),
                    ctx,
                    JR_A,
                    ApprovalDecisionRequest(decision="approve"),
                )
        # An institution-scoped user can never decide a join request.
        assert exc.value.status_code == 403
        assert state["institution_join_requests"][0]["status"] == "pending"

    def test_org_admin_scope_reaches_both_institutions_of_org_a(self):
        """Organization-scoped admin manages all of its own institutions."""
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ):
            authz.assert_can_manage_institution(_user(user_id=USER_ORG_A), ctx, INST_A1)
            authz.assert_can_manage_institution(_user(user_id=USER_ORG_A), ctx, INST_A2)
# ===========================================================================
# 4. Role + scope escalation denial
# ===========================================================================


class TestRoleEscalation:
    """Client input can never elevate privileges; scope never widens."""

    def test_student_cannot_become_admin(self):
        student = _user(INST_A1, roles=("student",), user_id=USER_STUDENT_A1)
        with pytest.raises(AppError) as exc:
            asyncio.run(require_roles("admin")(current_user=student))
        assert exc.value.status_code == 403
        assert exc.value.code == "FORBIDDEN"

    def test_student_denied_admin_endpoint(self):
        student = _user(INST_A1, roles=("student",), user_id=USER_STUDENT_A1)
        _as(student)
        try:
            with patch("app.api.admin.admin_academics.list_students") as svc:
                resp = client.get("/api/v1/admin/me")
        finally:
            _clear()
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
        svc.assert_not_called()

    def test_institution_admin_cannot_escalate_to_organization_scope(self):
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_organization(
                _user(user_id=USER_INST_A1), ctx, ORG_A
            )
        assert exc.value.code == "FORBIDDEN"

    def test_institution_a_admin_cannot_reach_institution_b(self):
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_institution(
                _user(user_id=USER_INST_A1), ctx, INST_B1
            )
        assert exc.value.code == "TENANT_MISMATCH"

    def test_org_a_admin_cannot_reach_org_b(self):
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_organization(_user(user_id=USER_ORG_A), ctx, ORG_B)
        assert exc.value.code == "ORGANIZATION_MISMATCH"

    def test_scope_columns_cannot_be_widened_by_client(self):
        """scope_type / scope_id sent in a decision body are rejected."""
        _as(_user(user_id=USER_ORG_A))
        try:
            resp = client.post(
                f"/api/v1/institutions/join-requests/{JR_A}/decision",
                json={
                    "decision": "approve",
                    "role": "admin",
                    "scope_type": "platform",
                    "scope_id": ORG_B,
                    "organization_id": ORG_B,
                },
            )
        finally:
            _clear()
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_login_cannot_supply_role_or_scope(self):
        base = {"email": "u@example.com", "password": "secret123"}
        for extra in (
            {"role": "admin"},
            {"roles": ["admin"]},
            {"scope_type": "platform"},
            {"scope_id": ORG_A},
            {"organization_id": ORG_A},
            {"institution_id": INST_A1},
        ):
            resp = client.post("/api/v1/auth/login", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)

    def test_student_login_cannot_supply_identity_fields(self):
        base = {"identifier": "student@college.edu", "password": "pw123456"}
        for extra in (
            {"role": "admin"},
            {"user_id": USER_STUDENT_A1},
            {"student_id": STUDENT_ID_A1},
            {"institution_id": INST_B1},
            {"approval_status": "approved"},
        ):
            resp = client.post(
                "/api/v1/auth/student/login", json={**base, **extra}
            )
            assert resp.status_code == 422, (extra, resp.text)
    def test_public_registration_cannot_supply_role_scope_or_identity(self):
        base = {
            "institution_code": "IMPHAL",
            "email": "new@college.edu",
            "password": "secret123",
            "first_name": "New",
            "last_name": "Student",
            "registration_type": "student",
            "register_number": "REG1",
        }
        for extra in (
            {"role": "admin"},
            {"scope_type": "platform"},
            {"user_id": USER_STUDENT_A1},
            {"student_id": STUDENT_ID_A1},
            {"institution_id": INST_B1},
            {"approval_status": "approved"},
        ):
            resp = client.post("/api/v1/users/register", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)

    def test_organization_registration_cannot_supply_role_or_status(self):
        base = {
            "name": "New Org",
            "organization_code": "NEWORG",
            "official_email": "info@neworg.example.com",
            "contact_information": "contact@neworg.example.com",
            "admin_email": "admin@neworg.example.com",
            "admin_password": "secret123",
            "admin_first_name": "Org",
            "admin_last_name": "Admin",
        }
        for extra in (
            {"role": "admin"},
            {"scope_type": "platform"},
            {"status": "active"},
            {"join_code": "HACKED"},
        ):
            resp = client.post("/api/v1/organizations/register", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)

    def test_institution_registration_cannot_supply_org_or_role(self):
        base = {
            "name": "New Campus",
            "institution_code": "NEWCAMP",
            "organization_code": "ACME",
            "official_email": "info@newcamp.example.com",
            "admin_email": "admin@newcamp.example.com",
            "admin_password": "secret123",
            "admin_first_name": "Inst",
            "admin_last_name": "Admin",
        }
        for extra in (
            {"organization_id": ORG_B},
            {"role": "admin"},
            {"status": "active"},
            {"is_active": True},
        ):
            resp = client.post("/api/v1/institutions/register", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)

    def test_client_student_id_path_substitution_denied(self):
        """A student's /me path uses the JWT identity, never a student id."""
        student = _user(INST_A1, roles=("student",), user_id=USER_STUDENT_A1)
        _as(student)
        try:
            with patch(
                "app.services.student_data.get_own_student",
                return_value={
                    "student_id": STUDENT_ID_A1,
                    "user_id": student["user_id"],
                    "institution_id": INST_A1,
                },
            ), patch(
                "app.services.student_data.results_repo.get_student_result_with_items",
                return_value={
                    "student_id": STUDENT_ID_B1,
                    "status": "published",
                    "institution_id": INST_B1,
                },
            ):
                resp = client.get(f"/api/v1/students/me/results/{STUDENT_ID_B1}")
        finally:
            _clear()
        # A foreign result is indistinguishable from "not found" (404).
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESULT_NOT_FOUND"
# ===========================================================================
# 5. Registration security
# ===========================================================================


def _deep_values(obj):
    """Yield every string/number value found anywhere in a nested structure."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from _deep_values(value)
    elif isinstance(obj, (list, tuple, set)):
        for value in obj:
            yield from _deep_values(value)
    elif obj is not None:
        yield str(obj)


class TestRegistrationSecurity:
    """Registration can never grant privileges or cross tenants."""

    def test_registration_type_admin_is_unrepresentable(self):
        base = {
            "institution_code": "IMPHAL",
            "email": "admin-wannabe@college.edu",
            "password": "secret123",
            "first_name": "Wan",
            "last_name": "Nabe",
        }
        for role in ("admin", "institution_admin", "organization_admin"):
            resp = client.post(
                "/api/v1/users/register",
                json={**base, "registration_type": role},
            )
            assert resp.status_code == 422, (role, resp.text)
            assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_organization_registration_grants_only_server_chosen_admin_scope(self):
        from app.schemas.tenancy import OrganizationRegistrationRequest
        from app.services import tenancy as svc

        payload = OrganizationRegistrationRequest(
            name="New Org",
            organization_code="neworg",
            official_email="info@neworg.example.com",
            contact_information="contact",
            admin_email="admin@neworg.example.com",
            admin_password="secret123",
            admin_first_name="Org",
            admin_last_name="Admin",
        )
        fake = _FakeClient({})
        calls = {}
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(tenancy_repo, "organization_code_exists", return_value=False),
            patch.object(tenancy_repo, "get_user_by_email", return_value=None),
            patch.object(svc, "_create_auth_account", return_value="auth-id"),
            patch.object(svc, "_create_public_user", return_value=USER_ORG_A),
            patch.object(
                tenancy_repo, "get_role_by_name", return_value={"role_id": ROLE_ID}
            ),
        ):

            def _assign(db, **kwargs):
                calls.update(kwargs)
                return {}

            with patch.object(
                tenancy_repo, "assign_user_role_scope", side_effect=_assign
            ):
                response = svc.register_organization(payload)

        assert calls["role_id"] == ROLE_ID
        assert calls["scope_type"] == "organization"
        assert calls["scope_id"] == calls["scope_organization_id"]
        assert response.status == "pending"
    def test_institution_registration_uses_server_resolved_organization(self):
        """A client cannot bypass organization ownership by supplying ids."""
        from app.schemas.tenancy import InstitutionRegistrationRequest
        from app.services import tenancy as svc

        payload = InstitutionRegistrationRequest(
            name="New Campus",
            institution_code="NEWCAMP",
            organization_code="BETA",
            official_email="info@newcamp.example.com",
            admin_email="admin@newcamp.example.com",
            admin_password="secret123",
            admin_first_name="Inst",
            admin_last_name="Admin",
        )
        fake = _FakeClient({})
        inserted = {}
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_organization_by_code",
                return_value=_org_row(ORG_B, "active"),
            ),
            patch.object(tenancy_repo, "institution_code_exists", return_value=False),
            patch.object(tenancy_repo, "get_user_by_email", return_value=None),
            patch.object(svc, "_create_auth_account", return_value="auth-id"),
            patch.object(svc, "_create_public_user", return_value=USER_INST_A1),
            patch.object(
                tenancy_repo, "get_role_by_name", return_value={"role_id": ROLE_ID}
            ),
            patch.object(tenancy_repo, "assign_user_role_scope", return_value={}),
            patch.object(tenancy_repo, "insert_join_request", return_value={}),
        ):

            def _insert(db, **kwargs):
                inserted.update(kwargs)
                return {
                    "institution_id": INST_B1,
                    "organization_id": kwargs["organization_id"],
                    "code": kwargs["code"],
                    "status": "pending",
                }

            with patch.object(tenancy_repo, "insert_institution", side_effect=_insert):
                response = svc.register_institution(payload)

        # The institution is bound to the SERVER-RESOLVED organization (B).
        assert inserted["organization_id"] == ORG_B
        assert response.organization_id == UUID(ORG_B)
        assert response.status == "pending"

    def test_institution_registration_rejects_non_active_organization(self):
        from app.schemas.tenancy import InstitutionRegistrationRequest
        from app.services import tenancy as svc

        payload = InstitutionRegistrationRequest(
            name="New Campus",
            institution_code="NEWCAMP",
            organization_code="BETA",
            official_email="info@newcamp.example.com",
            admin_email="admin@newcamp.example.com",
            admin_password="secret123",
            admin_first_name="Inst",
            admin_last_name="Admin",
        )
        fake = _FakeClient({})
        for status in ("pending", "rejected", "suspended"):
            with (
                patch.object(svc, "get_admin_client", return_value=fake),
                patch.object(
                    tenancy_repo,
                    "get_organization_by_code",
                    return_value=_org_row(ORG_B, status),
                ),
            ):
                with pytest.raises(AppError) as exc:
                    svc.register_institution(payload)
            assert exc.value.status_code == 403
            assert exc.value.code == "ORGANIZATION_NOT_ACCEPTING_REQUESTS"
    def test_users_cannot_register_into_non_active_institution(self):
        from app.schemas.users import UserRegistrationRequest
        from app.services import user_registration as svc

        payload = UserRegistrationRequest(
            registration_type="student",
            institution_code="PENDINGC",
            email="new@college.edu",
            password="secret123",
            first_name="New",
            last_name="Student",
            register_number="REG-1",
        )
        fake = _FakeClient({})
        for status in ("pending", "rejected", "suspended"):
            with (
                patch.object(svc, "get_admin_client", return_value=fake),
                patch.object(
                    tenancy_repo,
                    "get_institution_by_code",
                    return_value=_inst_row(INST_A1, ORG_A, status),
                ),
            ):
                with pytest.raises(AppError) as exc:
                    svc.register_user(payload)
            assert exc.value.status_code == 403
            assert exc.value.code == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"

    def test_duplicate_email_registration_rejected(self):
        from app.schemas.users import UserRegistrationRequest
        from app.services import user_registration as svc

        payload = UserRegistrationRequest(
            registration_type="student",
            institution_code="IMPHAL",
            email="dupe@college.edu",
            password="secret123",
            first_name="Dupe",
            last_name="Student",
            register_number="REG-2",
        )
        fake = _FakeClient({})
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_institution_by_code",
                return_value=_inst_row(INST_A1, ORG_A, "active"),
            ),
            patch.object(
                svc.student_svc,
                "_find_user_by_email",
                return_value={"user_id": USER_STUDENT_A1},
            ),
            patch.object(
                svc.academics_repo, "get_student_by_user_id", return_value=None
            ),
        ):
            with pytest.raises(AppError) as exc:
                svc.register_user(payload)
        assert exc.value.status_code == 409
        assert exc.value.code == "EMAIL_ALREADY_REGISTERED"

    def test_duplicate_academic_identifier_rejected(self):
        """The existing institution-scoped duplicate guard is enforced."""
        from app.schemas.users import UserRegistrationRequest
        from app.services import user_registration as svc

        payload = UserRegistrationRequest(
            registration_type="student",
            institution_code="IMPHAL",
            email="new@college.edu",
            password="secret123",
            first_name="New",
            last_name="Student",
            register_number="REG-DUP",
        )
        fake = _FakeClient({})
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_institution_by_code",
                return_value=_inst_row(INST_A1, ORG_A, "active"),
            ),
            patch.object(svc.student_svc, "_find_user_by_email", return_value=None),
            patch.object(
                svc.student_svc,
                "_assert_no_duplicate_identities",
                side_effect=AppError(
                    "Register number already registered",
                    status_code=409,
                    code="REGISTER_NUMBER_ALREADY_REGISTERED",
                ),
            ) as guard,
        ):
            with pytest.raises(AppError) as exc:
                svc.register_user(payload)
        assert exc.value.code == "REGISTER_NUMBER_ALREADY_REGISTERED"
        guard.assert_called_once()

    def test_registration_password_never_reaches_application_tables(self):
        """The password goes ONLY to Supabase Auth (GoTrue)."""
        from app.schemas.users import UserRegistrationRequest
        from app.services import user_registration as svc

        secret = "Sup3rSecret!Pass"
        payload = UserRegistrationRequest(
            registration_type="student",
            institution_code="IMPHAL",
            email="new@college.edu",
            password=secret,
            first_name="New",
            last_name="Student",
            register_number="REG-PW",
        )
        fake = _FakeClient({})
        auth_calls = []
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_institution_by_code",
                return_value=_inst_row(INST_A1, ORG_A, "active"),
            ),
            patch.object(svc.student_svc, "_find_user_by_email", return_value=None),
            patch.object(
                svc.student_svc, "_assert_no_duplicate_identities", return_value=None
            ),
            patch.object(
                svc.student_svc,
                "_create_auth_account",
                side_effect=lambda email, pw: auth_calls.append(pw) or "auth-id",
            ),
            patch.object(
                svc.student_svc, "_create_public_user", return_value=USER_STUDENT_A1
            ),
        ):
            response = svc.register_user(payload)

        # The password was handed to GoTrue exactly once...
        assert auth_calls == [secret]
        # ...and never written into any application table row.
        app_tables = {
            k: v for k, v in fake.state.items() if k not in {"accesses"}
        }
        for value in _deep_values(app_tables):
            assert secret not in value
        # Neither is it exposed on the response.
        assert secret not in response.model_dump_json()
# ===========================================================================
# 6. Approval security
# ===========================================================================


class TestApprovalSecurity:
    """Only the correct authority can decide; cross-tenant decisions fail."""

    def test_only_platform_authority_can_approve_organization(self):
        for scope_type, scope_id in (
            (authz.ORGANIZATION, ORG_A),
            (authz.INSTITUTION, INST_A1),
        ):
            ctx = _resolve([_role_row(scope_type, scope_id, ORG_A)])
            with pytest.raises(AppError) as exc:
                authz._assert_platform_authority(ctx)
            assert exc.value.status_code == 403
            assert exc.value.code == "FORBIDDEN"
        # Platform scope is the only accepted authority.
        authz._assert_platform_authority(
            _resolve([_role_row(authz.PLATFORM, None, None)])
        )

    def test_organization_admin_cannot_self_approve_own_organization(self):
        from app.schemas.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["organizations"] = [_org_row(ORG_A, "pending")]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_organization(
                    _user(user_id=USER_ORG_A),
                    ctx,
                    ORG_A,
                    ApprovalDecisionRequest(decision="approve"),
                )
        assert exc.value.status_code == 403
        assert exc.value.code == "FORBIDDEN"
        # The organization is still pending — no self-activation happened.
        assert state["organizations"][0]["status"] == "pending"

    def test_platform_admin_can_approve_pending_organization(self):
        from app.schemas.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["organizations"] = [_org_row(ORG_A, "pending")]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.PLATFORM, None, None)])
        with (
            patch.object(tenancy_svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo, "update_join_requests_for_organization", return_value=[]
            ),
        ):
            response = tenancy_svc.decide_organization(
                _user(user_id=USER_PLATFORM),
                ctx,
                ORG_A,
                ApprovalDecisionRequest(decision="approve"),
            )
        assert response.status == "approve"
        assert state["organizations"][0]["status"] == "active"

    def test_institution_admin_cannot_approve_join_request(self):
        from app.schemas.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["institution_join_requests"] = [
            {
                "join_request_id": JR_A,
                "organization_id": ORG_A,
                "institution_id": INST_A1,
                "status": "pending",
            }
        ]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_join_request(
                    _user(INST_A1, user_id=USER_INST_A1),
                    ctx,
                    JR_A,
                    ApprovalDecisionRequest(decision="approve"),
                )
        assert exc.value.status_code == 403
        assert state["institution_join_requests"][0]["status"] == "pending"

    def test_org_admin_can_decide_own_join_request(self):
        from app.schemas.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["institution_join_requests"] = [
            {
                "join_request_id": JR_A,
                "organization_id": ORG_A,
                "institution_id": INST_A1,
                "status": "pending",
            }
        ]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            response = tenancy_svc.decide_join_request(
                _user(user_id=USER_ORG_A),
                ctx,
                JR_A,
                ApprovalDecisionRequest(decision="approve"),
            )
        assert response.status == "approve"
        assert state["institution_join_requests"][0]["status"] == "approved"
        institution = state["institutions"][0]
        assert institution["institution_id"] == INST_A1
        assert institution["status"] == "active"
        assert institution["is_active"] is True

    def test_repeated_join_request_decision_is_safe(self):
        from app.schemas.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["institution_join_requests"] = [
            {
                "join_request_id": JR_A,
                "organization_id": ORG_A,
                "institution_id": INST_A1,
                "status": "approved",
            }
        ]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_join_request(
                    _user(user_id=USER_ORG_A),
                    ctx,
                    JR_A,
                    ApprovalDecisionRequest(decision="approve"),
                )
        assert exc.value.status_code == 422
        assert exc.value.code == "JOIN_REQUEST_NOT_PENDING"
        assert state["institution_join_requests"][0]["status"] == "approved"

    def test_repeated_organization_decision_is_safe(self):
        from app.schemas.tenancy import ApprovalDecisionRequest

        state = _base_state()
        state["organizations"] = [_org_row(ORG_A, "active")]
        fake = _FakeClient(state)
        ctx = _resolve([_role_row(authz.PLATFORM, None, None)])
        with patch.object(tenancy_svc, "get_admin_client", return_value=fake):
            with pytest.raises(AppError) as exc:
                tenancy_svc.decide_organization(
                    _user(user_id=USER_PLATFORM),
                    ctx,
                    ORG_A,
                    ApprovalDecisionRequest(decision="reject"),
                )
        assert exc.value.status_code == 422
        assert exc.value.code == "ORGANIZATION_NOT_PENDING"
        assert state["organizations"][0]["status"] == "active"

    def test_rejected_organization_cannot_accept_institution_requests(self):
        from app.schemas.tenancy import InstitutionRegistrationRequest
        from app.services import tenancy as svc

        payload = InstitutionRegistrationRequest(
            name="New Campus",
            institution_code="NEWCAMP",
            organization_code="BETA",
            official_email="info@newcamp.example.com",
            admin_email="admin@newcamp.example.com",
            admin_password="secret123",
            admin_first_name="Inst",
            admin_last_name="Admin",
        )
        fake = _FakeClient({})
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_organization_by_code",
                return_value=_org_row(ORG_B, "rejected"),
            ),
        ):
            with pytest.raises(AppError) as exc:
                svc.register_institution(payload)
        assert exc.value.status_code == 403
        assert exc.value.code == "ORGANIZATION_NOT_ACCEPTING_REQUESTS"

    def test_pending_organization_admin_denied_platform_only_authority(self):
        """A pending org's admin keeps management but never approval authority."""
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz._assert_platform_authority(ctx)
        assert exc.value.code == "FORBIDDEN"
# ===========================================================================
# 7. Authentication security
# ===========================================================================

LOGIN_URL = "/api/v1/auth/login"
STUDENT_LOGIN_URL = "/api/v1/auth/student/login"


def _gos_true_client(success=True, email="user@example.com"):
    auth = MagicMock()
    if not success:
        auth.auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid login credentials", 400, "invalid_grant"
        )
        return auth
    session = MagicMock()
    session.access_token = "mock-access-token"
    user = MagicMock()
    user.id = USER_PLATFORM
    user.email = email
    auth.auth.sign_in_with_password.return_value = MagicMock(session=session, user=user)
    return auth


def _sign_in_account(**overrides):
    account = {
        "user_id": USER_PLATFORM,
        "status": "active",
        "institution_id": None,
        "approval_status": None,
        "student_is_active": None,
    }
    account.update(overrides)
    return account


def _login(account, auth=None, email="user@example.com", db=None):
    auth = auth or _gos_true_client(email=email)
    db = db if db is not None else MagicMock()
    with (
        patch("app.api.auth.create_supabase_client", return_value=auth),
        patch(
            "app.api.auth.get_sign_in_context",
            new=AsyncMock(return_value=account),
        ),
        patch("app.api.auth.get_admin_client", return_value=db),
    ):
        return client.post(LOGIN_URL, json={"email": email, "password": "secret123"})


def _institution_db(is_active=True):
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single
        .return_value.execute.return_value.data
    ) = {
        "institution_id": INST_A1,
        "name": "Campus",
        "code": "IMPHAL",
        "status": "active" if is_active else "suspended",
        "is_active": is_active,
    }
    return db


class TestAuthenticationSecurity:
    """Valid credentials work; every lifecycle / identity bypass fails closed."""

    def test_valid_credentials_work(self):
        resp = _login(_sign_in_account())
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"] == "mock-access-token"

    def test_invalid_credentials_fail(self):
        resp = _login(
            _sign_in_account(), auth=_gos_true_client(success=False)
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_missing_public_user_row_denied(self):
        resp = _login(None)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_inactive_user_status_denied(self):
        resp = _login(_sign_in_account(status="inactive"))
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_pending_student_cannot_bypass_sign_in(self):
        resp = _login(
            _sign_in_account(
                institution_id=INST_A1, approval_status="pending", student_is_active=True
            ),
            db=_institution_db(),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_rejected_student_cannot_bypass_sign_in(self):
        resp = _login(
            _sign_in_account(
                institution_id=INST_A1, approval_status="rejected", student_is_active=True
            ),
            db=_institution_db(),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_inactive_institution_blocks_sign_in(self):
        """An approved student of a suspended institution cannot sign in."""
        resp = _login(
            _sign_in_account(
                institution_id=INST_A1, approval_status="approved", student_is_active=True
            ),
            db=_institution_db(is_active=False),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_approved_student_of_active_institution_can_sign_in(self):
        resp = _login(
            _sign_in_account(
                institution_id=INST_A1, approval_status="approved", student_is_active=True
            ),
            db=_institution_db(is_active=True),
        )
        assert resp.status_code == 200, resp.text

    def _student_login(self, payload, result=None, error=None):
        with patch(
            "app.api.student_auth.authenticate_student",
            side_effect=error if error else None,
            return_value=None if error else result,
        ) as svc:
            resp = client.post(STUDENT_LOGIN_URL, json=payload)
        return resp, svc

    def test_student_email_login_works(self):
        result = {
            "access_token": "student-token",
            "user": {"id": USER_STUDENT_A1, "email": "student@college.edu"},
        }
        resp, svc = self._student_login(
            {"identifier": "student@college.edu", "password": "secret123"}, result=result
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"] == "student-token"
        assert svc.call_args.args[0] == "student@college.edu"

    def test_register_number_login_works(self):
        result = {
            "access_token": "student-token",
            "user": {"id": USER_STUDENT_A1, "email": "student@college.edu"},
        }
        resp, svc = self._student_login(
            {
                "identifier": "REG-1001",
                "password": "secret123",
                "institution_code": "IMPHAL",
            },
            result=result,
        )
        assert resp.status_code == 200, resp.text
        assert svc.call_args.args[0] == "REG-1001"
        assert svc.call_args.args[2] == "IMPHAL"

    def test_university_roll_number_login_works(self):
        result = {
            "access_token": "student-token",
            "user": {"id": USER_STUDENT_A1, "email": "student@college.edu"},
        }
        resp, svc = self._student_login(
            {
                "identifier": "ROLL-2024-77",
                "password": "secret123",
                "institution_code": "IMPHAL",
            },
            result=result,
        )
        assert resp.status_code == 200, resp.text
        assert svc.call_args.args[0] == "ROLL-2024-77"

    def test_academic_identifier_without_institution_code_rejected(self):
        resp, svc = self._student_login(
            {"identifier": "REG-1001", "password": "secret123"}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
        svc.assert_not_called()

    def test_identity_resolution_requires_institution_code(self):
        from app.services.student_auth import _resolve_identity

        db = MagicMock()
        assert _resolve_identity(db, "REG-1001", None) is None
        assert _resolve_identity(db, "ROLL-2024-77", None) is None

    def test_admin_credentials_cannot_produce_student_session(self):
        resp, _ = self._student_login(
            {"identifier": "admin@college.edu", "password": "secret123"},
            error=SafeAuthFailure(),
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_inactive_institution_blocks_student_login(self):
        """The Phase 6.5 institution gate is enforced inside the service."""
        from app.services.student_auth import authenticate_student

        db = _institution_db(is_active=False)
        with (
            patch("app.services.student_auth.get_admin_client", return_value=db),
            patch(
                "app.services.student_auth._resolve_identity",
                return_value=("student@college.edu", UUID(INST_A1), {
                    "email": "student@college.edu",
                    "approval_status": "approved",
                    "is_active": True,
                    "institution_id": INST_A1,
                }),
            ),
        ):
            with pytest.raises(SafeAuthFailure):
                authenticate_student(
                    "student@college.edu", "secret123", "IMPHAL"
                )
# ===========================================================================
# 8. Public AI security (retrieval / context boundary)
# ===========================================================================


class TestPublicAISecurity:
    """Public AI is unauthenticated, server-tenant-resolved, public-only."""

    def test_public_chat_requires_no_authentication(self):
        from app.main import public_chat as public_chat_endpoint
        from app.services import public_chat

        source = inspect.getsource(public_chat.process_chat_request)
        assert "get_current_user" not in source
        # The public endpoint itself declares no auth dependency.
        signature = inspect.signature(public_chat_endpoint)
        for param in signature.parameters.values():
            default = param.default
            assert getattr(default, "dependency", None) is not get_current_user

    def test_public_institution_is_resolved_server_side(self):
        from app.services import public_chat

        source = inspect.getsource(public_chat._validate_public_institution)
        assert "get_institution_by_id" in source
        assert "get_organization_by_id" in source

    def test_inactive_institution_cannot_use_public_ai(self):
        for status in ("pending", "rejected", "suspended"):
            state = _base_state()
            state["institutions"] = [_inst_row(INST_A1, ORG_A, status)]
            fake = _FakeClient(state)
            with pytest.raises(AppError) as exc:
                _run_public_chat(fake, _chat_request())
            assert exc.value.status_code == 403
            assert exc.value.code == "INSTITUTION_NOT_ACTIVE"

    def test_inactive_organization_blocks_public_ai(self):
        state = _base_state()
        state["organizations"] = [_org_row(ORG_A, "suspended"), _org_row(ORG_B, "active")]
        fake = _FakeClient(state)
        with pytest.raises(AppError) as exc:
            _run_public_chat(fake, _chat_request())
        assert exc.value.status_code == 403
        assert exc.value.code == "ORGANIZATION_NOT_ACTIVE"

    def test_unknown_institution_denied(self):
        fake = _FakeClient(_base_state())
        with pytest.raises(AppError) as exc:
            _run_public_chat(fake, _chat_request(institution_id=uuid4()))
        assert exc.value.status_code == 404
        assert exc.value.code == "INSTITUTION_NOT_FOUND"

    def test_private_document_chunk_never_reaches_llm(self):
        fake = _FakeClient(_base_state())
        request = _chat_request(
            retrieved_chunks=[
                _retrieved_chunk(CHUNK_FAQ_A1, RUN_FAQ_A1, "Public handbook fact"),
                _retrieved_chunk(
                    CHUNK_PRIVATE_A1, RUN_PRIVATE_A1, "CONFIDENTIAL private doc"
                ),
            ]
        )
        _, provider = _run_public_chat(fake, request)
        texts = [c.text for c in provider.contexts[0].retrieved_knowledge]
        assert "Public handbook fact" in texts
        assert "CONFIDENTIAL private doc" not in texts

    def test_explicit_private_knowledge_source_denied(self):
        fake = _FakeClient(_base_state())
        with pytest.raises(AppError) as exc:
            _run_public_chat(
                fake, _chat_request(knowledge_source_id=KS_PRIVATE_A1)
            )
        assert exc.value.status_code == 403
        assert exc.value.code == "KNOWLEDGE_SOURCE_NOT_PUBLIC"

    def test_student_records_never_read_by_public_ai(self):
        """The public path never touches student/academic tables at all."""
        fake = _FakeClient(_base_state())
        request = _chat_request(
            retrieved_chunks=[
                _retrieved_chunk(CHUNK_FAQ_A1, RUN_FAQ_A1, "Public handbook fact")
            ]
        )
        _run_public_chat(fake, request)
        accesses = set(fake.state["accesses"])
        forbidden = {
            "students",
            "student_attendance",
            "attendance",
            "student_test_results",
            "test_results",
            "student_results",
            "results",
            "users",
        }
        assert not (accesses & forbidden), accesses

    def test_personalized_queries_require_protected_access(self):
        for question in (
            "What is my attendance?",
            "What are my test results?",
            "What was my CGPA?",
        ):
            fake = _FakeClient(_base_state())
            with pytest.raises(AppError) as exc:
                _run_public_chat(fake, _chat_request(query=question))
            assert exc.value.status_code == 401
            assert exc.value.code == "AUTH_REQUIRED"

    def test_general_policy_question_remains_public(self):
        """A policy question that merely mentions attendance stays public."""
        fake = _FakeClient(_base_state())
        request = _chat_request(
            query="What attendance percentage is required?",
            retrieved_chunks=[
                _retrieved_chunk(CHUNK_FAQ_A1, RUN_FAQ_A1, "Attendance policy fact")
            ],
        )
        response, _ = _run_public_chat(fake, request)
        assert response.status == "success"
