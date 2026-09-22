"""Phase 6.19 - Admin Experience & Administrative Workspace Foundation.

Backend security regression tests for the ADMIN role. NO production backend
behaviour is changed by Phase 6.19: the admin workspace is built ONLY on the
server-authoritative contracts that already exist. This suite PINS that
contract map so the frontend admin shell can never drift into privilege.

Tenant isolation and ownership are enforced server-side; none of the tests
below rely on frontend filtering.
"""

from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.security import SUPPORTED_ROLES, resolve_primary_role
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"
INSTITUTION_B = "30000000-0000-0000-0000-000000000002"
USER_ID = "30000000-0000-0000-0000-000000000301"
STUDENT_A = "30000000-0000-0000-0000-000000000101"
STUDENT_B = "30000000-0000-0000-0000-000000000102"

ADMIN_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "admin@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

ADMIN_USER = {
    "user_id": USER_ID,
    "auth_user_id": ADMIN_CLAIMS["sub"],
    "email": ADMIN_CLAIMS["email"],
    "roles": ["admin"],
    "institution_id": INSTITUTION_A,
}

NON_ADMIN_USERS = {
    "student": {
        "user_id": USER_ID,
        "auth_user_id": ADMIN_CLAIMS["sub"],
        "email": "student@college.edu",
        "roles": ["student"],
        "institution_id": INSTITUTION_A,
    },
    "faculty": {
        "user_id": USER_ID,
        "auth_user_id": ADMIN_CLAIMS["sub"],
        "email": "faculty@college.edu",
        "roles": ["faculty"],
        "institution_id": INSTITUTION_A,
    },
    "staff": {
        "user_id": USER_ID,
        "auth_user_id": ADMIN_CLAIMS["sub"],
        "email": "staff@college.edu",
        "roles": ["staff"],
        "institution_id": INSTITUTION_A,
    },
}

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
def _patch_admin_auth(user=ADMIN_USER):
    """Authenticate every request as the admin principal."""
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.core.security.verify_jwt", return_value=ADMIN_CLAIMS)
        )
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=user),
            )
        )
        yield


@contextmanager
def _patch_role_auth(role: str):
    """Authenticate every request as a non-admin principal."""
    user = NON_ADMIN_USERS[role]
    claims = dict(ADMIN_CLAIMS, email=user["email"])
    with ExitStack() as stack:
        stack.enter_context(patch("app.core.security.verify_jwt", return_value=claims))
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=user),
            )
        )
        yield


def _assert_forbidden(method: str, path: str, **kwargs) -> None:
    """The admin-only surface must stay 403 FORBIDDEN for non-admins."""
    response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
    assert response.status_code == 403, f"{method} {path}: {response.status_code}"
    assert response.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 1. Admin role resolution (server-authoritative, /auth/me)
# ---------------------------------------------------------------------------


def test_resolve_primary_role_admin_precedence_unchanged():
    """admin > staff > faculty > student precedence is untouched."""
    assert resolve_primary_role(["admin"]) == "admin"
    assert resolve_primary_role(["student", "admin"]) == "admin"
    assert resolve_primary_role(list(SUPPORTED_ROLES)) == "admin"
    assert resolve_primary_role(["unknown-role"]) is None
    assert resolve_primary_role(None) is None


def test_auth_me_returns_admin_role_with_tenant():
    """Admin identity: canonical role + tenant resolved SERVER-SIDE."""
    with _patch_admin_auth():
        response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["role"] == "admin"
    assert body["institution_id"] == INSTITUTION_A


def test_auth_me_client_params_cannot_override_admin_role():
    """Client-supplied role/institution params never override /auth/me."""
    with _patch_admin_auth():
        response = client.get(
            "/api/v1/auth/me",
            headers=AUTH_HEADERS,
            params={"role": "student", "institution_id": INSTITUTION_B},
        )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["institution_id"] == INSTITUTION_A


# ---------------------------------------------------------------------------
# 2. Admin -> admin surfaces ALLOWED (representative, tenant-scoped)
# ---------------------------------------------------------------------------


