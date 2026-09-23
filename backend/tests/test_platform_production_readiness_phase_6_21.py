"""Phase 6.21 - Authenticated Platform Production Readiness regression suite.

Pins VERIFIED production invariants (no new features, no arch changes):
auth/session boundaries, tenant isolation, role gates, registration +
approval safety, storage key hygiene, RAG tenant scoping, generation
failure mapping, conversation ownership, mutation safety, error leakage.
"""

from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import (
    assert_tenant_object,
    require_roles,
    resolve_primary_role,
    scope_tenant,
)
from app.main import app
from app.services.ingestion import _safe_filename, _validate

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "30000000-0000-0000-0000-000000000001"
TENANT_B = "30000000-0000-0000-0000-000000000002"
AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}
USER_ID = "30000000-0000-0000-0000-000000000701"
STUDENT_A = "30000000-0000-0000-0000-000000000101"
STUDENT_B = "30000000-0000-0000-0000-000000000102"
CLAIMS = {"sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "email": "p@college.edu"}


def _user(role="student", tenant=TENANT_A):
    return {
        "user_id": USER_ID,
        "auth_user_id": CLAIMS["sub"],
        "email": f"{role}@college.edu",
        "roles": [role],
        "institution_id": tenant,
    }


@contextmanager
def _auth(role="student", tenant=TENANT_A):
    principal = _user(role, tenant)
    with ExitStack() as stack:
        stack.enter_context(patch("app.core.security.verify_jwt", return_value=dict(CLAIMS)))
        stack.enter_context(
            patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=principal))
        )
        yield principal


def _envelope(response):
    """Return the error envelope; ``code``/``message`` are always present.

    Validation failures (422) additionally carry a ``details`` list — the
    pre-existing contract. No other key is ever allowed, so an accidental
    leak of internals into the envelope is caught here.
    """
    body = response.json()
    assert "error" in body, f"expected error envelope got: {body!r}"
    keys = set(body["error"].keys())
    assert {"code", "message"} <= keys, f"missing envelope keys: {keys}"
    assert keys <= {"code", "message", "details"}, f"unexpected envelope keys: {keys}"
    return body["error"]


def _assert_no_leak(text: str):
    lowered = text.lower()
    for marker in ("traceback", "select ", "supabase", "access_token",
                   "refresh_token", "service_role", "secret", "password"):
        assert marker not in lowered, f"leak {marker!r} in: {text[:300]!r}"


# ---------------------------------------------------------------------------
# 1. Auth + session boundaries
# ---------------------------------------------------------------------------


def test_missing_token_is_401_auth_required():
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert _envelope(r)["code"] == "AUTH_REQUIRED"
    _assert_no_leak(r.text)


def test_malformed_scheme_is_401():
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Token abc"})
    assert r.status_code == 401
    assert _envelope(r)["code"] == "INVALID_SCHEME"


def test_empty_bearer_token_is_401():
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer  "})
    assert r.status_code == 401
    assert _envelope(r)["code"] == "TOKEN_MISSING"


def test_invalid_token_is_401_without_internals():
    with patch("app.core.security.verify_jwt",
               side_effect=AppError("Invalid token", status_code=401, code="INVALID_TOKEN")):
        r = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert r.status_code == 401
    assert _envelope(r)["code"] == "INVALID_TOKEN"
    _assert_no_leak(r.text)


def test_expired_token_is_401_token_expired():
    with patch("app.core.security.verify_jwt",
               side_effect=AppError("Token has expired", status_code=401, code="TOKEN_EXPIRED")):
        r = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert r.status_code == 401
    assert _envelope(r)["code"] == "TOKEN_EXPIRED"


def test_login_rejects_client_role_injection_with_422():
    r = client.post("/api/v1/auth/login",
                    json={"email": "a@college.edu", "password": "secret12", "role": "admin"})
    assert r.status_code == 422
    assert _envelope(r)["code"] == "VALIDATION_ERROR"


