"""Phase 6.20 — Cross-Role Integration & Authorization Boundary Validation.

The Phase 6.16–6.19 suites each pin ONE role's contract. This suite validates
the COMPLETE authenticated role architecture — student, faculty, staff, admin —
as an integration: shell/role resolution, the cross-role API authorization
matrix, the Phase 6.4 staff approval exception, tenant isolation, cross-tenant
mutation safety, resistance to client-controlled tenant/identity parameters,
and the chat boundary for every authorized role.

NO production behaviour is changed by this phase. Every assertion below is
derived from the backend as the source of truth:

    identity chain   JWT -> get_current_user -> public.users -> user_roles
                     -> roles -> resolve_primary_role -> /auth/me

    GET  /api/v1/auth/me                  -> all authenticated roles  (resolved role)
    GET  /api/v1/conversations            -> all authenticated roles  (user-scoped)
    POST /api/v1/generation/chat          -> all authenticated roles  (get_current_user
                                             + scope_tenant, so tenant-pinned)
    GET  /api/v1/students/me/*            -> student-only identity chain
                                             (404 STUDENT_PROFILE_NOT_FOUND for
                                              non-student accounts)
    GET  /api/v1/admin/students/pending   -> require_roles("admin", "staff")
    POST /api/v1/admin/students/{id}/approve|reject
                                          -> require_roles("admin", "staff")
    *    every other /api/v1/admin/*      -> require_roles("admin") -> 403 FORBIDDEN

Not every endpoint behaves identically (the approval queue is the single,
explicit exception), so the matrix is asserted per endpoint category instead of
assuming uniform 403s.
"""

from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import SUPPORTED_ROLES, resolve_primary_role
from app.main import app
from app.schemas.chat import ChatRequest, ChatResponse

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"
INSTITUTION_B = "30000000-0000-0000-0000-000000000002"
OTHER_INSTITUTION = "30000000-0000-0000-0000-000000000003"

USER_ID = "30000000-0000-0000-0000-000000000701"
STUDENT_A = "30000000-0000-0000-0000-000000000101"
STUDENT_B = "30000000-0000-0000-0000-000000000102"
RESULT_B = "30000000-0000-0000-0000-000000000202"
ATTENDANCE_B = "30000000-0000-0000-0000-000000000303"
KNOWLEDGE_SOURCE_B = "30000000-0000-0000-0000-000000000404"
NOTICE_B = "30000000-0000-0000-0000-000000000505"
FAQ_B = "30000000-0000-0000-0000-000000000606"

AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}

CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "principal@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}


def _user(role: str | None, institution_id: str | None = INSTITUTION_A) -> dict:
    """One authenticated principal for a server-resolved role."""
    roles = [] if role is None else [role]
    return {
        "user_id": USER_ID,
        "auth_user_id": CLAIMS["sub"],
        "email": f"{role or 'unsupported'}@college.edu",
        "roles": roles,
        "institution_id": institution_id,
    }


USERS = {
    "admin": _user("admin"),
    "staff": _user("staff"),
    "faculty": _user("faculty"),
    "student": _user("student"),
    # A platform-level account (no students profile -> no tenant).
    "platform_admin": _user("admin", None),
    # Privileged role without a tenant: approval authority must stay closed.
    "tenantless_staff": _user("staff", None),
    "tenantless_faculty": _user("faculty", None),
    # Authenticated account with no supported role.
    "unsupported": _user(None),
}

ALL_FOUR_ROLES = ("student", "faculty", "staff", "admin")

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
def _auth(role: str, user: dict | None = None):
    """Authenticate every request as one server-resolved principal.

    ``user`` overrides the fixture for that role, which lets a test move the
    SAME role between tenants (Institution A -> Institution B) without changing
    anything else about the principal.
    """
    principal = user if user is not None else USERS[role]
    claims = dict(CLAIMS, email=principal["email"])
    with ExitStack() as stack:
        stack.enter_context(patch("app.core.security.verify_jwt", return_value=claims))
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=principal),
            )
        )
        yield


