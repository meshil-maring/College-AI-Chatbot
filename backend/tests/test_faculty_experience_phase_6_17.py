"""Phase 6.17 — Faculty Experience & Academic Workspace Foundation.

Backend security tests for the faculty role. NO production backend behaviour
is changed by Phase 6.17: the faculty experience is built ONLY on the
server-authoritative contracts that already exist. This suite PINS that
contract map so the frontend faculty shell can never drift into privilege:

Verified faculty capability map (source of truth = the backend):

    GET  /api/v1/auth/me                         -> role "faculty" + tenant   (ALLOWED)
    GET  /api/v1/conversations                   -> any authenticated user    (ALLOWED)
    POST /api/v1/documents/ingest (+ pipeline)   -> require_roles(admin,
                                                    staff, faculty)          (ALLOWED)
    GET  /api/v1/students/me/*                   -> student-only identity
                                                    chain                    (404 STUDENT_PROFILE_NOT_FOUND)
    *    /api/v1/admin/* (attendance, results,
         notices, resources, students, ...)      -> require_roles("admin")    (403 FORBIDDEN)

Tenant isolation and ownership are enforced server-side; none of the tests
below rely on frontend filtering.
"""

import io
from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import resolve_primary_role
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"
INSTITUTION_B = "30000000-0000-0000-0000-000000000002"
USER_ID = "30000000-0000-0000-0000-000000000201"

FACULTY_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "faculty@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

FACULTY_USER = {
    "id": USER_ID,
    "user_id": USER_ID,
    "auth_user_id": FACULTY_CLAIMS["sub"],
    "email": FACULTY_CLAIMS["email"],
    "roles": ["faculty"],
    "institution_id": INSTITUTION_A,
}

AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def _patch_faculty_auth(user=FACULTY_USER):
    """Authenticate every request as the faculty principal."""
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.core.security.verify_jwt", return_value=FACULTY_CLAIMS)
        )
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=user),
            )
        )
        yield


# ---------------------------------------------------------------------------
# 1. Faculty role resolution (server-authoritative, /auth/me)
# ---------------------------------------------------------------------------


def test_resolve_primary_role_returns_faculty():
    assert resolve_primary_role(["faculty"]) == "faculty"


def test_auth_me_returns_faculty_role_with_tenant():
    """Faculty identity: canonical role + tenant resolved SERVER-SIDE."""
    with _patch_faculty_auth():
        response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["role"] == "faculty"
    assert body["institution_id"] == INSTITUTION_A
    assert body["email"] == FACULTY_CLAIMS["email"]


def test_auth_me_faculty_multi_role_precedence_unchanged():
    """admin > staff > faculty > student precedence is untouched."""
    assert resolve_primary_role(["student", "faculty"]) == "faculty"
    assert resolve_primary_role(["faculty", "staff"]) == "staff"
    assert resolve_primary_role(["faculty", "admin"]) == "admin"


# ---------------------------------------------------------------------------
# 2. Faculty -> student-only endpoints DENIED (no student profile contract)
# ---------------------------------------------------------------------------


def _assert_faculty_denied_on_student_endpoint(path: str) -> None:
    with _patch_faculty_auth(), patch(
        "app.repositories.admin_academics.get_student_by_user_id",
        return_value=None,
    ):
        response = client.get(path, headers=AUTH_HEADERS)
    assert response.status_code == 404, f"{path}: {response.status_code}"
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"

def test_faculty_cannot_read_own_student_profile():
    _assert_faculty_denied_on_student_endpoint("/api/v1/students/me/profile")


def test_faculty_cannot_read_student_attendance():
    _assert_faculty_denied_on_student_endpoint("/api/v1/students/me/attendance")


def test_faculty_cannot_read_student_attendance_summary():
    _assert_faculty_denied_on_student_endpoint("/api/v1/students/me/attendance/summary")


def test_faculty_cannot_read_student_results():
    _assert_faculty_denied_on_student_endpoint("/api/v1/students/me/results")


def test_faculty_cannot_read_student_test_results():
    _assert_faculty_denied_on_student_endpoint("/api/v1/students/me/test-results")


def test_faculty_cannot_read_student_academic_profile():
    _assert_faculty_denied_on_student_endpoint("/api/v1/students/me/academic-profile")


def test_faculty_cannot_read_student_notices():
    _assert_faculty_denied_on_student_endpoint("/api/v1/students/me/notices")


def test_faculty_cannot_read_student_resources():
    _assert_faculty_denied_on_student_endpoint("/api/v1/students/me/resources")


