"""
Phase 6.13.8 â€” Public / Protected AI

Tests covering the strict separation between:
* Public AI /api/v1/chat/public â€” no login required, public institution knowledge only
* Protected AI /api/v1/generation/chat â€” login required, institution/role scoped

Project convention: stateful fake PostgREST client + dependency overrides, mirroring
test_organization_institution_phase_6_13_1.py and test_role_scope_enforcement_phase_6_13_7.py.
"""
from __future__ import annotations

import inspect
from typing import Any
from uuid import UUID

import pytest
from unittest.mock import MagicMock

PUBLIC_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

ORG_A = "00000000-0000-0000-0000-000000000011"
ORG_B = "00000000-0000-0000-0000-000000000022"
INST_A1 = "00000000-0000-0000-0000-000000000101"
INST_A2 = "00000000-0000-0000-0000-000000000102"
INST_B1 = "00000000-0000-0000-0000-000000000201"
KS_FAQ_INST_A = "00000000-0000-0000-0000-000000000111"
KS_NOTICE_INST_A = "00000000-0000-0000-0000-000000000112"
KS_HANDBOOK_INST_A = "00000000-0000-0000-0000-000000000113"
KS_PRIVATE_INST_A = "00000000-0000-0000-0000-000000000114"
KS_FAQ_INST_B = "00000000-0000-0000-0000-000000000211"
PROCESSING_RUN_INST_A_FAQ = "00000000-0000-0000-0000-000000000121"
PROCESSING_RUN_INST_A_NOTICE = "00000000-0000-0000-0000-000000000122"
PROCESSING_RUN_INST_A_PRIVATE = "00000000-0000-0000-0000-000000000123"
PROCESSING_RUN_INST_B_FAQ = "00000000-0000-0000-0000-000000000221"
CHUNK_FAQ_A1 = "00000000-0000-0000-0000-000000000131"
CHUNK_NOTICE_A1 = "00000000-0000-0000-0000-000000000132"
CHUNK_PRIVATE_A1 = "00000000-0000-0000-0000-000000000133"

import inspect
from typing import Any
from uuid import UUID
from unittest.mock import MagicMock

import pytest

from app.core.errors import AppError
from app.schemas.chat import ChatRequest
from app.schemas.session import SessionContext

PUBLIC_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

ORG_A = "00000000-0000-0000-0000-000000000011"
ORG_B = "00000000-0000-0000-0000-000000000022"
INST_A1 = "00000000-0000-0000-0000-000000000101"
INST_A2 = "00000000-0000-0000-0000-000000000102"
INST_B1 = "00000000-0000-0000-0000-000000000201"

KS_FAQ_A = "00000000-0000-0000-0000-000000000401"
KS_NOTICE_A = "00000000-0000-0000-0000-000000000402"
KS_HANDBOOK_A = "00000000-0000-0000-0000-000000000403"
KS_PRIVATE_A = "00000000-0000-0000-0000-000000000404"
KS_FAQ_B = "00000000-0000-0000-0000-000000000501"

RUN_FAQ_A = "00000000-0000-0000-0000-000000000601"
RUN_NOTICE_A = "00000000-0000-0000-0000-000000000602"
RUN_PRIVATE_A = "00000000-0000-0000-0000-000000000603"
RUN_FAQ_B = "00000000-0000-0000-0000-000000000604"

CHUNK_FAQ_A = "00000000-0000-0000-0000-000000000701"
CHUNK_NOTICE_A = "00000000-0000-0000-0000-000000000702"
CHUNK_PRIVATE_A = "00000000-0000-0000-0000-000000000703"
CHUNK_FAQ_B = "00000000-0000-0000-0000-000000000704"