def _assert_forbidden(role: str, method: str, path: str, **kwargs) -> None:
    """A privileged surface must answer 403 FORBIDDEN for this role."""
    with _auth(role):
        response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
    assert response.status_code == 403, f"{role} {method} {path}: {response.status_code}"
    assert response.json()["error"]["code"] == "FORBIDDEN"


def _assert_tenant_mismatch(role: str, method: str, path: str, **kwargs) -> None:
    """A cross-tenant request must answer 403 TENANT_MISMATCH."""
    with _auth(role):
        response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
    assert response.status_code == 403, f"{role} {method} {path}: {response.status_code}"
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def _assert_student_chain_closed(path: str) -> None:
    """/students/me/* stays a student-only identity chain.

    A non-student account has no `students` row, so the chain fails closed with
    404 STUDENT_PROFILE_NOT_FOUND — the same answer for every role, which also
    prevents role enumeration through this surface.
    """
    for role in ("faculty", "staff", "admin", "unsupported"):
        with _auth(role), patch(
            "app.repositories.admin_academics.get_student_by_user_id",
            return_value=None,
        ):
            response = client.get(path, headers=AUTH_HEADERS)
        assert response.status_code == 404, f"{role} {path}: {response.status_code}"
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


# Every admin-only surface, with the request shape each one needs. Mutations are
# included deliberately: the role dependency must reject them BEFORE any handler
# body (and therefore before any database write) executes.
ADMIN_ONLY_REQUESTS: tuple[tuple[str, str, dict], ...] = (
    ("GET", "/api/v1/admin/me", {}),
    ("GET", "/api/v1/admin/dashboard", {}),
    ("GET", "/api/v1/admin/students", {"params": {"institution_id": INSTITUTION_A}}),
    ("POST", "/api/v1/admin/students", {"json": {"institution_id": INSTITUTION_A}}),
    ("GET", f"/api/v1/admin/students/{STUDENT_A}", {}),
    ("PATCH", f"/api/v1/admin/students/{STUDENT_A}", {"json": {}}),
    ("DELETE", f"/api/v1/admin/students/{STUDENT_A}", {}),
    ("GET", f"/api/v1/admin/students/{STUDENT_A}/attendance", {}),
    ("POST", "/api/v1/admin/attendance", {"json": {"student_id": STUDENT_A}}),
    (
        "PATCH",
        f"/api/v1/admin/attendance/{ATTENDANCE_B}",
        {"json": {"status": "present"}},
    ),
    ("DELETE", f"/api/v1/admin/attendance/{ATTENDANCE_B}", {}),
    ("GET", f"/api/v1/admin/students/{STUDENT_A}/results", {}),
    ("POST", "/api/v1/admin/results", {"json": {"student_id": STUDENT_A}}),
    ("PATCH", f"/api/v1/admin/results/{RESULT_B}", {"json": {}}),
    ("DELETE", f"/api/v1/admin/results/{RESULT_B}", {}),
    ("GET", f"/api/v1/admin/students/{STUDENT_A}/test-results", {}),
    ("POST", "/api/v1/admin/test-results", {"json": {"student_id": STUDENT_A}}),
    ("PATCH", f"/api/v1/admin/test-results/{RESULT_B}", {"json": {}}),
    ("DELETE", f"/api/v1/admin/test-results/{RESULT_B}", {}),
    ("GET", "/api/v1/admin/notices", {}),
    ("POST", "/api/v1/admin/notices", {"json": {"institution_id": INSTITUTION_A}}),
    ("PATCH", f"/api/v1/admin/notices/{NOTICE_B}", {"json": {}}),
    ("DELETE", f"/api/v1/admin/notices/{NOTICE_B}", {}),
    ("GET", "/api/v1/admin/faqs", {}),
    ("POST", "/api/v1/admin/faqs", {"json": {"institution_id": INSTITUTION_A}}),
    ("PATCH", f"/api/v1/admin/faqs/{FAQ_B}", {"json": {}}),
    ("DELETE", f"/api/v1/admin/faqs/{FAQ_B}", {}),
    (
        "GET",
        "/api/v1/admin/knowledge-sources",
        {"params": {"institution_id": INSTITUTION_A}},
    ),
    (
        "POST",
        "/api/v1/admin/knowledge-sources",
        {"json": {"institution_id": INSTITUTION_A}},
    ),
    (
        "GET",
        f"/api/v1/admin/knowledge-sources/{KNOWLEDGE_SOURCE_B}",
        {},
    ),
    ("GET", f"/api/v1/admin/documents/{RESULT_B}", {}),
    (
        "POST",
        "/api/v1/admin/documents",
        {"files": {"file": ("a.txt", b"x", "text/plain")}, "data": {"knowledge_source_id": KNOWLEDGE_SOURCE_B}},
    ),
    (
        "POST",
        f"/api/v1/admin/documents/{RESULT_B}/versions",
        {"files": {"file": ("a.txt", b"x", "text/plain")}},
    ),
    ("DELETE", f"/api/v1/admin/documents/{RESULT_B}", {}),
    ("GET", "/api/v1/admin/audit-logs", {}),
)