def test_auth_me_shape_is_stable_and_minimal():
    with _auth("admin", TENANT_A):
        r = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"authenticated", "user_id", "auth_user_id",
                                "email", "role", "institution_id"}
    assert body["role"] == "admin"
    assert "access_token" not in body


def test_expired_token_on_conversations_is_401():
    with patch("app.core.security.verify_jwt",
               side_effect=AppError("Token has expired", status_code=401, code="TOKEN_EXPIRED")):
        r = client.get("/api/v1/conversations", headers=AUTH_HEADERS)
    assert r.status_code == 401
    assert _envelope(r)["code"] == "TOKEN_EXPIRED"
    _assert_no_leak(r.text)

# ---------------------------------------------------------------------------
# 2. Tenant boundaries
# ---------------------------------------------------------------------------


def test_scope_tenant_rejects_foreign_tenant():
    with pytest.raises(AppError) as exc:
        scope_tenant(_user("student", TENANT_A), TENANT_B)
    assert exc.value.status_code == 403
    assert exc.value.code == "TENANT_MISMATCH"


def test_scope_tenant_defaults_to_own_tenant():
    from uuid import UUID
    assert scope_tenant(_user("student", TENANT_A), None) == UUID(TENANT_A)


def test_assert_tenant_object_rejects_cross_tenant_row():
    with pytest.raises(AppError) as exc:
        assert_tenant_object(_user("admin", TENANT_A), TENANT_B)
    assert exc.value.status_code == 403


def test_assert_tenant_object_allows_global_rows():
    assert_tenant_object(_user("student", TENANT_A), None)


def test_chat_rejects_cross_tenant_institution():
    with _auth("student", TENANT_A):
        r = client.post("/api/v1/generation/chat", headers=AUTH_HEADERS,
                        json={"user_query": "Hello?", "institution_id": TENANT_B})
    assert r.status_code == 403
    assert _envelope(r)["code"] == "TENANT_MISMATCH"
    _assert_no_leak(r.text)


def test_admin_students_list_rejects_foreign_institution():
    with _auth("admin", TENANT_A):
        r = client.get(f"/api/v1/admin/students?institution_id={TENANT_B}",
                       headers=AUTH_HEADERS)
    assert r.status_code == 403
    assert _envelope(r)["code"] == "TENANT_MISMATCH"


# ---------------------------------------------------------------------------
# 3. Role boundaries
# ---------------------------------------------------------------------------


def test_student_cannot_reach_admin_dashboard():
    with _auth("student", TENANT_A):
        r = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert r.status_code == 403
    assert _envelope(r)["code"] == "FORBIDDEN"


def test_faculty_cannot_reach_pending_queue():
    with _auth("faculty", TENANT_A):
        r = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert r.status_code == 403


def test_staff_cannot_reach_admin_only_surface():
    with _auth("staff", TENANT_A):
        r = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert r.status_code == 403


def test_unauthenticated_admin_route_is_401_not_403():
    r = client.get("/api/v1/admin/dashboard")
    assert r.status_code == 401


def test_client_role_values_never_influence_resolution():
    assert resolve_primary_role(["student"]) == "student"
    assert resolve_primary_role(["admin", "student"]) == "admin"
    assert resolve_primary_role(["superadmin", "root"]) is None
    assert resolve_primary_role([]) is None
    assert resolve_primary_role(None) is None


def test_require_roles_denies_without_membership():
    import asyncio
    denied = require_roles("admin")
    with pytest.raises(AppError) as exc:
        asyncio.run(denied(current_user=_user("student", TENANT_A)))
    assert exc.value.status_code == 403

# ---------------------------------------------------------------------------
# 4. Registration + approval security
# ---------------------------------------------------------------------------


def test_registration_rejects_privileged_role_field():
    # first/last name supplied so the ONLY validation failure is the
    # forbidden extra field (proves `extra="forbid"`, not a missing field).
    r = client.post("/api/v1/registration",
                    json={"institution_id": TENANT_A, "email": "n@college.edu",
                          "password": "secret12", "first_name": "Nia",
                          "last_name": "Rao", "register_number": "REG-900",
                          "role": "admin"})
    assert r.status_code == 422
    assert "role" in str(_envelope(r).get("details"))


