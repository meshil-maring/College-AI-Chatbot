"""Phase 6.18 — Staff Experience & Operational Workspace Foundation.

Backend security tests for the staff role. NO production backend behaviour
is changed by Phase 6.18: the staff experience is built ONLY on the
server-authoritative contracts that already exist. This suite PINS that
contract map so the frontend staff shell can never drift into privilege:

Verified staff capability map (source of truth = the backend):

    GET  /api/v1/auth/me                        -> role "staff" + tenant  (ALLOWED)
    GET  /api/v1/conversations                  -> any authenticated user (ALLOWED)
    POST /api/v1/documents/ingest (+ pipeline)  -> require_roles(admin,
                                                    staff, faculty)        (ALLOWED, tenant-scoped)
    GET  /api/v1/admin/students/pending         -> require_roles(admin, staff),
                                                    tenant-scoped _approval_scope
                                                    (ALLOWED for tenant-bound staff)
    POST /api/v1/admin/students/{id}/approve    -> require_roles(admin, staff),
                                                    tenant-pinned          (ALLOWED)
    POST /api/v1/admin/students/{id}/reject     -> require_roles(admin, staff),
                                                    tenant-pinned          (ALLOWED)
    GET  /api/v1/students/me/*                  -> student-only identity
                                                    chain                  (404 STUDENT_PROFILE_NOT_FOUND)
    *    /api/v1/admin/* (students CRUD, attendance, results, test-results,
         notices, faqs, knowledge-sources, documents, dashboard, /me,
         audit-logs)                            -> require_roles("admin") (403 FORBIDDEN)

Tenant isolation and ownership are enforced server-side; none of the tests
below rely on frontend filtering.
"""

import io
from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.security import SUPPORTED_ROLES, resolve_primary_role
from app.main import app
from app.repositories.admin_academics import STUDENT_APPROVAL_COLUMNS

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"
INSTITUTION_B = "30000000-0000-0000-0000-000000000002"
USER_ID = "30000000-0000-0000-0000-000000000401"
STUDENT_A = "30000000-0000-0000-0000-000000000301"
STUDENT_B = "30000000-0000-0000-0000-000000000302"

STAFF_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "staff@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

STAFF_USER = {
    "id": USER_ID,
    "user_id": USER_ID,
    "auth_user_id": STAFF_CLAIMS["sub"],
    "email": STAFF_CLAIMS["email"],
    "roles": ["staff"],
    "institution_id": INSTITUTION_A,
}

TENANT_LESS_STAFF_USER = dict(STAFF_USER, institution_id=None)

AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}

PENDING_STUDENT_ROW = {
    "student_id": STUDENT_A,
    "user_id": "u-1",
    "institution_id": INSTITUTION_A,
    "student_number": "STU-0001",
    "email": "student@college.edu",
    "register_number": "REG-001",
    "university_roll_number": None,
    "approval_status": "pending",
    "status": "active",
    "is_active": True,
    "enrollment_date": None,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def _patch_staff_auth(user=STAFF_USER):
    """Authenticate every request as the staff principal."""
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.core.security.verify_jwt", return_value=STAFF_CLAIMS)
        )
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=user),
            )
        )
        yield


def _assert_staff_forbidden(method: str, path: str, **kwargs) -> None:
    """Every admin-only surface must stay 403 FORBIDDEN for staff."""
    with _patch_staff_auth():
        response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
    assert response.status_code == 403, f"{method} {path}: {response.status_code}"
    assert response.json()["error"]["code"] == "FORBIDDEN"


def _assert_staff_denied_on_student_endpoint(path: str) -> None:
    """The /students/me/* identity chain fails closed for a staff principal."""
    with _patch_staff_auth(), patch(
        "app.repositories.admin_academics.get_student_by_user_id",
        return_value=None,
    ):
        response = client.get(path, headers=AUTH_HEADERS)
    assert response.status_code == 404, f"{path}: {response.status_code}"
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# 1. Staff role resolution (server-authoritative, /auth/me)
# ---------------------------------------------------------------------------