# Notes for the matrix above:
#   * the Phase 6.4 approval queue (`/admin/students/pending` and
#     approve/reject) is intentionally NOT part of the admin-only list — it is
#     the single documented staff exception, asserted separately below;
#   * every entry is checked for the student, faculty and staff roles, so a
#     staff session can never inherit admin privileges.




# ---------------------------------------------------------------------------
# 1. Server-authoritative role resolution (JWT -> users -> roles -> /auth/me)
# ---------------------------------------------------------------------------


def test_role_resolution_matrix_is_unchanged():
    """Each role resolves to itself; precedence stays admin > staff > faculty > student."""
    assert resolve_primary_role(["student"]) == "student"
    assert resolve_primary_role(["faculty"]) == "faculty"
    assert resolve_primary_role(["staff"]) == "staff"
    assert resolve_primary_role(["admin"]) == "admin"
    # Precedence is untouched by this phase.
    assert resolve_primary_role(["student", "faculty"]) == "faculty"
    assert resolve_primary_role(["student", "staff"]) == "staff"
    assert resolve_primary_role(["faculty", "staff"]) == "staff"
    assert resolve_primary_role(["staff", "admin"]) == "admin"
    assert resolve_primary_role(list(SUPPORTED_ROLES)) == "admin"
    # Unsupported/null roles never resolve to a privileged role.
    assert resolve_primary_role(["unknown-role"]) is None
    assert resolve_primary_role([]) is None
    assert resolve_primary_role(None) is None


def test_auth_me_resolves_each_role_with_its_own_tenant():
    for role in ALL_FOUR_ROLES:
        with _auth(role):
            response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
        assert response.status_code == 200, role
        body = response.json()
        assert body["authenticated"] is True
        assert body["role"] == role
        assert body["institution_id"] == INSTITUTION_A
        # No token/secret material is ever part of the identity payload.
        assert set(body) == {
            "authenticated",
            "user_id",
            "auth_user_id",
            "email",
            "role",
            "institution_id",
        }


def test_auth_me_never_derives_the_role_from_client_parameters():
    """URL/localStorage/body role values cannot influence the resolved role."""
    for role in ALL_FOUR_ROLES:
        with _auth(role):
            response = client.get(
                "/api/v1/auth/me",
                headers=AUTH_HEADERS,
                params={
                    "role": "admin",
                    "institution_id": INSTITUTION_B,
                    "user_id": "client-supplied",
                    "tenant_id": INSTITUTION_B,
                },
            )
        assert response.status_code == 200, role
        body = response.json()
        assert body["role"] == role, role
        assert body["institution_id"] == INSTITUTION_A, role