def test_registration_rejects_approval_status_field():
    r = client.post("/api/v1/registration",
                    json={"institution_id": TENANT_A, "email": "n@college.edu",
                          "password": "secret12", "first_name": "Nia",
                          "last_name": "Rao", "register_number": "REG-901",
                          "approval_status": "approved"})
    assert r.status_code == 422
    assert "approval_status" in str(_envelope(r).get("details"))


def test_registration_unexpected_failure_is_safe_500():
    with patch("app.services.student_registration._register_student",
               side_effect=RuntimeError("SELECT FROM users WHERE boom")):
        r = client.post("/api/v1/registration",
                        json={"institution_id": TENANT_A, "email": "n@college.edu",
                              "password": "secret12", "first_name": "Nia",
                              "last_name": "Rao", "register_number": "REG-903"})
    assert r.status_code == 500
    assert _envelope(r)["code"] == "REGISTRATION_FAILED"
    _assert_no_leak(r.text)
    assert "secret12" not in r.text


def test_duplicate_registration_is_409():
    with patch("app.services.student_registration._register_student",
               side_effect=AppError("dup", status_code=409,
                                    code="EMAIL_ALREADY_REGISTERED")):
        r = client.post("/api/v1/registration",
                        json={"institution_id": TENANT_A, "email": "d@college.edu",
                              "password": "secret12", "first_name": "Dee",
                              "last_name": "Iyer", "register_number": "REG-904"})
    assert r.status_code == 409
    assert _envelope(r)["code"] == "EMAIL_ALREADY_REGISTERED"
    _assert_no_leak(r.text)


def test_student_cannot_approve():
    with _auth("student", TENANT_A):
        r = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve",
                        headers=AUTH_HEADERS)
    assert r.status_code == 403


def test_faculty_cannot_reject():
    with _auth("faculty", TENANT_A):
        r = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject",
                        headers=AUTH_HEADERS)
    assert r.status_code == 403


def test_stale_approval_decision_is_409_without_write():
    # Approval is a strict pending -> approved | rejected state machine. The
    # service resolves the target row before writing, so an already-decided
    # student yields 409 STUDENT_NOT_PENDING and NO update statement runs.
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value \
        .execute.return_value.data = {
            "student_id": STUDENT_A, "user_id": USER_ID,
            "institution_id": TENANT_A, "approval_status": "approved"}
    with (_auth("admin", TENANT_A),
          patch("app.services.admin_academics.get_admin_client", return_value=db)):
        r = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve",
                        headers=AUTH_HEADERS)
    assert r.status_code == 409
    assert _envelope(r)["code"] == "STUDENT_NOT_PENDING"
    db.table.return_value.update.assert_not_called()


def test_cross_tenant_approval_is_403_before_state_read():
    # Tenant mismatch is enforced BEFORE the approval state is disclosed.
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value \
        .execute.return_value.data = {
            "student_id": STUDENT_B, "user_id": USER_ID,
            "institution_id": TENANT_B, "approval_status": "pending"}
    with (_auth("admin", TENANT_A),
          patch("app.services.admin_academics.get_admin_client", return_value=db)):
        r = client.post(f"/api/v1/admin/students/{STUDENT_B}/approve",
                        headers=AUTH_HEADERS)
    assert r.status_code == 403
    assert _envelope(r)["code"] == "TENANT_MISMATCH"
    db.table.return_value.update.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Storage isolation
# ---------------------------------------------------------------------------


def test_safe_filename_strips_traversal():
    assert _safe_filename("../../etc/passwd") == "passwd"
    assert _safe_filename("..\\..\\secret.txt") == "secret.txt"
    assert _safe_filename("/abs/path/doc.pdf") == "doc.pdf"
    assert _safe_filename("") == "upload"


def test_safe_filename_restricts_character_set():
    cleaned = _safe_filename("my report (final)!.pdf")
    assert "/" not in cleaned and "\\" not in cleaned
    assert ".." not in cleaned
    for char in cleaned:
        assert char.isalnum() or char in "._-"


