"""Phase 7.24 — Staff & Faculty operational capability audit (evidence).

This suite is AUDIT EVIDENCE ONLY. It adds no endpoint, no service, no schema,
no migration and no frontend change. Every test asserts behaviour that the
EXISTING Phase 7.20 authorization chain already provides, so that the audit's
capability matrix and student-scope conclusions are proven rather than assumed.

The required chain under audit:

    verified JWT
      -> get_current_user
      -> active public.users + user_roles + roles
      -> resolve_institution_authorization_context
      -> require_institution_roles(allowed roles)
      -> AuthorizationContext(institution_id, role, active)
      -> tenant-filtered query (scope_tenant / assert_tenant_object)

Scenarios required by the Phase 7.24 brief:

    * Staff A     -> Institution B              denied
    * Faculty A   -> Institution B              denied
    * Staff       -> Admin capability           denied
    * Faculty     -> Admin capability           denied
    * Student     -> Staff/Faculty capability   denied
    * Deactivated Staff   -> protected operation denied
    * Deactivated Faculty -> protected operation denied
    * Super Admin -> must NOT inherit institution staff/faculty permissions

Plus the capability inventory itself: which routes staff/faculty may reach,
and the student-scope model (no academic-assignment relationship exists).
"""

from __future__ import annotations

import inspect
import re
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.admin import _ADMIN, _APPROVAL
from app.core.security import get_current_user
from app.main import app


client = TestClient(app, raise_server_exceptions=False)

INST_A = "72400000-0000-0000-0000-00000000000a"
INST_B = "72400000-0000-0000-0000-00000000000b"

STAFF_A = "72500000-0000-0000-0000-00000000000a"
FACULTY_A = "72500000-0000-0000-0000-00000000000b"
ADMIN_A = "72500000-0000-0000-0000-00000000000c"
STUDENT_A = "72500000-0000-0000-0000-00000000000d"
SUPER_ADMIN = "72500000-0000-0000-0000-00000000000e"

STUDENT_A_ROW = "72600000-0000-0000-0000-00000000000a"
STUDENT_B_ROW = "72600000-0000-0000-0000-00000000000b"
KNOWLEDGE_SOURCE_A = "72700000-0000-0000-0000-00000000000a"
KNOWLEDGE_SOURCE_B = "72700000-0000-0000-0000-00000000000b"

AUTH_HEADERS = {"Authorization": "Bearer phase724.token"}

STAFF_OR_FACULTY = ("staff", "faculty")


# ---------------------------------------------------------------------------
# Principal construction
# ---------------------------------------------------------------------------


def _grant(role: str, institution_id: str | None) -> dict:
    return {
        "role": role,
        "scope_type": "institution" if institution_id else "platform",
        "scope_id": institution_id,
        "scope_organization_id": None,
        "is_active": True,
    }


def _principal(
    user_id: str,
    role: str,
    institution_id: str | None,
    *,
    status: str = "active",
) -> dict:
    """A principal shaped exactly like ``get_current_user`` after Phase 7.20.

    The top-level ``institution_id`` is deliberately ``None``: the dependency
    must re-derive the tenant from ``role_assignments.scope_id`` and must
    never trust a client-controlled tenant.
    """
    return {
        "user_id": user_id,
        "auth_user_id": user_id,
        "email": f"{role}@example.edu",
        "status": status,
        "roles": [role],
        "institution_id": None,
        "role_assignments": [_grant(role, institution_id)],
    }


STAFF_A_USER = _principal(STAFF_A, "staff", INST_A)
FACULTY_A_USER = _principal(FACULTY_A, "faculty", INST_A)
ADMIN_A_USER = _principal(ADMIN_A, "admin", INST_A)
STUDENT_A_USER = _principal(STUDENT_A, "student", INST_A)
SUPER_ADMIN_USER = _principal(SUPER_ADMIN, "super_admin", None)

DEACTIVATED_STAFF_USER = _principal(STAFF_A, "staff", INST_A, status="deactivated")
DEACTIVATED_FACULTY_USER = _principal(FACULTY_A, "faculty", INST_A, status="deactivated")

STAFF_AND_FACULTY_USERS = [(STAFF_A_USER, "staff"), (FACULTY_A_USER, "faculty")]