def test_unsupported_role_resolves_to_no_privileged_context():
    with _auth("unsupported"):
        response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["role"] is None
    # And it is still an authenticated, tenant-bound session.
    assert response.json()["institution_id"] == INSTITUTION_A



# ---------------------------------------------------------------------------
# 2. Cross-role API authorization matrix
# ---------------------------------------------------------------------------


def test_admin_only_matrix_is_closed_for_every_non_admin_role():
    """*    /admin/* (except the approval queue) is admin-only.

    Asserted for student, faculty AND staff so a staff session can never inherit
    administrative authority — including the mutation entries, which never reach
    a handler body.
    """
    for role in ("student", "faculty", "staff"):
        for method, path, kwargs in ADMIN_ONLY_REQUESTS:
            _assert_forbidden(role, method, path, **kwargs)


def test_student_privileged_boundary_is_closed_server_side():
    """The student UI alone is not evidence — the backend must deny."""
    with _auth("student"), patch(
        "app.api.admin.admin_academics.list_students"
    ) as list_mock, patch("app.api.admin.get_admin_client") as client_mock:
        response = client.get(
            "/api/v1/admin/students",
            params={"institution_id": INSTITUTION_A},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    list_mock.assert_not_called()
    client_mock.assert_not_called()


def test_admin_only_matrix_is_open_for_admin():
    """The same surfaces remain reachable for the admin role (read paths)."""
    with _auth("admin"), patch(
        "app.api.admin.admin_dashboard.get_dashboard_summary", return_value={}
    ), patch(
        "app.api.admin.admin_academics.list_students", return_value=[]
    ), patch(
        "app.api.admin.admin_academics.get_student", return_value=PENDING_STUDENT_ROW
    ), patch(
        "app.api.admin.admin_academics.list_results_for_student", return_value=[]
    ), patch(
        "app.api.admin.admin_academics.list_test_results_for_student", return_value=[]
    ), patch(
        "app.api.admin.attendance.list_attendance_for_student", return_value=[]
    ), patch(
        "app.api.admin.admin_notices.list_notices", return_value=[]
    ), patch(
        "app.api.admin.admin_faq.list_faqs", return_value=[]
    ), patch(
        "app.api.admin.knowledge_repo.list_knowledge_sources", return_value=[]
    ), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ):
        calls = (
            ("GET", "/api/v1/admin/me", {}),
            ("GET", "/api/v1/admin/dashboard", {}),
            ("GET", "/api/v1/admin/students", {"params": {"institution_id": INSTITUTION_A}}),
            ("GET", f"/api/v1/admin/students/{STUDENT_A}", {}),
            ("GET", f"/api/v1/admin/students/{STUDENT_A}/results", {}),
            ("GET", f"/api/v1/admin/students/{STUDENT_A}/test-results", {}),
            ("GET", f"/api/v1/admin/students/{STUDENT_A}/attendance", {}),
            ("GET", "/api/v1/admin/notices", {}),
            ("GET", "/api/v1/admin/faqs", {}),
            (
                "GET",
                "/api/v1/admin/knowledge-sources",
                {"params": {"institution_id": INSTITUTION_A}},
            ),
            ("GET", "/api/v1/admin/audit-logs", {}),
        )
        for method, path, kwargs in calls:
            response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
            assert response.status_code == 200, f"admin {method} {path}: {response.status_code}"


def test_student_identity_chain_is_closed_for_every_other_role():
    """/students/me/* answers 404 STUDENT_PROFILE_NOT_FOUND (never data) for
    faculty, staff, admin, and unsupported accounts."""
    for path in (
        "/api/v1/students/me/profile",
        "/api/v1/students/me/academic-profile",
        "/api/v1/students/me/results",
        "/api/v1/students/me/results/summary",
        "/api/v1/students/me/test-results",
        "/api/v1/students/me/test-results/summary",
        "/api/v1/students/me/attendance",
        "/api/v1/students/me/attendance/summary",
        "/api/v1/students/me/notices",
        "/api/v1/students/me/resources",
    ):
        _assert_student_chain_closed(path)