def test_upload_validation_rejects_empty():
    with pytest.raises(AppError) as exc:
        _validate("doc.pdf", "application/pdf", 0)
    assert exc.value.code == "EMPTY_FILE"


def test_upload_validation_rejects_executable():
    with pytest.raises(AppError) as exc:
        _validate("malware.exe", "application/octet-stream", 100)
    assert exc.value.code == "INVALID_FILE_TYPE"


def test_upload_validation_enforces_size_limit():
    from app.config import settings
    with pytest.raises(AppError) as exc:
        _validate("big.pdf", "application/pdf",
                  settings.max_upload_size_mb * 1024 * 1024 + 1)
    assert exc.value.code == "FILE_TOO_LARGE"
    assert exc.value.status_code == 413


def test_ingest_object_key_is_tenant_scoped_and_sanitized():
    import asyncio
    from app.services import ingestion as ingestion_svc
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value \
        .maybe_single.return_value.execute.return_value.data = {
            "knowledge_source_id": "ks-1", "institution_id": TENANT_A}
    upload = MagicMock()
    upload.filename = "../../evil.pdf"
    upload.content_type = "application/pdf"

    async def _fake_read():
        return b"%PDF fake"
    upload.read = _fake_read
    with (patch.object(ingestion_svc, "get_admin_client", return_value=db),
          patch.object(ingestion_svc, "get_r2_client", return_value=MagicMock()),
          patch.object(ingestion_svc, "upload_file", return_value="k") as up_mock,
          patch.object(ingestion_svc, "create_document",
                       return_value={"document_id": "doc-1"}),
          patch.object(ingestion_svc, "create_document_version",
                       return_value={"document_version_id": "dv-1"}),
          patch.object(ingestion_svc, "create_processing_run",
                       return_value={"processing_run_id": "run-1"})):
        result = asyncio.run(ingestion_svc.ingest_document(
            file=upload, knowledge_source_id="ks-1", user_id=USER_ID))
    key = result.storage_object_key
    assert key.startswith(f"{TENANT_A}/ks-1/")
    assert ".." not in key and "\\" not in key
    assert up_mock.call_args[0][2] == key


def test_extraction_failure_response_carries_no_internals():
    run_id = str(uuid4())
    run = {"processing_run_id": run_id, "status": "queued",
           "document_versions": {"document_version_id": str(uuid4()),
                                 "storage_bucket": "b", "storage_object_key": "k",
                                 "file_type": "pdf"}}
    with (_auth("admin", TENANT_A),
          patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
          patch("app.api.ingestion.get_processing_run_with_version", return_value=run),
          patch("app.api.ingestion.update_run_status"),
          patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
          patch("app.api.ingestion.download_file", return_value=b"not a pdf %%%")):
        r = client.post(f"/api/v1/documents/{run_id}/extract", headers=AUTH_HEADERS)
    assert r.status_code == 500
    error = _envelope(r)
    assert error["code"] == "EXTRACTION_FAILED"
    assert error["message"] == "Document processing failed during extraction"
    _assert_no_leak(r.text)


def test_retrieval_forwards_caller_tenant():
    from app.schemas.retrieval import RetrievalRequest
    from app.services import retrieval as retrieval_svc
    captured = {}

    def _fake_search(query_embedding, *, top_k, institution_id=None, **kwargs):
        captured["institution_id"] = institution_id
        return []
    with (patch.object(retrieval_svc, "embed_query", return_value=[0.0] * 1536),
          patch.object(retrieval_svc, "search_chunks", side_effect=_fake_search)):
        retrieval_svc.retrieve(RetrievalRequest(query="fees?", institution_id=TENANT_A))
    assert captured["institution_id"] == TENANT_A


def test_malformed_embedding_is_422_not_500():
    from app.services.retrieval import retrieve_chunks
    with pytest.raises(AppError) as exc:
        retrieve_chunks([0.0] * 8, institution_id=TENANT_A)
    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_QUERY_EMBEDDING"