def test_admin_me_returns_identity_and_status():
    with _patch_admin_auth():
        response = client.get("/api/v1/admin/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["is_admin"] is True


def test_admin_dashboard_scoped_to_own_tenant():
    with _patch_admin_auth(), patch(
        "app.api.admin.admin_dashboard.get_dashboard_summary", return_value={}
    ) as dash_mock:
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 200
    dash_mock.assert_called_once_with(institution_id=UUID(INSTITUTION_A))


def test_admin_list_students_scoped_to_own_tenant():
    with _patch_admin_auth(), patch(
        "app.api.admin.admin_academics.list_students", return_value=[]
    ) as list_mock:
        response = client.get(
            "/api/v1/admin/students",
            params={"institution_id": INSTITUTION_A},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200
    assert list_mock.call_args.args[0] == UUID(INSTITUTION_A)


# ---------------------------------------------------------------------------
# 3. Non-admin roles -> admin surfaces DENIED (403), staff exception intact
# ---------------------------------------------------------------------------


def test_student_denied_admin_surfaces():
    with _patch_role_auth("student"):
        for method, path in (
            ("GET", "/api/v1/admin/me"),
            ("GET", "/api/v1/admin/dashboard"),
            ("GET", "/api/v1/admin/students"),
            ("GET", "/api/v1/admin/notices"),
            ("GET", "/api/v1/admin/faqs"),
            ("POST", "/api/v1/admin/results"),
            ("GET", "/api/v1/admin/audit-logs"),
        ):
            _assert_forbidden(method, path)


def test_faculty_denied_admin_surfaces():
    with _patch_role_auth("faculty"):
        for method, path in (
            ("GET", "/api/v1/admin/me"),
            ("GET", "/api/v1/admin/dashboard"),
            ("POST", "/api/v1/admin/results/csv-upload"),
            ("GET", "/api/v1/admin/audit-logs"),
        ):
            _assert_forbidden(method, path)


def test_staff_denied_admin_surfaces_except_approval_queue():
    """Staff keeps ONLY the Phase 6.4/6.18 approval exception - nothing more
    is granted merely because Phase 6.19 audits the admin workspace."""
    with _patch_role_auth("staff"):
        for method, path in (
            ("GET", "/api/v1/admin/me"),
            ("GET", "/api/v1/admin/dashboard"),
            ("GET", "/api/v1/admin/students"),
            ("POST", "/api/v1/admin/results/csv-upload"),
            ("GET", "/api/v1/admin/audit-logs"),
        ):
            _assert_forbidden(method, path)


def test_staff_approval_exception_remains_intact():
    with _patch_role_auth("staff"), patch(
        "app.api.admin.admin_academics.list_pending_approvals",
        return_value=[PENDING_STUDENT_ROW],
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == [PENDING_STUDENT_ROW]


# ---------------------------------------------------------------------------
# 4. Admin approval workflow + tenant isolation (no cross-tenant write)
# ---------------------------------------------------------------------------


def test_admin_lists_pending_students_scoped_to_own_tenant():
    with _patch_admin_auth(), patch(
        "app.api.admin.admin_academics.list_pending_approvals",
        return_value=[PENDING_STUDENT_ROW],
    ) as list_mock:
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == [PENDING_STUDENT_ROW]
    list_mock.assert_called_once_with(UUID(INSTITUTION_A), limit=100, offset=0)


def test_admin_foreign_institution_filter_rejected():
    """A foreign ?institution_id= can never widen the queue scope."""
    with _patch_admin_auth(), patch(
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


def test_admin_approves_pending_student_within_own_tenant():
    db = MagicMock()
    with _patch_admin_auth(), patch(
        "app.api.admin.admin_academics.approve_student",
        return_value=dict(PENDING_STUDENT_ROW, approval_status="approved"),
    ) as approve_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock, patch(
        "app.api.admin.get_admin_client", return_value=db
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    approve_mock.assert_called_once_with(UUID(STUDENT_A), UUID(INSTITUTION_A))
    audit_mock.assert_called_once()


def test_admin_cannot_approve_cross_tenant_student():
    """Institution A's admin cannot approve Institution B's student. Tenant
    is enforced BEFORE any state change; no write happens."""
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    with _patch_admin_auth(), patch(
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


def test_admin_cannot_reject_cross_tenant_student():
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    with _patch_admin_auth(), patch(
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


def test_admin_cannot_read_cross_tenant_student():
    """Tenant A -> tenant B reads fail closed on the student surface."""
    with _patch_admin_auth(), patch(
        "app.api.admin.admin_academics.get_student",
        return_value=dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B),
    ):
        response = client.get(
            f"/api/v1/admin/students/{STUDENT_B}", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_admin_approval_identity_params_are_inert():
    """Approve bodies accept NO fields: client identity params never change
    the decision target or tenant (both come from path + JWT context)."""
    with _patch_admin_auth(), patch(
        "app.api.admin.admin_academics.approve_student",
        return_value=dict(PENDING_STUDENT_ROW, approval_status="approved"),
    ) as approve_mock, patch(
        "app.api.admin.record_admin_action"
    ), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/approve",
            params={"institution_id": INSTITUTION_B, "student_id": STUDENT_B},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200
    approve_mock.assert_called_once_with(UUID(STUDENT_A), UUID(INSTITUTION_A))


# ---------------------------------------------------------------------------
# 5. Results CSV upload (POST /results/csv-upload, tenant-scoped Form field)
# ---------------------------------------------------------------------------


def test_admin_csv_upload_foreign_institution_rejected():
    """The institution_id Form field is re-scoped SERVER-SIDE: a foreign
    value can never widen the upload target tenant."""
    with _patch_admin_auth(), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.api.admin.admin_academics.upload_results_csv"
    ) as upload_mock:
        response = client.post(
            "/api/v1/admin/results/csv-upload",
            files={"file": ("results.csv", b"student_number\n", "text/csv")},
            data={"institution_id": INSTITUTION_B},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    upload_mock.assert_not_called()


def test_admin_csv_upload_own_institution_scopes_correctly():
    with _patch_admin_auth(), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.api.admin.admin_academics.upload_results_csv"
    ) as upload_mock, patch(
        "app.api.admin.record_admin_action"
    ):
        response = client.post(
            "/api/v1/admin/results/csv-upload",
            files={"file": ("results.csv", b"student_number\n", "text/csv")},
            data={"institution_id": INSTITUTION_A},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200
    upload_mock.assert_called_once()
    assert upload_mock.call_args.args[1] == UUID(INSTITUTION_A)


# ---------------------------------------------------------------------------
# 6. Data minimization (no token/secret material in identity responses)
# ---------------------------------------------------------------------------


def test_admin_responses_expose_no_token_material():
    with _patch_admin_auth():
        me = client.get("/api/v1/auth/me", headers=AUTH_HEADERS).json()
        admin_me = client.get("/api/v1/admin/me", headers=AUTH_HEADERS).json()
    forbidden = ("access_token", "refresh_token", "password", "jwt", "secret")
    for body in (me, admin_me):
        for key in body:
            assert key not in forbidden, key
    assert admin_me["user_id"] == USER_ID
    assert set(admin_me) == {"user_id", "auth_user_id", "email", "roles", "is_admin"}