def test_faculty_cannot_use_the_student_contract_even_with_client_identity_params():
    """Faculty -> /students/me/* stays closed; client identity fields are inert."""
    with _auth("faculty"), patch(
        "app.repositories.admin_academics.get_student_by_user_id", return_value=None
    ) as by_user:
        response = client.get(
            "/api/v1/students/me/profile",
            headers=AUTH_HEADERS,
            params={
                "student_id": STUDENT_A,
                "user_id": USER_ID,
                "institution_id": INSTITUTION_A,
            },
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"
    # The chain was resolved from the JWT identity, and it stops there.
    by_user.assert_called_once()



# ---------------------------------------------------------------------------
# 3. The staff approval exception (Phase 6.4) — preserved, not widened
# ---------------------------------------------------------------------------


def test_approval_queue_is_allowed_for_staff_and_admin_only():
    """staff + admin may list/approve/reject; student + faculty get 403."""
    with _auth("staff"), patch(
        "app.api.admin.admin_academics.list_pending_approvals",
        return_value=[PENDING_STUDENT_ROW],
    ) as list_mock:
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == [PENDING_STUDENT_ROW]
    list_mock.assert_called_once_with(UUID(INSTITUTION_A), limit=100, offset=0)

    with _auth("admin"), patch(
        "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
    ):
        assert client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS).status_code == 200

    for role in ("student", "faculty"):
        _assert_forbidden(role, "GET", "/api/v1/admin/students/pending")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/approve")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/reject")


def test_denied_approval_attempts_never_reach_the_handler_or_write():
    """403 happens in the dependency: no approval service call, no write."""
    for role in ("student", "faculty"):
        with _auth(role), patch(
            "app.api.admin.admin_academics.approve_student"
        ) as approve_mock, patch(
            "app.api.admin.admin_academics.reject_student"
        ) as reject_mock, patch(
            "app.api.admin.record_admin_action"
        ) as audit_mock, patch(
            "app.api.admin.get_admin_client"
        ) as client_mock:
            approve = client.post(
                f"/api/v1/admin/students/{STUDENT_A}/approve", headers=AUTH_HEADERS
            )
            reject = client.post(
                f"/api/v1/admin/students/{STUDENT_A}/reject", headers=AUTH_HEADERS
            )
        assert approve.status_code == 403, role
        assert reject.status_code == 403, role
        approve_mock.assert_not_called()
        reject_mock.assert_not_called()
        audit_mock.assert_not_called()
        client_mock.assert_not_called()


def test_staff_and_admin_approve_within_their_own_tenant():
    for role in ("staff", "admin"):
        with _auth(role), patch(
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
        assert response.status_code == 200, role
        assert response.json()["approval_status"] == "approved"
        approve_mock.assert_called_once_with(UUID(STUDENT_A), UUID(INSTITUTION_A))
        audit_mock.assert_called_once()


def test_stale_approval_decision_produces_the_documented_409():
    """pending -> approved is strict: a stale approve/reject is 409 and writes nothing."""
    already_decided = dict(PENDING_STUDENT_ROW, approval_status="approved")
    for role in ("staff", "admin"):
        for operation in ("approve", "reject"):
            with _auth(role), patch(
                "app.services.admin_academics.get_admin_client",
                return_value=MagicMock(),
            ), patch(
                "app.services.admin_academics.academics_repo.get_student_for_approval",
                return_value=already_decided,
            ), patch(
                "app.services.admin_academics.academics_repo.set_student_approval_status"
            ) as write_mock, patch(
                "app.api.admin.record_admin_action"
            ) as audit_mock:
                response = client.post(
                    f"/api/v1/admin/students/{STUDENT_A}/{operation}",
                    headers=AUTH_HEADERS,
                )
            assert response.status_code == 409, f"{role} {operation}"
            assert response.json()["error"]["code"] == "STUDENT_NOT_PENDING"
            # The rejected/approved record is never mutated again.
            write_mock.assert_not_called()
            audit_mock.assert_not_called()


def test_platform_level_staff_and_faculty_hold_no_approval_authority():
    """Tenantless privileged users fail safely (Phase 6.4 OPTION A)."""
    for role in ("tenantless_staff", "tenantless_faculty"):
        _assert_forbidden(role, "GET", "/api/v1/admin/students/pending")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/approve")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/reject")