def test_resolve_primary_role_returns_staff():
    assert resolve_primary_role(["staff"]) == "staff"


def test_staff_multi_role_precedence_unchanged():
    """admin > staff > faculty > student precedence is untouched."""
    assert resolve_primary_role(["student", "staff"]) == "staff"
    assert resolve_primary_role(["faculty", "staff"]) == "staff"
    assert resolve_primary_role(["staff", "admin"]) == "admin"
    assert resolve_primary_role(list(SUPPORTED_ROLES)) == "admin"


def test_auth_me_returns_staff_role_with_tenant():
    """Staff identity: canonical role + tenant resolved SERVER-SIDE."""
    with _patch_staff_auth():
        response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["role"] == "staff"
    assert body["institution_id"] == INSTITUTION_A
    assert body["email"] == STAFF_CLAIMS["email"]


def test_auth_me_client_role_claims_cannot_override_staff_role():
    """Client-supplied role/institution parameters never override /auth/me."""
    with _patch_staff_auth():
        response = client.get(
            "/api/v1/auth/me",
            headers=AUTH_HEADERS,
            params={"role": "admin", "institution_id": INSTITUTION_B},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "staff"
    assert body["institution_id"] == INSTITUTION_A

# ---------------------------------------------------------------------------
# 2. Staff -> student approval queue ALLOWED (the one verified operational
#    staff contract: require_roles("admin", "staff"), tenant-scoped)
# ---------------------------------------------------------------------------


def test_staff_lists_pending_students_for_own_tenant():
    """Tenant-bound staff always receive their OWN institution's queue; the
    tenant is resolved server-side and no institution_id is needed."""
    with _patch_staff_auth(), patch(
        "app.api.admin.admin_academics.list_pending_approvals",
        return_value=[PENDING_STUDENT_ROW],
    ) as list_mock:
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == [PENDING_STUDENT_ROW]
    list_mock.assert_called_once_with(UUID(INSTITUTION_A), limit=100, offset=0)


def test_staff_own_institution_filter_is_accepted():
    """An own-institution query filter is accepted (Phase 6.4 contract)."""
    with _patch_staff_auth(), patch(
        "app.api.admin.admin_academics.list_pending_approvals",
        return_value=[],
    ) as list_mock:
        response = client.get(
            "/api/v1/admin/students/pending",
            params={"institution_id": INSTITUTION_A},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200
    list_mock.assert_called_once_with(UUID(INSTITUTION_A), limit=100, offset=0)


def test_staff_foreign_institution_filter_rejected_with_tenant_mismatch():
    """A foreign ?institution_id= can never widen the staff queue scope."""
    with _patch_staff_auth(), patch(
        "app.api.admin.admin_academics.list_pending_approvals",
    ) as list_mock:
        response = client.get(
            "/api/v1/admin/students/pending",
            params={"institution_id": INSTITUTION_B},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    list_mock.assert_not_called()

def test_staff_approves_pending_student_within_own_tenant():
    with _patch_staff_auth(), patch(
        "app.api.admin.admin_academics.approve_student",
        return_value=dict(PENDING_STUDENT_ROW, approval_status="approved"),
    ) as approve_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock, patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    approve_mock.assert_called_once_with(UUID(STUDENT_A), UUID(INSTITUTION_A))
    audit_mock.assert_called_once()


def test_staff_rejects_pending_student_within_own_tenant():
    with _patch_staff_auth(), patch(
        "app.api.admin.admin_academics.reject_student",
        return_value=dict(PENDING_STUDENT_ROW, approval_status="rejected"),
    ) as reject_mock, patch(
        "app.api.admin.record_admin_action"
    ), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/reject", headers=AUTH_HEADERS
        )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "rejected"
    reject_mock.assert_called_once_with(UUID(STUDENT_A), UUID(INSTITUTION_A))


def test_staff_cannot_approve_cross_tenant_student():
    """Staff A (Institution A) cannot approve Institution B's student. The
    service enforces tenant BEFORE any state change; no write happens."""
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    with _patch_staff_auth(), patch(
        "app.services.admin_academics.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.services.admin_academics.academics_repo.get_student_for_approval",
        return_value=foreign_student,
    ), patch(
        "app.services.admin_academics.academics_repo.set_student_approval_status"
    ) as write_mock:
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()


def test_staff_cannot_reject_cross_tenant_student():
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    with _patch_staff_auth(), patch(
        "app.services.admin_academics.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.services.admin_academics.academics_repo.get_student_for_approval",
        return_value=foreign_student,
    ), patch(
        "app.services.admin_academics.academics_repo.set_student_approval_status"
    ) as write_mock:
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/reject", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()

def test_platform_level_staff_denied_approval_authority():
    """A tenant-less staff account never gains approval authority (Phase 6.4
    OPTION A: the privilege-escalation surface stays closed)."""
    for method, path in (
        ("GET", "/api/v1/admin/students/pending"),
        ("POST", f"/api/v1/admin/students/{STUDENT_A}/approve"),
        ("POST", f"/api/v1/admin/students/{STUDENT_A}/reject"),
    ):
        with _patch_staff_auth(user=TENANT_LESS_STAFF_USER):
            response = client.request(method, path, headers=AUTH_HEADERS)
        assert response.status_code == 403, f"{method} {path}: {response.status_code}"
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_staff_cannot_widen_approval_scope_with_identity_parameters():
    """student_id/institution_id supplied by the client are never an
    authorization mechanism: approval scope comes from the JWT context."""
    with _patch_staff_auth(), patch(
        "app.api.admin.admin_academics.approve_student",
        return_value=dict(PENDING_STUDENT_ROW, approval_status="approved"),
    ) as approve_mock, patch(
        "app.api.admin.record_admin_action"
    ), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/approve",
            params={"institution_id": INSTITUTION_B, "staff_id": "x"},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200  # body accepts NO fields; params are inert
    approve_mock.assert_called_once_with(UUID(STUDENT_B), UUID(INSTITUTION_A))


# ---------------------------------------------------------------------------
# 3. Staff -> privileged admin surfaces DENIED (403 FORBIDDEN)
# ---------------------------------------------------------------------------


def test_staff_denied_admin_identity():
    _assert_staff_forbidden("GET", "/api/v1/admin/me")


def test_staff_denied_admin_dashboard():
    _assert_staff_forbidden("GET", "/api/v1/admin/dashboard")


def test_staff_denied_admin_student_list():
    _assert_staff_forbidden("GET", "/api/v1/admin/students")


def test_staff_denied_admin_student_read():
    _assert_staff_forbidden("GET", f"/api/v1/admin/students/{STUDENT_A}")


def test_staff_denied_admin_student_update():
    _assert_staff_forbidden("PATCH", f"/api/v1/admin/students/{STUDENT_A}", json={})


def test_staff_denied_admin_student_delete():
    _assert_staff_forbidden("DELETE", f"/api/v1/admin/students/{STUDENT_A}")


def test_staff_denied_admin_attendance_create():
    _assert_staff_forbidden(
        "POST",
        "/api/v1/admin/attendance",
        json={
            "student_id": STUDENT_A,
            "date": "2026-01-01",
            "status": "present",
        },
    )


def test_staff_denied_admin_results_create():
    _assert_staff_forbidden("POST", "/api/v1/admin/results", json={})

def test_staff_denied_admin_student_results():
    _assert_staff_forbidden("GET", f"/api/v1/admin/students/{STUDENT_A}/results")


def test_staff_denied_admin_test_results_create():
    _assert_staff_forbidden("POST", "/api/v1/admin/test-results", json={})


def test_staff_denied_admin_student_test_results():
    _assert_staff_forbidden("GET", f"/api/v1/admin/students/{STUDENT_A}/test-results")


def test_staff_denied_admin_notices_list():
    _assert_staff_forbidden("GET", "/api/v1/admin/notices")


def test_staff_denied_admin_notice_create():
    _assert_staff_forbidden("POST", "/api/v1/admin/notices", json={})


def test_staff_denied_admin_faqs_list():
    _assert_staff_forbidden("GET", "/api/v1/admin/faqs")


def test_staff_denied_admin_knowledge_sources():
    _assert_staff_forbidden(
        "GET", f"/api/v1/admin/knowledge-sources?institution_id={INSTITUTION_A}"
    )


def test_staff_denied_admin_audit_logs():
    _assert_staff_forbidden("GET", "/api/v1/admin/audit-logs")


def test_staff_denied_admin_results_csv_upload():
    _assert_staff_forbidden(
        "POST",
        "/api/v1/admin/results/csv-upload",
        data={"institution_id": INSTITUTION_A},
    )


# ---------------------------------------------------------------------------
# 4. Staff -> student-only endpoints DENIED (no student profile contract)
# ---------------------------------------------------------------------------


def test_staff_cannot_read_own_student_profile():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/profile")


def test_staff_cannot_read_student_attendance():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/attendance")


def test_staff_cannot_read_student_attendance_summary():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/attendance/summary")


def test_staff_cannot_read_student_results():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/results")


def test_staff_cannot_read_student_test_results():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/test-results")


def test_staff_cannot_read_student_academic_profile():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/academic-profile")


def test_staff_cannot_read_student_notices():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/notices")


def test_staff_cannot_read_student_resources():
    _assert_staff_denied_on_student_endpoint("/api/v1/students/me/resources")


def test_staff_identity_parameters_cannot_widen_student_scope():
    """Client-supplied identity values can never become an authorization
    mechanism: the student identity chain ignores them and still fails
    closed for a staff principal (no student profile)."""
    with _patch_staff_auth(), patch(
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
# 5. Staff -> AI Assistant ALLOWED (existing authenticated chat path)
# ---------------------------------------------------------------------------


def test_staff_can_list_own_conversations():
    """Conversations authenticate with get_current_user (any role) and scope
    to the authenticated user_id server-side."""
    with _patch_staff_auth(), patch(
        "app.api.conversations.get_user_conversations",
        return_value=[],
    ) as conversations_mock:
        response = client.get("/api/v1/conversations", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == []
    conversations_mock.assert_called_once()

# ---------------------------------------------------------------------------
# 6. Staff tenant isolation on the authorized ingestion pipeline
# ---------------------------------------------------------------------------


def _ingest_with_tenant(ks_institution: str | None):
    """POST /documents/ingest as staff against a knowledge source whose
    tenant is controlled by the test. The downstream pipeline is stubbed so
    the test isolates ONLY the role + tenant authorization gate."""
    from app.schemas.ingestion import IngestResponse

    claims = dict(STAFF_CLAIMS)
    user = dict(STAFF_USER, institution_id=INSTITUTION_A)
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


def test_staff_ingest_allowed_for_own_tenant():
    response = _ingest_with_tenant(INSTITUTION_A)
    # Reaching the pipeline (201) proves the role + tenant gate passed; the
    # pipeline itself is covered by test_ingestion.py.
    assert response.status_code == 201


def test_staff_ingest_denied_for_cross_tenant_knowledge_source():
    """Staff A (Institution A) cannot ingest into Institution B's source."""
    response = _ingest_with_tenant(INSTITUTION_B)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


# ---------------------------------------------------------------------------
# 7. Data minimization of the verified approval-queue projection
# ---------------------------------------------------------------------------


def test_approval_queue_projection_never_contains_secret_material():
    """The only student payload a staff client receives is the minimal
    Phase 6.4 approval projection — no credentials, no token material."""
    forbidden = ("password", "token", "secret", "encrypted_password")
    lowered = STUDENT_APPROVAL_COLUMNS.lower()
    for needle in forbidden:
        assert needle not in lowered, needle
    # The projection stays minimal and approval-oriented.
    assert "approval_status" in lowered
    assert "student_number" in lowered