@contextmanager
def _as(principal: dict, *, institution_active: bool = True):
    """Authenticate as ``principal`` with a controlled institution lifecycle row."""
    app.dependency_overrides[get_current_user] = lambda: principal
    scope_ids = [
        grant["scope_id"]
        for grant in principal.get("role_assignments", [])
        if grant.get("scope_id")
    ]
    institution = {
        "institution_id": str(scope_ids[0] if scope_ids else None),
        "status": "active" if institution_active else "suspended",
        "is_active": institution_active,
    }
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch(
            "app.services.authorization.tenancy_repo.get_institution_by_id",
            return_value=institution,
        ),
        patch(
            "app.db.supabase.get_super_admin_authorization",
            new=AsyncMock(return_value={"status": "active", "has_platform_grant": True}),
        ),
    ):
        yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _clean_dependencies():
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)
    yield
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)


def _error_code(response) -> str | None:
    """Read the stable AppError code out of a failure response."""
    body = response.json()
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return body["error"].get("code")
    return None
# ---------------------------------------------------------------------------
# 1. Capability inventory — the routes each role may actually reach
# ---------------------------------------------------------------------------

# (method, path) for the admin surface staff/faculty must NOT reach.
ADMIN_ONLY_ROUTES = [
    ("GET", "/api/v1/admin/me"),
    ("GET", "/api/v1/admin/dashboard"),
    ("GET", "/api/v1/admin/memberships"),
    ("GET", "/api/v1/admin/memberships/requests"),
    ("GET", "/api/v1/admin/faqs"),
    ("GET", "/api/v1/admin/notices"),
    ("GET", "/api/v1/admin/audit-logs"),
    ("GET", f"/api/v1/admin/students/{STUDENT_A_ROW}"),
    ("GET", f"/api/v1/admin/students/{STUDENT_A_ROW}/results"),
    ("GET", f"/api/v1/admin/students/{STUDENT_A_ROW}/test-results"),
    ("GET", f"/api/v1/admin/students/{STUDENT_A_ROW}/attendance"),
]


@pytest.mark.parametrize("method,path", ADMIN_ONLY_ROUTES)
@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_are_denied_every_admin_only_route(
    method: str, path: str, principal: dict, label: str
) -> None:
    """Neither Staff nor Faculty reaches any admin-only capability."""
    with _as(principal):
        response = client.request(method, path, headers=AUTH_HEADERS)
    assert response.status_code == 403, (label, path, response.status_code)
    assert _error_code(response) == "FORBIDDEN", (label, path)


def test_student_is_denied_the_staff_approval_capability() -> None:
    """Student -> staff/faculty capability is denied."""
    with _as(STUDENT_A_USER):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"


def test_student_is_denied_the_faculty_ingestion_capability() -> None:
    """The shared staff/faculty ingestion capability is not student-reachable."""
    with (
        _as(STUDENT_A_USER),
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_knowledge_source", return_value=None),
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_A},
        )
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/admin/students/pending"),
        ("POST", f"/api/v1/admin/students/{STUDENT_A_ROW}/approve"),
        ("POST", f"/api/v1/admin/students/{STUDENT_A_ROW}/reject"),
    ],
)
def test_faculty_is_denied_the_staff_only_approval_capability(
    method: str, path: str
) -> None:
    """Faculty is NOT part of the admin/staff approval boundary.

    This is the ONE capability that distinguishes Staff from Faculty today.
    """
    with _as(FACULTY_A_USER):
        response = client.request(method, path, headers=AUTH_HEADERS)
    assert response.status_code == 403, (path, response.status_code)
    assert _error_code(response) == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 2. Cross-tenant isolation
# ---------------------------------------------------------------------------


def test_staff_cannot_redirect_the_approval_queue_to_another_institution() -> None:
    """Staff A -> Institution B is denied at the query parameter."""
    with (
        _as(STAFF_A_USER),
        patch("app.services.admin_academics.academics_repo.list_pending_students", return_value=[]) as repo,
    ):
        response = client.get(
            "/api/v1/admin/students/pending",
            headers=AUTH_HEADERS,
            params={"institution_id": INST_B},
        )
    assert response.status_code == 403
    assert _error_code(response) == "TENANT_MISMATCH"
    repo.assert_not_called()