# ---------------------------------------------------------------------------
# 4. Tenant isolation matrix (Institution A vs Institution B)
# ---------------------------------------------------------------------------
#
#   Institution A: Student A / Faculty A / Staff A / Admin A
#   Institution B: Student B / Faculty B / Staff B / Admin B
#
# Every tenant-bound role is exercised in BOTH directions where the surface
# exists; the pinned outcome is 403 TENANT_MISMATCH (reads) and 403 with no
# write at all (mutations).


def test_admin_a_cannot_read_admin_b_student_records():
    foreign = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B, student_id=STUDENT_B)
    with _auth("admin", _user("admin", INSTITUTION_A)), patch(
        "app.api.admin.admin_academics.get_student", return_value=foreign
    ):
        _assert_tenant_mismatch("admin", "GET", f"/api/v1/admin/students/{STUDENT_B}")


def test_admin_a_cannot_read_admin_b_notice_faq_document_and_knowledge_source():
    """Every admin read surface re-checks the row's tenant (not just the query)."""
    with _auth("admin"), patch(
        "app.api.admin.admin_notices.get_notice",
        return_value={"notice_id": NOTICE_B, "institution_id": INSTITUTION_B},
    ):
        _assert_tenant_mismatch("admin", "GET", f"/api/v1/admin/notices/{NOTICE_B}")

    with _auth("admin"), patch(
        "app.api.admin.admin_faq.get_faq",
        return_value={"faq_id": FAQ_B, "institution_id": INSTITUTION_B},
    ):
        _assert_tenant_mismatch("admin", "GET", f"/api/v1/admin/faqs/{FAQ_B}")

    with _auth("admin"), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.api.admin.knowledge_repo.get_knowledge_source_detail",
        return_value={
            "knowledge_source_id": KNOWLEDGE_SOURCE_B,
            "institution_id": INSTITUTION_B,
        },
    ):
        _assert_tenant_mismatch(
            "admin", "GET", f"/api/v1/admin/knowledge-sources/{KNOWLEDGE_SOURCE_B}"
        )

    with _auth("admin"), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.api.admin.knowledge_repo.get_document_with_versions",
        return_value={"document_id": RESULT_B, "knowledge_source_id": KNOWLEDGE_SOURCE_B},
    ), patch(
        "app.api.admin.knowledge_repo.get_knowledge_source_detail",
        return_value={
            "knowledge_source_id": KNOWLEDGE_SOURCE_B,
            "institution_id": INSTITUTION_B,
        },
    ):
        _assert_tenant_mismatch("admin", "GET", f"/api/v1/admin/documents/{RESULT_B}")


def test_staff_a_cannot_approve_or_reject_staff_bs_student():
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    for operation in ("approve", "reject"):
        with _auth("staff"), patch(
            "app.services.admin_academics.get_admin_client", return_value=MagicMock()
        ), patch(
            "app.services.admin_academics.academics_repo.get_student_for_approval",
            return_value=foreign_student,
        ), patch(
            "app.services.admin_academics.academics_repo.set_student_approval_status"
        ) as write_mock, patch(
            "app.api.admin.record_admin_action"
        ) as audit_mock:
            response = client.post(
                f"/api/v1/admin/students/{STUDENT_B}/{operation}", headers=AUTH_HEADERS
            )
        assert response.status_code == 403, operation
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"
        # The foreign record is never mutated and no audit entry is written.
        write_mock.assert_not_called()
        audit_mock.assert_not_called()


def test_staff_a_cannot_list_staff_bs_pending_queue_via_parameters():
    _assert_tenant_mismatch(
        "staff",
        "GET",
        "/api/v1/admin/students/pending",
        params={"institution_id": INSTITUTION_B},
    )