def test_faculty_identity_parameters_cannot_widen_student_scope():
    """Client-supplied identity values can never become an authorization
    mechanism: the student identity chain ignores them and still fails
    closed for a faculty principal (no student profile)."""
    with _patch_faculty_auth(), patch(
        "app.repositories.admin_academics.get_student_by_user_id",
        return_value=None,
    ):
        response = client.get(
            "/api/v1/students/me/notices",
            params={"institution_id": INSTITUTION_B, "student_id": "x"},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# 3. Faculty -> privileged admin endpoints DENIED (403 FORBIDDEN)
# ---------------------------------------------------------------------------


def _assert_faculty_forbidden(method: str, path: str, **kwargs) -> None:
    with _patch_faculty_auth():
        response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
    assert response.status_code == 403, f"{method} {path}: {response.status_code}"
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_faculty_denied_admin_identity():
    _assert_faculty_forbidden("GET", "/api/v1/admin/me")


def test_faculty_denied_admin_dashboard():
    _assert_faculty_forbidden("GET", "/api/v1/admin/dashboard")


def test_faculty_denied_admin_student_list():
    _assert_faculty_forbidden("GET", "/api/v1/admin/students")


def test_faculty_denied_admin_pending_students():
    _assert_faculty_forbidden("GET", "/api/v1/admin/students/pending")


def test_faculty_denied_admin_attendance_create():
    _assert_faculty_forbidden(
        "POST",
        "/api/v1/admin/attendance",
        json={
            "student_id": "30000000-0000-0000-0000-000000000301",
            "date": "2026-01-01",
            "status": "present",
        },
    )


def test_faculty_denied_admin_results_create():
    _assert_faculty_forbidden(
        "POST",
        "/api/v1/admin/results",
        json={},
    )


def test_faculty_denied_admin_notices_list():
    _assert_faculty_forbidden("GET", "/api/v1/admin/notices")


def test_faculty_denied_admin_notice_create():
    _assert_faculty_forbidden("POST", "/api/v1/admin/notices", json={})


def test_faculty_denied_admin_knowledge_sources():
    _assert_faculty_forbidden(
        "GET",
        f"/api/v1/admin/knowledge-sources?institution_id={INSTITUTION_B}",
    )


def test_faculty_denied_admin_student_approval():
    """Approval is admin/staff only; faculty is NOT in _APPROVAL."""
    _assert_faculty_forbidden(
        "POST",
        "/api/v1/admin/students/30000000-0000-0000-0000-000000000301/approve",
    )


def test_faculty_denied_admin_audit_logs():
    _assert_faculty_forbidden("GET", "/api/v1/admin/audit-logs")


# ---------------------------------------------------------------------------
# 4. Faculty -> AI Assistant ALLOWED (existing authenticated chat path)
# ---------------------------------------------------------------------------


def test_faculty_can_list_own_conversations():
    """Conversations authenticate with get_current_user (any role) and scope
    to the authenticated user_id server-side."""
    with _patch_faculty_auth(), patch(
        "app.api.conversations.get_user_conversations",
        return_value=[],
    ) as conversations_mock:
        response = client.get("/api/v1/conversations", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == []
    conversations_mock.assert_called_once()


# ---------------------------------------------------------------------------
# 5. Faculty tenant isolation on the authorized ingestion pipeline
# ---------------------------------------------------------------------------


def _ingest_with_tenant(ks_institution: str | None):
    """POST /documents/ingest as faculty against a knowledge source whose
    tenant is controlled by the test. The downstream pipeline is stubbed so
    the test isolates ONLY the role + tenant authorization gate."""
    from app.schemas.ingestion import IngestResponse

    claims = dict(FACULTY_CLAIMS)
    user = dict(FACULTY_USER, institution_id=INSTITUTION_A)
    ks = {"knowledge_source_id": "ks1", "institution_id": ks_institution}
    db = MagicMock()
    stub_response = IngestResponse(
        knowledge_source_id="ks1",
        document_id="doc1",
        document_version_id="dv1",
        processing_run_id="pr1",
        storage_object_key="k",
    )
    with (
        patch("app.core.security.verify_jwt", return_value=claims),
        patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=user)),
        patch("app.api.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_knowledge_source", return_value=ks),
        patch(
            "app.api.ingestion.ingest_document",
            new=AsyncMock(return_value=stub_response),
        ),
    ):
        return client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            data={"knowledge_source_id": "ks1"},
            files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        )


def test_faculty_ingest_allowed_for_own_tenant():
    response = _ingest_with_tenant(INSTITUTION_A)
    # Reaching the pipeline (201) proves the role + tenant gate passed; the
    # pipeline itself is covered by test_ingestion.py.
    assert response.status_code == 201


def test_faculty_ingest_denied_for_cross_tenant_knowledge_source():
    """Faculty A (Institution A) cannot ingest into Institution B's source."""
    response = _ingest_with_tenant(INSTITUTION_B)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"