def test_staff_cannot_approve_a_student_from_another_institution() -> None:
    """Staff A -> Institution B student row is denied.

    The real service runs (only the data layer is doubled) so the tenant check
    inside ``_resolve_approval_target`` is genuinely exercised.
    """
    with (
        _as(STAFF_A_USER),
        patch("app.services.admin_academics.get_admin_client", return_value=MagicMock()),
        patch(
            "app.services.admin_academics.academics_repo.get_student_for_approval",
            return_value={
                "student_id": STUDENT_B_ROW,
                "institution_id": INST_B,
                "approval_status": "pending",
                "user_id": "u-1",
            },
        ) as target,
        patch(
            "app.services.admin_academics.academics_repo.set_student_approval_status",
            return_value=None,
        ) as write,
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B_ROW}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert _error_code(response) == "TENANT_MISMATCH"
    target.assert_called_once()
    write.assert_not_called()


def test_staff_cannot_list_students_at_all() -> None:
    """Staff is not an admin, so the role gate rejects before any query."""
    with (
        _as(STAFF_A_USER),
        patch("app.services.admin_academics.academics_repo.list_students", return_value=[]) as repo,
    ):
        response = client.get(
            "/api/v1/admin/students",
            headers=AUTH_HEADERS,
            params={"institution_id": INST_B},
        )
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"
    repo.assert_not_called()


def _source_row(institution_id: str) -> dict:
    return {"knowledge_source_id": KNOWLEDGE_SOURCE_B, "institution_id": institution_id}


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_cannot_ingest_into_another_institution(
    principal: dict, label: str
) -> None:
    """Institution A staff/faculty -> Institution B knowledge source is denied."""
    with (
        _as(principal),
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_knowledge_source", return_value=_source_row(INST_B)),
        patch("app.api.ingestion.ingest_document", new=AsyncMock()) as ingest,
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_B},
        )
    assert response.status_code == 403, label
    assert _error_code(response) == "TENANT_MISMATCH", label
    ingest.assert_not_called()


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_cannot_chat_as_another_institution(
    principal: dict, label: str
) -> None:
    """AI Assistant tenant isolation: a client-supplied institution cannot win."""
    with (
        _as(principal),
        patch("app.main.process_chat_request", return_value=None) as process,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "hello", "institution_id": INST_B},
        )
    assert response.status_code == 403, label
    assert _error_code(response) == "TENANT_MISMATCH", label
    process.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Fail-closed institution scope
# ---------------------------------------------------------------------------


def _tenantless_principal(role: str) -> dict:
    """A role principal holding a PLATFORM grant with no institution scope."""
    uid = f"72800000-0000-0000-0000-0000000000{len(role):02d}"
    return {
        "user_id": uid,
        "auth_user_id": uid,
        "email": f"{role}@example.edu",
        "status": "active",
        "roles": [role],
        "institution_id": None,
        "role_assignments": [_grant(role, None)],
    }