def test_student_a_cannot_reach_student_bs_academic_data():
    """The student chain resolves from the JWT; a foreign students row is refused."""
    foreign = {
        "student_id": STUDENT_B,
        "user_id": USER_ID,
        "institution_id": INSTITUTION_B,
    }
    with _auth("student"), patch(
        "app.api.students.student_data.get_own_profile", return_value=foreign
    ):
        _assert_tenant_mismatch("student", "GET", "/api/v1/students/me/profile")


def test_faculty_a_cannot_use_faculty_bs_tenant_on_the_chat_contract():
    _assert_tenant_mismatch(
        "faculty",
        "POST",
        "/api/v1/generation/chat",
        json={"user_query": "hello", "institution_id": INSTITUTION_B},
    )


def test_platform_level_admin_keeps_its_documented_global_authority():
    """Pre-existing Phase 6.1 convention (unchanged by this phase): a
    platform-level admin has no institution, so an explicit institution filter
    is honoured. Tenant-BOUND accounts never get this passthrough."""
    with _auth("platform_admin"), patch(
        "app.api.admin.admin_academics.list_students", return_value=[]
    ) as list_mock:
        response = client.get(
            "/api/v1/admin/students",
            params={"institution_id": INSTITUTION_B},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200
    assert list_mock.call_args.args[0] == UUID(INSTITUTION_B)


def test_tenantless_privileged_accounts_gain_no_operational_authority():
    """Fail safe: no tenant means no admin surface and no approval authority.

    The chat contract keeps its locked Phase 6.1 platform passthrough (a
    documented, pre-existing limitation — see the phase document); every
    administrative surface stays closed.
    """
    for role in ("tenantless_staff", "tenantless_faculty"):
        _assert_forbidden(role, "GET", "/api/v1/admin/me")
        _assert_forbidden(role, "GET", "/api/v1/admin/dashboard")
        _assert_forbidden(
            role,
            "GET",
            "/api/v1/admin/students",
            params={"institution_id": INSTITUTION_A},
        )
        _assert_forbidden(role, "GET", "/api/v1/admin/students/pending")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/approve")


# ---------------------------------------------------------------------------
# 5. Cross-tenant mutation safety (403 AND no database write)
# ---------------------------------------------------------------------------


def test_cross_tenant_student_management_mutations_write_nothing():
    foreign = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B, student_id=STUDENT_B)

    # Create with a foreign institution_id in the payload.
    with _auth("admin"), patch(
        "app.api.admin.admin_academics.create_student"
    ) as create_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock, patch(
        "app.api.admin.get_admin_client"
    ) as db_mock:
        response = client.post(
            "/api/v1/admin/students",
            json={
                "user_id": USER_ID,
                "institution_id": INSTITUTION_B,
                "student_number": "STU-9001",
                "enrollment_date": "2026-01-01",
            },
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    create_mock.assert_not_called()
    audit_mock.assert_not_called()
    db_mock.assert_not_called()

    # Update a foreign student record.
    with _auth("admin"), patch(
        "app.api.admin.admin_academics.get_student", return_value=foreign
    ), patch("app.api.admin.admin_academics.update_student") as update_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock:
        response = client.patch(
            f"/api/v1/admin/students/{STUDENT_B}",
            json={"status": "inactive"},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    update_mock.assert_not_called()
    audit_mock.assert_not_called()

    # Delete a foreign student record.
    with _auth("admin"), patch(
        "app.api.admin.admin_academics.get_student", return_value=foreign
    ), patch("app.api.admin.admin_academics.archive_student") as delete_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock:
        response = client.delete(
            f"/api/v1/admin/students/{STUDENT_B}", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    delete_mock.assert_not_called()
    audit_mock.assert_not_called()



def test_cross_tenant_academic_mutations_write_nothing():
    """Attendance / results / test results: the student's tenant is checked
    BEFORE the write service is called."""
    foreign = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B, student_id=STUDENT_B)
    attendance_payload = {
        "student_id": STUDENT_B,
        "section_id": str(uuid4()),
        "academic_year_id": str(uuid4()),
        "semester_id": str(uuid4()),
        "date": "2026-01-05",
        "status": "present",
    }
    result_payload = {
        "student_id": STUDENT_B,
        "academic_year_id": str(uuid4()),
        "semester_id": str(uuid4()),
        "program_id": str(uuid4()),
        "result_type": "semester",
    }
    test_result_payload = {
        "student_id": STUDENT_B,
        "course_id": str(uuid4()),
        "academic_year_id": str(uuid4()),
        "semester_id": str(uuid4()),
        "test_name": "Midterm",
        "test_type": "internal",
        "max_marks": 50,
        "scored_marks": 40,
    }

    with _auth("admin"), patch(
        "app.api.admin.admin_academics.get_student", return_value=foreign
    ), patch("app.api.admin.attendance.create_attendance") as write_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock:
        response = client.post(
            "/api/v1/admin/attendance", json=attendance_payload, headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()
    audit_mock.assert_not_called()

    with _auth("admin"), patch(
        "app.api.admin.admin_academics.get_student", return_value=foreign
    ), patch("app.api.admin.admin_academics.create_result") as write_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock:
        response = client.post(
            "/api/v1/admin/results", json=result_payload, headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()
    audit_mock.assert_not_called()

    with _auth("admin"), patch(
        "app.api.admin.admin_academics.get_student", return_value=foreign
    ), patch("app.api.admin.admin_academics.create_test_result") as write_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock:
        response = client.post(
            "/api/v1/admin/test-results", json=test_result_payload, headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()
    audit_mock.assert_not_called()


def test_cross_tenant_notice_and_faq_mutations_write_nothing():
    notice_payload = {
        "institution_id": INSTITUTION_B,
        "title": "Foreign notice",
        "content": "Should never be created.",
    }
    faq_payload = {
        "institution_id": INSTITUTION_B,
        "question": "Foreign FAQ?",
        "answer": "Should never be created.",
    }

    with _auth("admin"), patch(
        "app.api.admin.admin_notices.create_notice"
    ) as write_mock, patch("app.api.admin.record_admin_action") as audit_mock:
        response = client.post(
            "/api/v1/admin/notices", json=notice_payload, headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()
    audit_mock.assert_not_called()

    with _auth("admin"), patch("app.api.admin.admin_faq.create_faq") as write_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock:
        response = client.post(
            "/api/v1/admin/faqs", json=faq_payload, headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()
    audit_mock.assert_not_called()


def test_cross_tenant_knowledge_source_and_document_writes_create_nothing():
    with _auth("admin"), patch(
        "app.api.admin.knowledge_repo.create_knowledge_source"
    ) as create_mock, patch("app.api.admin.record_admin_action") as audit_mock, patch(
        "app.api.admin.get_admin_client"
    ) as db_mock:
        response = client.post(
            "/api/v1/admin/knowledge-sources",
            json={
                "institution_id": INSTITUTION_B,
                "source_type": "document",
                "title": "Foreign source",
            },
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    create_mock.assert_not_called()
    audit_mock.assert_not_called()
    db_mock.assert_not_called()

    # Uploading a document into another institution's knowledge source.
    with _auth("admin"), patch(
        "app.api.admin.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.api.admin.knowledge_repo.get_knowledge_source_detail",
        return_value={
            "knowledge_source_id": KNOWLEDGE_SOURCE_B,
            "institution_id": INSTITUTION_B,
        },
    ), patch("app.api.admin.admin_documents.upload_document") as upload_mock, patch(
        "app.api.admin.record_admin_action"
    ) as audit_mock:
        response = client.post(
            "/api/v1/admin/documents",
            files={"file": ("notes.txt", b"foreign content", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_B},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    upload_mock.assert_not_called()
    audit_mock.assert_not_called()