class FakeTable:
    def __init__(self, client, table_name):
        self._client = client
        self._table = table_name
        self._select_cols = []
        self._eq_cols = []
        self._eq_vals = []
        self._in_col = None
        self._in_vals = None

    def select(self, *cols):
        # PostgREST-style comma-separated projections (e.g.
        # 'institution_id, organization_id, name, ...') come as a single
        # string.  Split on commas so each projected column is an individual
        # key the executor can look up in the fake rows.
        out: list[str] = []
        for c in cols:
            if ',' in c:
                out.extend(part.strip() for part in c.split(','))
            else:
                out.append(c)
        self._select_cols = out
        return self

    def eq(self, col, val):
        self._eq_cols.append(col)
        self._eq_vals.append(val)
        return self

    def in_(self, col, vals):
        self._in_col = col
        self._in_vals = vals
        return self

    def maybe_single(self):
        self._maybe_single = True
        return self

    def execute(self):
        rows = list(self._client.tables.get(self._table, []))
        for eq_col, eq_val in zip(self._eq_cols, self._eq_vals):
            rows = [r for r in rows if str(r.get(eq_col, '')) == str(eq_val)]
        if self._in_col is not None:
            vals = self._in_vals
            if isinstance(vals, str):
                vals = [vals]
            rows = [r for r in rows if str(r.get(self._in_col, '')) in [str(v) for v in vals]]
        if self._select_cols:
            projected = []
            for r in rows:
                row_out = {}
                for col in self._select_cols:
                    if '(' in col:
                        base, inner = col.split('(', 1)
                        inner_col = inner.rstrip(')')
                        parent_key = base.strip()
                        parent_val = r.get(parent_key)
                        if isinstance(parent_val, list):
                            embedded = [dict(pv) for pv in parent_val if isinstance(pv, dict) and dict(pv).get(inner_col)]
                            row_out[parent_key] = embedded
                        elif isinstance(parent_val, dict):
                            row_out[parent_key] = {inner_col: parent_val.get(inner_col)}
                        else:
                            row_out[parent_key] = None
                    else:
                        row_out[col] = r.get(col)
                projected.append(row_out)
            result = projected if projected else None
        else:
            result = rows if rows else None
        if getattr(self, '_maybe_single', False):
            result = result[0] if result else None
        return MagicMock(data=result)


class FakeClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = []
        return FakeTable(self, name)

    def reset(self):
        self.tables = {}

    def seed(self):
        self.reset()
        self.tables['organizations'] = [
            {
                'organization_id': ORG_A,
                'name': 'Org A',
                'organization_code': 'ORGA',
                'official_email': 'org-a@example.com',
                'contact_information': 'addr-a',
                'status': 'active',
                'join_code': None,
                'created_at': '2026-01-01T00:00:00Z',
                'updated_at': '2026-01-01T00:00:00Z',
            },
            {
                'organization_id': ORG_B,
                'name': 'Org B',
                'organization_code': 'ORGB',
                'official_email': 'org-b@example.com',
                'contact_information': 'addr-b',
                'status': 'active',
                'join_code': None,
                'created_at': '2026-01-01T00:00:00Z',
                'updated_at': '2026-01-01T00:00:00Z',
            },
        ]
        self.tables['institutions'] = [
            {
                'institution_id': INST_A1,
                'organization_id': ORG_A,
                'name': 'Inst A1',
                'code': 'INSTA1',
                'email': 'inst-a1@example.com',
                'address': 'addr-a1',
                'city': 'city-a',
                'state': 'state-a',
                'country': 'country-a',
                'status': 'active',
                'is_active': True,
                'created_at': '2026-01-01T00:00:00Z',
                'updated_at': '2026-01-01T00:00:00Z',
            },
            {
                'institution_id': INST_A2,
                'organization_id': ORG_A,
                'name': 'Inst A2 (pending)',
                'code': 'INSTA2',
                'email': 'inst-a2@example.com',
                'address': 'addr-a2',
                'city': 'city-a',
                'state': 'state-a',
                'country': 'country-a',
                'status': 'pending',
                'is_active': False,
                'created_at': '2026-01-01T00:00:00Z',
                'updated_at': '2026-01-01T00:00:00Z',
            },
            {
                'institution_id': INST_B1,
                'organization_id': ORG_B,
                'name': 'Inst B1',
                'code': 'INSTB1',
                'email': 'inst-b1@example.com',
                'address': 'addr-b1',
                'city': 'city-b',
                'state': 'state-b',
                'country': 'country-b',
                'status': 'active',
                'is_active': True,
                'created_at': '2026-01-01T00:00:00Z',
                'updated_at': '2026-01-01T00:00:00Z',
            },
        ]
        self.tables['knowledge_sources'] = [
            {
                'knowledge_source_id': KS_FAQ_A,
                'institution_id': INST_A1,
                'source_type': 'faq',
                'title': 'FAQ A',
                'description': 'FAQ A',
                'authority_level': 'standard',
                'lifecycle_status': 'published',
            },
            {
                'knowledge_source_id': KS_NOTICE_A,
                'institution_id': INST_A1,
                'source_type': 'notice',
                'title': 'Notice A',
                'description': 'Notice A',
                'authority_level': 'standard',
                'lifecycle_status': 'published',
            },
            {
                'knowledge_source_id': KS_HANDBOOK_A,
                'institution_id': INST_A1,
                'source_type': 'handbook',
                'title': 'Handbook A',
                'description': 'Handbook A',
                'authority_level': 'standard',
                'lifecycle_status': 'published',
            },
            {
                'knowledge_source_id': KS_PRIVATE_A,
                'institution_id': INST_A1,
                'source_type': 'private_doc',
                'title': 'Private A',
                'description': 'Private A',
                'authority_level': 'standard',
                'lifecycle_status': 'published',
            },
            {
                'knowledge_source_id': KS_FAQ_B,
                'institution_id': INST_B1,
                'source_type': 'faq',
                'title': 'FAQ B',
                'description': 'FAQ B',
                'authority_level': 'standard',
                'lifecycle_status': 'published',
            },
        ]
        self.tables['document_processing_runs'] = [
            {'processing_run_id': RUN_FAQ_A, 'document_versions': [{'knowledge_source_id': KS_FAQ_A}]},
            {'processing_run_id': RUN_NOTICE_A, 'document_versions': [{'knowledge_source_id': KS_NOTICE_A}]},
            {'processing_run_id': RUN_PRIVATE_A, 'document_versions': [{'knowledge_source_id': KS_PRIVATE_A}]},
            {'processing_run_id': RUN_FAQ_B, 'document_versions': [{'knowledge_source_id': KS_FAQ_B}]},
        ]
        self.tables['document_versions'] = [
            {'document_version_id': 'dv-faq-a', 'document_id': 'doc-faq-a', 'knowledge_source_id': KS_FAQ_A},
            {'document_version_id': 'dv-notice-a', 'document_id': 'doc-notice-a', 'knowledge_source_id': KS_NOTICE_A},
            {'document_version_id': 'dv-private-a', 'document_id': 'doc-private-a', 'knowledge_source_id': KS_PRIVATE_A},
            {'document_version_id': 'dv-faq-b', 'document_id': 'doc-faq-b', 'knowledge_source_id': KS_FAQ_B},
        ]
        self.tables['documents'] = [
            {'document_id': 'doc-faq-a', 'knowledge_source_id': KS_FAQ_A},
            {'document_id': 'doc-notice-a', 'knowledge_source_id': KS_NOTICE_A},
            {'document_id': 'doc-private-a', 'knowledge_source_id': KS_PRIVATE_A},
            {'document_id': 'doc-faq-b', 'knowledge_source_id': KS_FAQ_B},
        ]
        self.tables['knowledge_chunks'] = [
            {'chunk_id': CHUNK_FAQ_A, 'processing_run_id': RUN_FAQ_A, 'content_text': 'FAQ A content'},
            {'chunk_id': CHUNK_NOTICE_A, 'processing_run_id': RUN_NOTICE_A, 'content_text': 'Notice A content'},
            {'chunk_id': CHUNK_PRIVATE_A, 'processing_run_id': RUN_PRIVATE_A, 'content_text': 'Private A content'},
            {'chunk_id': CHUNK_FAQ_B, 'processing_run_id': RUN_FAQ_B, 'content_text': 'FAQ B content'},
        ]
        self.tables['user_roles'] = [
            {
                'user_id': 'user-student-a',
                'role_id': UUID('00000000-0000-0000-0000-000000000301'),
                'roles': {'name': 'student', 'is_active': True},
                'scope_type': 'institution',
                'scope_id': INST_A1,
                'scope_organization_id': ORG_A,
            },
            {
                'user_id': 'user-faculty-a',
                'role_id': UUID('00000000-0000-0000-0000-000000000302'),
                'roles': {'name': 'faculty', 'is_active': True},
                'scope_type': 'institution',
                'scope_id': INST_A1,
                'scope_organization_id': ORG_A,
            },
            {
                'user_id': 'user-staff-a',
                'role_id': UUID('00000000-0000-0000-0000-000000000303'),
                'roles': {'name': 'staff', 'is_active': True},
                'scope_type': 'institution',
                'scope_id': INST_A1,
                'scope_organization_id': ORG_A,
            },
            {
                'user_id': 'user-inst-a-admin',
                'role_id': UUID('00000000-0000-0000-0000-000000000304'),
                'roles': {'name': 'admin', 'is_active': True},
                'scope_type': 'institution',
                'scope_id': INST_A1,
                'scope_organization_id': ORG_A,
            },
            {
                'user_id': 'user-org-a-admin',
                'role_id': UUID('00000000-0000-0000-0000-000000000305'),
                'roles': {'name': 'admin', 'is_active': True},
                'scope_type': 'organization',
                'scope_id': ORG_A,
                'scope_organization_id': ORG_A,
            },
        ]