@pytest.mark.parametrize("role", STAFF_OR_FACULTY)
def test_platform_scoped_principal_is_not_unrestricted_authority(role: str) -> None:
    """A tenant-less staff/faculty grant fails closed; it is never platform power.

    The role exists but its platform scope is not an institution scope, so the
    request is refused BEFORE any queue is read.
    """
    with (
        _as(_tenantless_principal(role)),
        patch(
            "app.services.admin_academics.academics_repo.list_pending_students",
            return_value=[],
        ) as repo,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _error_code(response) in {"FORBIDDEN", "SCOPE_MISSING"}
    repo.assert_not_called()


@pytest.mark.parametrize("role", STAFF_OR_FACULTY)
def test_suspended_institution_fails_closed_for_staff_and_faculty(role: str) -> None:
    """An inactive institution revokes staff/faculty capability immediately."""
    principal = _principal(f"72900000-0000-0000-0000-00000000000{role}", role, INST_A)
    with (
        _as(principal, institution_active=False),
        patch(
            "app.services.admin_academics.academics_repo.list_pending_students",
            return_value=[],
        ) as repo,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _error_code(response) in {"FORBIDDEN", "TENANT_INACTIVE"}
    repo.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Deactivated user behaviour
# ---------------------------------------------------------------------------


DEACTIVATED_USERS = [
    (DEACTIVATED_STAFF_USER, "staff"),
    (DEACTIVATED_FACULTY_USER, "faculty"),
]


def test_deactivated_staff_cannot_use_the_approval_queue() -> None:
    with (
        _as(DEACTIVATED_STAFF_USER),
        patch("app.services.admin_academics.academics_repo.list_pending_students", return_value=[]) as repo,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _error_code(response) == "ACCOUNT_INACTIVE"
    repo.assert_not_called()


def test_deactivated_staff_cannot_approve_a_student() -> None:
    with (
        _as(DEACTIVATED_STAFF_USER),
        patch(
            "app.services.admin_academics.academics_repo.get_student_for_approval",
            return_value={"student_id": STUDENT_A_ROW},
        ) as repo,
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A_ROW}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert _error_code(response) == "ACCOUNT_INACTIVE"
    repo.assert_not_called()


@pytest.mark.parametrize("principal,label", DEACTIVATED_USERS)
def test_deactivated_staff_and_faculty_cannot_ingest(principal: dict, label: str) -> None:
    with (
        _as(principal),
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_knowledge_source", return_value=_source_row(INST_A)),
        patch("app.api.ingestion.ingest_document", new=AsyncMock()) as ingest,
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_A},
        )
    assert response.status_code == 403, label
    assert _error_code(response) == "ACCOUNT_INACTIVE", label
    ingest.assert_not_called()


@pytest.mark.parametrize("principal,label", DEACTIVATED_USERS)
def test_deactivated_staff_and_faculty_cannot_use_the_ai_assistant(
    principal: dict, label: str
) -> None:
    with (
        _as(principal),
        patch("app.main.process_chat_request", return_value=None) as process,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "hello", "institution_id": INST_A},
        )
    assert response.status_code == 403, label
    assert _error_code(response) == "ACCOUNT_INACTIVE", label
    process.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Super Admin must not inherit institution staff/faculty permissions
# ---------------------------------------------------------------------------

SUPER_ADMIN_MUST_NOT_REACH = [
    ("GET", "/api/v1/admin/students/pending"),
    ("GET", "/api/v1/admin/dashboard"),
    ("GET", "/api/v1/admin/memberships"),
    ("GET", "/api/v1/admin/students"),
]


@pytest.mark.parametrize("method,path", SUPER_ADMIN_MUST_NOT_REACH)
def test_super_admin_does_not_inherit_institution_staff_faculty_permissions(
    method: str, path: str
) -> None:
    """Platform authority does NOT imply institution staff/faculty capability."""
    with _as(SUPER_ADMIN_USER):
        response = client.request(method, path, headers=AUTH_HEADERS)
    assert response.status_code == 403, (path, response.status_code, response.text)
    assert _error_code(response) == "FORBIDDEN"


def test_super_admin_does_not_inherit_the_staff_faculty_ingestion_capability() -> None:
    with (
        _as(SUPER_ADMIN_USER),
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.ingest_document", new=AsyncMock()) as ingest,
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_A},
        )
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"
    ingest.assert_not_called()


def test_super_admin_does_not_inherit_the_institution_chat_capability() -> None:
    with (
        _as(SUPER_ADMIN_USER),
        patch("app.main.process_chat_request", return_value=None) as process,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "hello", "institution_id": INST_A},
        )
    assert response.status_code == 403
    assert _error_code(response) == "FORBIDDEN"
    process.assert_not_called()


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_are_still_denied_the_platform_surface(
    principal: dict, label: str
) -> None:
    """The boundary is symmetric: neither direction leaks."""
    with _as(principal):
        response = client.get("/api/v1/platform/institutions", headers=AUTH_HEADERS)
    assert response.status_code == 403, label
    assert _error_code(response) == "FORBIDDEN", label


# ---------------------------------------------------------------------------
# 6. Role escalation
# ---------------------------------------------------------------------------


def _route_paths() -> set[str]:
    """Every registered path, including those on included sub-routers."""
    return {
        route.path
        for route in app.routes
        if isinstance(getattr(route, "path", None), str)
    }


def test_no_generic_role_editing_interface_exists() -> None:
    """There is deliberately no generic `PATCH /users/{id}` role interface."""
    paths = _route_paths()
    assert "/api/v1/users/{user_id}" not in paths
    assert "/api/v1/users/{user_id}/role" not in paths
    assert "/api/v1/admin/roles" not in paths