def test_chat_requires_authentication():
    r = client.post("/api/v1/generation/chat",
                    json={"user_query": "Hi", "institution_id": TENANT_A})
    assert r.status_code == 401


def test_provider_timeout_maps_to_safe_envelope():
    import httpx
    from app.schemas.generation import AIContext
    from app.services.generation_provider import OpenRouterGenerationProvider
    ctx = AIContext(user_question="fees?", system_instructions="sys",
                    grounding_instructions="ground", retrieved_knowledge=[],
                    conversation_history=[])

    def _timeout(request):
        raise httpx.TimeoutException("timed out", request=request)
    provider = OpenRouterGenerationProvider(
        client=httpx.Client(transport=httpx.MockTransport(_timeout)))
    with patch("app.services.generation_provider.settings") as ms:
        ms.openrouter_api_key = "k"
        ms.openrouter_model = "m"
        ms.openrouter_base_url = "https://openrouter.ai/api/v1"
        # The optional attribution headers must stay concrete strings: the
        # provider only sends them when configured, and a MagicMock here would
        # mask the timeout path with an httpx header TypeError.
        ms.openrouter_site_url = ""
        ms.openrouter_app_name = ""
        with pytest.raises(AppError) as exc:
            provider.generate(ctx)
    assert exc.value.code == "AI_PROVIDER_TIMEOUT"
    assert exc.value.status_code == 504


def test_rate_limit_maps_to_429_envelope():
    import httpx
    from app.schemas.generation import AIContext
    from app.services.generation_provider import OpenRouterGenerationProvider
    ctx = AIContext(user_question="q", system_instructions="sys",
                    grounding_instructions="ground", retrieved_knowledge=[],
                    conversation_history=[])
    transport = httpx.MockTransport(lambda request: httpx.Response(429, json={}))
    provider = OpenRouterGenerationProvider(client=httpx.Client(transport=transport))
    with patch("app.services.generation_provider.settings") as ms:
        ms.openrouter_api_key = "k"
        ms.openrouter_model = "m"
        ms.openrouter_base_url = "https://openrouter.ai/api/v1"
        ms.openrouter_site_url = ""
        ms.openrouter_app_name = ""
        with pytest.raises(AppError) as exc:
            provider.generate(ctx)
    assert exc.value.code == "AI_PROVIDER_RATE_LIMIT"
    assert exc.value.status_code == 429


def test_chat_generation_failure_is_safe_500():
    with (_auth("student", TENANT_A),
          patch("app.main.resolve_session_context", return_value=MagicMock()),
          patch("app.main.process_chat_request",
                side_effect=AppError("AI generation failed", status_code=500,
                                     code="GENERATION_FAILED"))):
        r = client.post("/api/v1/generation/chat", headers=AUTH_HEADERS,
                        json={"user_query": "Hello", "institution_id": TENANT_A})
    assert r.status_code == 500
    assert _envelope(r)["code"] == "GENERATION_FAILED"
    _assert_no_leak(r.text)


def test_foreign_conversation_messages_are_404():
    from uuid import UUID
    from app.services import conversation_history as history
    with (patch("app.services.conversation_history.get_admin_client",
                return_value=MagicMock()),
          patch("app.services.conversation_history.get_conversation",
                return_value={"conversation_id": "c", "user_id": STUDENT_B})):
        with pytest.raises(AppError) as exc:
            history.get_conversation_messages(uuid4(), UUID(STUDENT_A))
    assert exc.value.status_code == 404
    assert exc.value.code == "CONVERSATION_NOT_FOUND"


def test_conversation_routes_require_authentication():
    assert client.get("/api/v1/conversations").status_code == 401
    assert client.get(f"/api/v1/conversations/{uuid4()}/messages").status_code == 401