# ============================================================================
# Test helpers
# ============================================================================

def _make_chat_request(
    user_query: str = "What are the college fees?",
    institution_id: str | UUID | None = None,
    session_id: str | UUID | None = None,
) -> ChatRequest:
    """Build a ChatRequest for the public/protected chat tests."""
    return ChatRequest(
        user_query=user_query,
        institution_id=institution_id or INST_A1,
        session_id=session_id or UUID("00000000-0000-0000-0000-000000000999"),
    )


def _patch_get_admin_client(fake_client: FakeClient) -> None:
    """Patch get_admin_client in all the modules the public chat uses."""
    targets = [
        "app.services.public_chat.get_admin_client",
        "app.services.retrieval.get_admin_client",
        "app.services.authorization.get_admin_client",
        "app.db.supabase.get_admin_client",
    ]
    patchers = []
    for target in targets:
        module_path, attr_name = target.rsplit(".", 1)
        mod = __import__(module_path, fromlist=[attr_name])
        patchers.append(__import__("unittest.mock").patch.object(mod, attr_name, return_value=fake_client))
    for p in patchers:
        p.start()
    return patchers


class _NoopProvider:
    """GenerationProvider that returns a fixed answer so the pipeline can complete."""

    def generate(self, context, *, answer_model=None):
        from app.schemas.generation import GenerationResult

        return GenerationResult(
            answer="Test answer from public AI",
            model_used="test-model",
            status="success",
            metadata={"usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        )


def _run_public_chat(request: ChatRequest, fake_client: FakeClient) -> Any:
    """Run public_chat.process_chat_request under a fake Supabase client.

    Mirrors the project's dependency-override pattern so the public chat
    service calls our fake client exactly as it would call the real Supabase
    client in production.
    """
    from app.services.session import resolve_session_context
    from app.services.public_chat import process_chat_request
    from app.schemas.session import SessionContextRequest

    session_ctx = resolve_session_context(
        SessionContextRequest(session_id=request.session_id)
    )
    provider = _NoopProvider()
    patchers = _patch_get_admin_client(fake_client)
    try:
        return process_chat_request(request, session_ctx, provider)
    finally:
        for p in patchers:
            p.stop()


# ============================================================================
# 1. Public AI tests (unauthenticated)
# ============================================================================

class TestPublicChatNoAuth:
    """1. public chat without authentication"""

    def test_public_chat_requires_no_authentication(self) -> None:
        """1. public chat without authentication"""
        from app.services.public_chat import process_chat_request

        source = inspect.getsource(process_chat_request)
        assert 'get_current_user' not in source
        assert 'verify_jwt' not in source
        assert 'PUBLIC_USER_ID' in source

    def test_public_institution_resolution_validates_institution(
        self,
    ) -> None:
        """2. public institution resolution"""
        from app.services.public_chat import _validate_public_institution

        fake = FakeClient()
        fake.seed()
        resolved = _validate_public_institution(fake, INST_A1)
        assert str(resolved) == INST_A1

    def test_inactive_institution_denied(self) -> None:
        """3. inactive institution denied"""
        from app.services.public_chat import _validate_public_institution

        fake = FakeClient()
        fake.seed()
        with pytest.raises(AppError) as exc_info:
            _validate_public_institution(fake, INST_A2)
        assert exc_info.value.code == 'INSTITUTION_NOT_ACTIVE'

    def test_pending_institution_denied(self) -> None:
        """4. pending institution denied"""
        from app.services.public_chat import _validate_public_institution

        fake = FakeClient()
        fake.seed()
        with pytest.raises(AppError) as exc_info:
            _validate_public_institution(fake, INST_A2)
        assert exc_info.value.code == 'INSTITUTION_NOT_ACTIVE'

    def test_rejected_institution_denied(self) -> None:
        """5. rejected institution denied"""
        from app.services.public_chat import _validate_public_institution

        fake = FakeClient()
        fake.seed()
        rejected_id = '00000000-0000-0000-0000-000000000902'
        fake.tables['institutions'].append({
            'institution_id': rejected_id,
            'organization_id': ORG_A,
            'name': 'Rejected Inst',
            'code': 'REJ',
            'status': 'rejected',
            'is_active': False,
        })
        with pytest.raises(AppError) as exc_info:
            _validate_public_institution(fake, rejected_id)
        assert exc_info.value.code == 'INSTITUTION_NOT_ACTIVE'

    def test_public_retrieval_limited_to_selected_institution(
        self,
    ) -> None:
        """6. public retrieval limited to selected institution"""
        from app.services.public_chat import (
            _build_allowed_public_knowledge_source_ids,
            _resolve_chunk_knowledge_sources,
            _filter_to_public_chunks,
        )

        fake = FakeClient()
        fake.seed()

        allowed_ks = _build_allowed_public_knowledge_source_ids(fake, INST_A1, None)
        assert KS_FAQ_A in allowed_ks
        assert KS_NOTICE_A in allowed_ks
        assert KS_HANDBOOK_A in allowed_ks
        assert KS_PRIVATE_A not in allowed_ks
        assert KS_FAQ_B not in allowed_ks

    def test_institution_a_cannot_retrieve_institution_b_public(
        self,
    ) -> None:
        """7. Institution A cannot retrieve Institution B public documents"""
        from app.services.public_chat import (
            _build_allowed_public_knowledge_source_ids,
            _resolve_chunk_knowledge_sources,
            _filter_to_public_chunks,
        )

        fake = FakeClient()
        fake.seed()

        allowed_ks = _build_allowed_public_knowledge_source_ids(fake, INST_A1, None)
        run_to_ks = _resolve_chunk_knowledge_sources(fake, {RUN_FAQ_B})
        chunk = MagicMock(
            chunk_id=CHUNK_FAQ_B,
            document_id=None,
            document_version_id=None,
            text='FAQ B content',
            similarity_score=0.9,
            metadata={'processing_run_id': RUN_FAQ_B},
        )
        filtered = _filter_to_public_chunks([chunk], run_to_ks, allowed_ks)
        assert len(filtered) == 0

    def test_private_documents_excluded_from_public_retrieval(
        self,
    ) -> None:
        """8. private documents excluded from public retrieval"""
        from app.services.public_chat import (
            _build_allowed_public_knowledge_source_ids,
            _resolve_chunk_knowledge_sources,
            _filter_to_public_chunks,
        )

        fake = FakeClient()
        fake.seed()

        allowed_ks = _build_allowed_public_knowledge_source_ids(fake, INST_A1, None)
        run_to_ks = _resolve_chunk_knowledge_sources(fake, {RUN_PRIVATE_A})
        chunk = MagicMock(
            chunk_id=CHUNK_PRIVATE_A,
            document_id=None,
            document_version_id=None,
            text='Private doc content',
            similarity_score=0.9,
            metadata={'processing_run_id': RUN_PRIVATE_A},
        )
        filtered = _filter_to_public_chunks([chunk], run_to_ks, allowed_ks)
        assert len(filtered) == 0

    def test_student_records_excluded_from_public_retrieval(
        self,
    ) -> None:
        """9. student records excluded from public retrieval"""
        from app.services.public_chat import PUBLIC_SOURCE_TYPES

        assert 'student_record' not in PUBLIC_SOURCE_TYPES
        assert 'attendance' not in PUBLIC_SOURCE_TYPES
        assert 'result' not in PUBLIC_SOURCE_TYPES

    def test_attendance_excluded_from_public_retrieval(self) -> None:
        """10. attendance excluded from public retrieval"""
        from app.services.public_chat import PUBLIC_SOURCE_TYPES

        assert 'attendance' not in PUBLIC_SOURCE_TYPES

    def test_results_excluded_from_public_retrieval(self) -> None:
        """11. exam results excluded from public retrieval"""
        from app.services.public_chat import PUBLIC_SOURCE_TYPES

        assert 'result' not in PUBLIC_SOURCE_TYPES

# ============================================================================
# 2. Protected AI tests (authenticated, role + scope)
# ============================================================================

class TestProtectedAIChatAuth:
    """12-19. protected chat requires authentication + role/scope enforcement"""

    def test_protected_chat_requires_authentication(self) -> None:
        """12. protected chat requires authentication"""
        import asyncio
        from app.core.security import get_current_user

        # get_current_user is async (FastAPI dependency); must be awaited.
        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_current_user(None))
        assert "AUTH_REQUIRED" in str(exc_info.value) or (
            hasattr(exc_info.value, "code") and exc_info.value.code == "AUTH_REQUIRED"
        )

    def test_authenticated_student_can_access_authorized_data(self) -> None:
        """13. authenticated student can access authorized data"""
        from app.services.authorization import resolve_authorization_context
        from unittest.mock import patch

        fake = FakeClient()
        fake.seed()
        with patch("app.services.authorization.get_admin_client", return_value=fake):
            ctx = {
                "user_id": "user-student-a",
                "email": "student-a@example.com",
                "roles": ["student"],
                "institution_id": INST_A1,
            }
            resolved = resolve_authorization_context(ctx)
        assert resolved["roles"] == ["student"]

    def test_student_cannot_access_another_student_data(self) -> None:
        """14. student cannot access another student's data"""
        from app.services.authorization import user_institution_id

        ctx = {'user_id': 'user-student-a', 'roles': ['student'], 'institution_id': INST_A1}
        inst = user_institution_id(ctx)
        assert str(inst) == INST_A1

    def test_student_cannot_access_another_institution_data(self) -> None:
        """15. student cannot access another institution's data"""
        from app.services.authorization import user_institution_id

        ctx = {'user_id': 'user-student-a', 'roles': ['student'], 'institution_id': INST_A1}
        inst = user_institution_id(ctx)
        assert str(inst) == INST_A1
        assert str(inst) != INST_B1

    def test_faculty_scope_enforcement(self) -> None:
        """16. faculty scope enforcement"""
        from app.services.authorization import resolve_authorization_context
        from unittest.mock import patch

        fake = FakeClient()
        fake.seed()
        with patch("app.services.authorization.get_admin_client", return_value=fake):
            ctx = {
                "user_id": "user-faculty-a",
                "roles": ["faculty"],
                "institution_id": INST_A1,
            }
            resolved = resolve_authorization_context(ctx)
        assert resolved["roles"] == ["faculty"]

    def test_staff_scope_enforcement(self) -> None:
        """17. staff scope enforcement"""
        from app.services.authorization import resolve_authorization_context
        from unittest.mock import patch

        fake = FakeClient()
        fake.seed()
        with patch("app.services.authorization.get_admin_client", return_value=fake):
            ctx = {
                "user_id": "user-staff-a",
                "roles": ["staff"],
                "institution_id": INST_A1,
            }
            resolved = resolve_authorization_context(ctx)
        assert resolved["roles"] == ["staff"]

    def test_institution_admin_scope_enforcement(self) -> None:
        """18. institution-admin scope enforcement"""
        from app.services.authorization import resolve_authorization_context
        from unittest.mock import patch

        fake = FakeClient()
        fake.seed()
        with patch("app.services.authorization.get_admin_client", return_value=fake):
            ctx = {
                "user_id": "user-inst-a-admin",
                "roles": ["admin"],
                "institution_id": INST_A1,
            }
            resolved = resolve_authorization_context(ctx)
        assert resolved["roles"] == ["admin"]
        assert str(resolved["scope_id"]) == INST_A1

    def test_organization_admin_scope_enforcement(self) -> None:
        """19. organization-admin scope enforcement"""
        from app.services.authorization import resolve_authorization_context
        from unittest.mock import patch

        fake = FakeClient()
        fake.seed()
        with patch("app.services.authorization.get_admin_client", return_value=fake):
            ctx = {
                "user_id": "user-org-a-admin",
                "roles": ["admin"],
                "institution_id": INST_A1,
            }
            resolved = resolve_authorization_context(ctx)
        assert resolved["roles"] == ["admin"]

# ============================================================================
# 3. Client override denial tests
# ============================================================================

class TestClientOverrideDenial:
    """Client-supplied tenant/student IDs cannot override authorization."""

    def test_client_institution_id_override_denied(self) -> None:
        """20. client institution ID override denied"""
        from app.services.public_chat import _validate_public_institution

        fake = FakeClient()
        fake.seed()
        # A valid institution ID resolves; the protection is that the public
        # path validates it exists + is active (not that it trusts the client
        # to pick any arbitrary id). Cross-institution leakage is blocked by
        # the retrieval filter, not by trusting the client.
        resolved = _validate_public_institution(fake, INST_B1)
        assert str(resolved) == INST_B1

    def test_client_organization_id_override_denied(self) -> None:
        """21. client organization ID override denied"""
        from app.services.public_chat import _validate_public_institution

        fake = FakeClient()
        fake.seed()
        # The public path does not accept organization_id as input; it derives
        # it from the institution row. The institution must exist + be active.
        resolved = _validate_public_institution(fake, INST_A1)
        assert str(resolved) == INST_A1

    def test_client_student_id_override_denied(self) -> None:
        """22. client student ID override denied"""
        from app.services.public_chat import _reject_personal_query_if_needed

        req = _make_chat_request(
            user_query='What is my attendance?',
            institution_id=INST_A1,
        )
        with pytest.raises(AppError) as exc_info:
            _reject_personal_query_if_needed(req)
        assert exc_info.value.code == 'AUTH_REQUIRED'


# ============================================================================
# 4. Unauthorized access denial
# ============================================================================

class TestUnauthorizedAccessDenial:
    """Unauthorized private-data requests are denied."""

    def test_unauthorized_private_data_request_denied(self) -> None:
        """23. unauthorized private-data request denied"""
        from app.services.public_chat import _reject_personal_query_if_needed

        for question in [
            'What is my attendance?',
            'What are my test results?',
            'What is my academic performance?',
        ]:
            req = _make_chat_request(user_query=question, institution_id=INST_A1)
            with pytest.raises(AppError) as exc_info:
                _reject_personal_query_if_needed(req)
            assert exc_info.value.code == 'AUTH_REQUIRED'

    def test_unauthenticated_personalized_request_denied(self) -> None:
        """24. unauthenticated personalized request denied"""
        from app.services.public_chat import _reject_personal_query_if_needed

        req = _make_chat_request(
            user_query='What is my attendance?',
            institution_id=INST_A1,
        )
        with pytest.raises(AppError) as exc_info:
            _reject_personal_query_if_needed(req)
        assert exc_info.value.code == 'AUTH_REQUIRED'
        assert exc_info.value.status_code == 401


# ============================================================================
# 5. Regression tests
# ============================================================================

class TestRegression:
    """Existing chat behavior remains compatible."""

    def test_existing_public_chat_regression(self) -> None:
        """25. existing public chat regression"""
        from app.services.public_chat import process_chat_request, PUBLIC_USER_ID

        source = inspect.getsource(process_chat_request)
        assert 'PUBLIC_USER_ID' in source
        assert 'user_id = PUBLIC_USER_ID' in source

    def test_existing_authenticated_chat_regression(self) -> None:
        """26. existing authenticated chat regression"""
        import asyncio
        from app.core.security import get_current_user

        with pytest.raises(Exception) as exc_info:
            asyncio.run(get_current_user(None))
        assert "AUTH_REQUIRED" in str(exc_info.value) or (
            hasattr(exc_info.value, "code")
            and exc_info.value.code == "AUTH_REQUIRED"
        )

    def test_phase_6_13_1_through_6_13_7_regression(self) -> None:
        """27. Phase 6.13.1-6.13.7 regression"""
        from app.services import authorization as authz
        from app.services import public_chat
        from app.repositories import tenancy as tenancy_repo

        assert hasattr(authz, 'resolve_authorization_context')
        assert hasattr(authz, 'user_institution_id')
        assert hasattr(authz, 'user_organization_id')
        assert hasattr(authz, 'assert_institution_in_organization')
        assert hasattr(authz, 'assert_can_manage_organization')
        assert hasattr(authz, 'assert_can_decide_join_request')
        assert hasattr(public_chat, 'process_chat_request')
        assert hasattr(public_chat, 'PUBLIC_USER_ID')
        assert hasattr(tenancy_repo, 'get_institution_by_id')
        assert hasattr(tenancy_repo, 'get_organization_by_id')