@pytest.mark.parametrize(
    "field", ["institution_id", "requested_role", "user_id", "role", "organization_id"]
)
def test_membership_decision_body_forbids_role_and_institution_input(field: str) -> None:
    """A client can never name a role or an institution on a decision request."""
    with _as(ADMIN_A_USER):
        response = client.post(
            "/api/v1/admin/memberships/requests/"
            "00000000-0000-0000-0000-000000000001/approve",
            headers=AUTH_HEADERS,
            json={field: "staff"},
        )
    assert response.status_code == 422, field


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_cannot_reach_the_onboarding_lifecycle(
    principal: dict, label: str
) -> None:
    """The Phase 7.23 request queue, roster and lifecycle are admin-only."""
    for method, path in (
        ("GET", "/api/v1/admin/memberships/requests"),
        ("GET", "/api/v1/admin/memberships"),
        ("POST", f"/api/v1/admin/memberships/{STAFF_A}/deactivate"),
        ("POST", f"/api/v1/admin/memberships/{STAFF_A}/reactivate"),
    ):
        with _as(principal):
            response = client.request(method, path, headers=AUTH_HEADERS)
        assert response.status_code == 403, (label, method, path, response.status_code)
        assert _error_code(response) == "FORBIDDEN", (label, method, path)


# ---------------------------------------------------------------------------
# 7. Positive capability evidence (not merely denial)
# ---------------------------------------------------------------------------


def test_the_ingestion_dependency_allows_exactly_the_three_operational_roles() -> None:
    """`/documents/*` is the sole non-chat capability shared by staff + faculty."""
    from app.api import ingestion

    source = inspect.getsource(ingestion)
    match = re.search(
        r'_INGEST_ALLOWED = require_institution_roles\(([^)]*)\)', source
    )
    assert match is not None
    assert re.findall(r'"([a-z_]+)"', match.group(1)) == [
        "admin",
        "staff",
        "faculty",
    ]


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_reach_ingestion_within_their_own_institution(
    principal: dict, label: str
) -> None:
    """The shared knowledge capability IS implemented, not merely denied."""
    with (
        _as(principal),
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch(
            "app.api.ingestion.get_knowledge_source",
            return_value=_source_row(INST_A),
        ),
        patch(
            "app.api.ingestion.ingest_document",
            new=AsyncMock(
                return_value={
                    "knowledge_source_id": KNOWLEDGE_SOURCE_A,
                    "document_id": "00000000-0000-0000-0000-0000000000d1",
                    "document_version_id": "00000000-0000-0000-0000-0000000000d2",
                    "processing_run_id": "00000000-0000-0000-0000-0000000000d3",
                    "storage_object_key": "institution-a/doc.txt",
                    "status": "queued",
                }
            ),
        ) as ingest,
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            files={"file": ("a.txt", b"hello", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_A},
        )
    assert response.status_code == 201, (label, response.text)
    ingest.assert_awaited_once()


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_ai_assistant_is_reachable_in_tenant_for_staff_and_faculty(
    principal: dict, label: str
) -> None:
    """The AI Assistant capability IS implemented and tenant-pinned."""
    from app.schemas.chat import ChatResponse

    answer = ChatResponse(
        user_query="hello",
        session_id="00000000-0000-0000-0000-0000000000cc",
        conversation_id="00000000-0000-0000-0000-0000000000aa",
        message_id="00000000-0000-0000-0000-0000000000bb",
        answer="ok",
        status="success",
    )
    with (
        _as(principal),
        patch("app.main.resolve_session_context", return_value={"sources": []}),
        patch("app.main.process_chat_request", return_value=answer) as process,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "hello", "institution_id": INST_A},
        )
    assert response.status_code == 200, (label, response.text)
    pinned = process.call_args.kwargs["current_user"]
    assert pinned["institution_id"] == INST_A, label


def test_staff_reaches_the_approval_queue_within_its_own_institution() -> None:
    """The ONE staff-specific operational capability is proven reachable."""
    with (
        _as(STAFF_A_USER),
        patch(
            "app.services.admin_academics.academics_repo.list_pending_students",
            return_value=[],
        ) as repo,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200, response.text
    repo.assert_called_once()
    # The queue is pinned to the server-resolved institution, never a
    # client-supplied one.
    assert repo.call_args.args[1] == UUID(INST_A)


# ---------------------------------------------------------------------------
# 8. Student-scope model — proven from the schema ledger, not assumed
# ---------------------------------------------------------------------------

_MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def _migration_sql() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(_MIGRATIONS.glob("*.sql"))
    )