def test_user_a_cannot_read_user_b_conversation_via_api():
    other = str(uuid4())
    with (_auth("student", TENANT_A),
          patch("app.services.conversation_history.get_admin_client",
                return_value=MagicMock()),
          patch("app.services.conversation_history.get_conversation",
                return_value={"conversation_id": other, "user_id": STUDENT_B})):
        r = client.get(f"/api/v1/conversations/{other}/messages", headers=AUTH_HEADERS)
    assert r.status_code == 404
    assert _envelope(r)["code"] == "CONVERSATION_NOT_FOUND"


def test_duplicate_error_mapping_hides_sqlstate():
    # Postgres unique-violation (23505) must be mapped to a business 409 whose
    # message never echoes the SQLSTATE, constraint name, or SQL text.
    from app.services import attendance as attendance_svc
    from app.services import results as results_svc
    for mapper, expected in (
        (attendance_svc._duplicate_error, "ATTENDANCE_DUPLICATE"),
        (results_svc._result_duplicate_error, "RESULT_DUPLICATE"),
        (results_svc._test_result_duplicate_error, "TEST_RESULT_DUPLICATE"),
    ):
        mapped = mapper(Exception(
            'duplicate key value violates unique constraint "students_pkey" (23505)'))
        assert mapped.status_code == 409
        assert mapped.code == expected
        assert "23505" not in mapped.message
        assert "constraint" not in mapped.message.lower()


def test_failed_upload_compensates_orphaned_object():
    import asyncio
    from app.services import ingestion as ingestion_svc
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value \
        .maybe_single.return_value.execute.return_value.data = {
            "knowledge_source_id": "ks-1", "institution_id": TENANT_A}
    upload = MagicMock()
    upload.filename = "doc.pdf"
    upload.content_type = "application/pdf"

    async def _fake_read():
        return b"%PDF fake"
    upload.read = _fake_read
    with (patch.object(ingestion_svc, "get_admin_client", return_value=db),
          patch.object(ingestion_svc, "get_r2_client", return_value=MagicMock()),
          patch.object(ingestion_svc, "upload_file", return_value="k"),
          patch.object(ingestion_svc, "create_document",
                       return_value={"document_id": "d"}),
          patch.object(ingestion_svc, "create_document_version",
                       side_effect=RuntimeError("db down")),
          patch.object(ingestion_svc, "delete_file") as del_mock):
        with pytest.raises(AppError) as exc:
            asyncio.run(ingestion_svc.ingest_document(
                file=upload, knowledge_source_id="ks-1", user_id=USER_ID))
    assert exc.value.code == "REGISTRATION_FAILED"
    del_mock.assert_called_once()


def test_dev_routes_hidden_outside_dev_mode():
    # The dev password-recovery router is gated at ROUTER level, so with
    # DEV_TEST_MODE=false every path answers a flat 404 (feature existence is
    # not disclosed) regardless of payload shape.
    with patch("app.api.dev_auth.settings") as ms:
        ms.dev_test_mode = False
        for path in ("/api/v1/dev/auth/forgot-password",
                     "/api/v1/dev/auth/change-password",
                     "/api/v1/dev/auth/admin/reset-student-password"):
            r = client.post(path, json={})
            assert r.status_code == 404
            assert _envelope(r)["code"] == "NOT_FOUND"
            _assert_no_leak(r.text)


def test_embedding_failure_message_redacts_api_key():
    from app.services.embeddings import _safe_error_message
    with patch("app.services.embeddings.settings") as ms:
        ms.openrouter_api_key = "sk-or-SECRETVALUE"
        cleaned = _safe_error_message(Exception("boom sk-or-SECRETVALUE end"))
    assert "sk-or-SECRETVALUE" not in cleaned
    assert "[redacted]" in cleaned


def test_unhandled_exception_is_generic_500():
    with (patch("app.main.resolve_session_context",
                side_effect=RuntimeError("SELECT boom")),
          _auth("student", TENANT_A)):
        r = client.post("/api/v1/generation/chat", headers=AUTH_HEADERS,
                        json={"user_query": "Hi", "institution_id": TENANT_A})
    assert r.status_code == 500
    assert _envelope(r)["code"] == "INTERNAL_ERROR"
    _assert_no_leak(r.text)