def _created_tables() -> set[str]:
    sql = _migration_sql()
    return {
        match.lower()
        for match in re.findall(r'CREATE TABLE[^;]*?"public"\."([a-z_]+)"', sql)
    }


def _table_body(table: str) -> str:
    sql = _migration_sql()
    match = re.search(
        rf'CREATE TABLE[^;]*?"public"\."{table}"\s*\((.*?)\);', sql, re.S
    )
    assert match is not None, f"table {table} not found in the migration ledger"
    return match.group(1).lower()


@pytest.mark.parametrize(
    "table",
    ["faculties", "faculty", "staffs", "staff", "staff_profiles", "faculty_profiles"],
)
def test_no_staff_or_faculty_profile_table_exists(table: str) -> None:
    """There is no staffs/faculty profile table anywhere in the schema ledger."""
    assert table not in _created_tables()


@pytest.mark.parametrize(
    "table",
    [
        "teaching_assignments",
        "faculty_assignments",
        "course_faculty",
        "instructor_assignments",
        "class_teachers",
        "faculty_courses",
        "faculty_students",
    ],
)
def test_no_teaching_assignment_or_faculty_student_scope_table_exists(table: str) -> None:
    """The Faculty -> Student scope relationship is NOT implemented."""
    assert table not in _created_tables()


def test_the_only_staff_faculty_scope_is_the_institution_role_grant() -> None:
    """`user_roles.scope_id` is the ONLY scope staff/faculty hold.

    This is the authoritative student-scope finding: staff and faculty are
    institution-scoped BY ROLE, with no narrower academic-assignment layer.
    """
    from app.core.security import SUPPORTED_ROLES

    assert "staff" in SUPPORTED_ROLES
    assert "faculty" in SUPPORTED_ROLES

    # `scope_type` / `scope_id` were added to the EXISTING user_roles table by
    # ALTER TABLE in the Phase 6.13 migration, not declared in CREATE TABLE.
    sql = _migration_sql()
    for column in ("scope_type", "scope_id", "scope_organization_id"):
        assert re.search(
            rf'ALTER TABLE "public"\."user_roles"\s*'
            rf'ADD COLUMN IF NOT EXISTS "{column}"',
            sql,
        ), column

    columns = _table_body("user_roles")
    for forbidden in ("course_id", "department_id", "section_id", "program_id"):
        assert forbidden not in columns, forbidden


def test_institution_membership_request_carries_no_assignment_semantics() -> None:
    """Onboarding metadata is NOT an academic assignment relationship."""
    columns = _table_body("institution_membership_requests")
    # `department` / `designation` are free-text onboarding metadata only.
    assert '"department"' in columns
    assert '"designation"' in columns
    for forbidden in ("course_id", "section_id", "program_id", "faculty_id"):
        assert forbidden not in columns, forbidden
    # Role escalation is structurally impossible at the database level.
    assert "array['staff'::text, 'faculty'::text]" in columns


def test_academic_tables_exist_but_carry_no_faculty_owner_relationship() -> None:
    """Courses/departments/sections exist, but none is linked to a faculty user.

    This is precisely why no faculty -> student scope can be derived today.
    """
    created = _created_tables()
    for academic_table in ("courses", "departments", "sections", "course_offerings"):
        assert academic_table in created, academic_table

    sql = _migration_sql()
    for pattern in (
        r'course_offerings[^;]*?REFERENCES "public"\."users"',
        r'sections[^;]*?REFERENCES "public"\."users"',
        r'courses[^;]*?REFERENCES "public"\."users"',
        r'courses[^;]*?"(?:instructor|faculty|teacher|owner)_user_id"',
        r'sections[^;]*?"(?:instructor|faculty|teacher)_user_id"',
    ):
        assert not re.search(pattern, sql, re.S | re.I), pattern


def test_no_staff_or_faculty_router_exists() -> None:
    """Capability is expressed by role dependencies, not by role-specific APIs."""
    paths = _route_paths()
    assert not [p for p in paths if p.startswith("/api/v1/staff")]
    assert not [p for p in paths if p.startswith("/api/v1/faculty")]