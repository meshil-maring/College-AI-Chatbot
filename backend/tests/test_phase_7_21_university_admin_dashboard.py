"""Phase 7.21 — University Admin operational dashboard.

Two institutions, two admins, one rule: the dashboard describes exactly the
institution the SERVER resolved for the caller, and nothing else.

The fixtures deliberately route through the real Phase 7.20 dependency
(``require_institution_roles`` -> ``resolve_institution_authorization_context``)
and only stub the authorization module's service-role client, so the guard logic
under test is the production one.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.admin import _ADMIN, _APPROVAL
from app.core.security import get_current_user
from app.main import app
from tests.dashboard_contract import build_dashboard

client = TestClient(app, raise_server_exceptions=False)

INST_A = "71000000-0000-0000-0000-00000000000a"
INST_B = "71000000-0000-0000-0000-00000000000b"
ADMIN_A = "72000000-0000-0000-0000-00000000000a"
ADMIN_B = "72000000-0000-0000-0000-00000000000b"
STUDENT_A = "73000000-0000-0000-0000-00000000000a"
FACULTY_A = "73100000-0000-0000-0000-00000000000a"
STAFF_A = "73200000-0000-0000-0000-00000000000a"
SUPER_ADMIN = "73400000-0000-0000-0000-00000000000a"

AUTH_HEADERS = {"Authorization": "Bearer phase721.token"}

# Distinct, non-zero numbers per tenant so any cross-tenant bleed is visible.
DASHBOARD_A = build_dashboard(
    name="Alpha University",
    code="ALPHA",
    total_students=11,
    pending_approvals=2,
    approved=9,
    active_students=8,
    sources_total=5,
    sources_active=4,
    documents_total=13,
    active_faqs=6,
    active_notices=3,
    attendance_records=101,
    test_results=202,
    results=303,
)
DASHBOARD_B = build_dashboard(
    name="Beta Institute",
    code="BETA",
    total_students=77,
    pending_approvals=9,
    approved=68,
    active_students=55,
    sources_total=21,
    sources_active=17,
    documents_total=88,
    active_faqs=31,
    active_notices=19,
    attendance_records=707,
    test_results=808,
    results=909,
)
DASHBOARD_BY_INSTITUTION = {
    INST_A: DASHBOARD_A,
    INST_B: DASHBOARD_B,
}


def _grant(role: str, institution_id: str | None, scope_type: str = "institution") -> dict:
    return {
        "role": role,
        "scope_type": scope_type,
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
    scope_type: str = "institution",
) -> dict:
    assignments = (
        [_grant(role, institution_id, scope_type)] if institution_id is not None else []
    )
    return {
        "user_id": user_id,
        "auth_user_id": user_id,
        "email": f"{role}@example.edu",
        "status": status,
        "roles": [role],
        # Deliberately None: the dependency must use role_assignments.scope_id.
        "institution_id": None,
        "role_assignments": assignments,
    }


ADMIN_A_USER = _principal(ADMIN_A, "admin", INST_A)
ADMIN_B_USER = _principal(ADMIN_B, "admin", INST_B)
STUDENT_USER = _principal(STUDENT_A, "student", INST_A)
FACULTY_USER = _principal(FACULTY_A, "faculty", INST_A)
STAFF_USER = _principal(STAFF_A, "staff", INST_A)
SUPER_ADMIN_USER = _principal(SUPER_ADMIN, "super_admin", None, scope_type="platform")
# An `admin` role row that is platform-scoped, not institution-scoped.
PLATFORM_SCOPED_ADMIN = _principal(ADMIN_A, "admin", INST_A, scope_type="platform")
# A role row with no tenant at all.
TENANTLESS_ADMIN = _principal(ADMIN_A, "admin", None)
INACTIVE_ADMIN = _principal(ADMIN_A, "admin", INST_A, status="inactive")


@contextmanager
def _authenticated(
    principal: dict,
    *,
    institution_active: bool = True,
    dashboard_response=None,
):
    """Run as ``principal``, with the dashboard service replaced by a mock.

    Only the data layer is stubbed. The Phase 7.20 dependency
    (``require_institution_roles``) and its lifecycle verification run for
    real, so these tests exercise the production authorization guard.
    """
    app.dependency_overrides[get_current_user] = lambda: principal
    grants = principal.get("role_assignments") or []
    institution = (
        {"status": "active", "is_active": True}
        if institution_active and grants
        else {"status": "suspended", "is_active": False}
    )

    def _tenant_scoped_dashboard(*, institution_id, **_kwargs):
        """Return the fixture belonging to the tenant the API layer resolved."""
        return DASHBOARD_BY_INSTITUTION.get(
            str(institution_id), build_dashboard(name="Unknown", code="UNK")
        )

    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch(
            "app.services.authorization.tenancy_repo.get_institution_by_id",
            return_value=institution,
        ),
        patch(
            "app.services.admin_dashboard.get_admin_client", return_value=MagicMock()
        ),
        patch(
            "app.services.admin_dashboard.knowledge_repo.list_notices",
            return_value=[],
        ),
        patch(
            "app.api.admin.admin_dashboard.get_dashboard_summary",
            side_effect=dashboard_response or _tenant_scoped_dashboard,
        ) as service,
    ):
        yield service
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _clean_dependencies():
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)
    yield
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)


# ============================================================================
# 1-4. Admin A sees A; Admin B sees B; neither sees the other.
# ============================================================================


def test_admin_a_receives_institution_a_metrics() -> None:
    with _authenticated(ADMIN_A_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["institution"] == {"name": "Alpha University", "code": "ALPHA", "status": "active"}
    assert body["students"]["total"] == 11
    assert body["academics"]["attendance_records"] == 101


def test_admin_b_receives_institution_b_metrics() -> None:
    with _authenticated(ADMIN_B_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["institution"] == {"name": "Beta Institute", "code": "BETA", "status": "active"}
    assert body["students"]["total"] == 77
    assert body["academics"]["attendance_records"] == 707


def test_admin_a_cannot_see_institution_b_data() -> None:
    with _authenticated(ADMIN_A_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    raw = response.text
    for leak in ("Beta Institute", "BETA", INST_B, "77", "909", "707"):
        assert leak not in raw, f"Admin A dashboard leaked {leak!r}"


def test_admin_b_cannot_see_institution_a_data() -> None:
    with _authenticated(ADMIN_B_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    raw = response.text
    for leak in ("Alpha University", "ALPHA", INST_A, "11", "303", "101"):
        assert leak not in raw, f"Admin B dashboard leaked {leak!r}"


def test_service_only_ever_receives_the_authorized_tenant() -> None:
    """The API layer hands the service exactly the resolved institution."""
    with _authenticated(ADMIN_A_USER) as service:
        client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
        assert service.call_args.kwargs["institution_id"] == UUID(INST_A)
    with _authenticated(ADMIN_B_USER) as service:
        client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
        assert service.call_args.kwargs["institution_id"] == UUID(INST_B)


# ============================================================================
# 5-6. Client-supplied tenant values must not move the scope.
# ============================================================================


@pytest.mark.parametrize(
    "params",
    [
        {"institution_id": INST_B},
        {"institution_id": INST_B, "role": "super_admin"},
        {"scope_type": "platform"},
        {"institution_code": "BETA"},
        {"code": "BETA"},
        {"tenant": INST_B},
    ],
)
def test_client_supplied_institution_values_never_alter_scope(params) -> None:
    """Phase 7.21 §9 — a foreign tenant in ANY parameter changes nothing.

    The parameter no longer exists on the endpoint, so FastAPI ignores it. The
    response is byte-for-byte Admin A's own dashboard either way.
    """
    with _authenticated(ADMIN_A_USER):
        clean = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
        manipulated = client.get(
            "/api/v1/admin/dashboard", headers=AUTH_HEADERS, params=params
        )
    assert clean.status_code == 200
    assert manipulated.status_code == 200
    assert manipulated.json() == clean.json()
    assert manipulated.json()["institution"]["code"] == "ALPHA"


def test_foreign_institution_id_is_never_echoed_back() -> None:
    with _authenticated(ADMIN_A_USER):
        response = client.get(
            f"/api/v1/admin/dashboard?institution_id={INST_B}", headers=AUTH_HEADERS
        )
    assert INST_B not in response.text


# ============================================================================
# 7-8. Scope and lifecycle denial.
# ============================================================================


def test_tenantless_admin_is_denied() -> None:
    with _authenticated(TENANTLESS_ADMIN):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] in ("SCOPE_MISSING", "SCOPE_INCONSISTENT")


def test_platform_scoped_admin_is_denied() -> None:
    """A platform `admin` role row is NOT a University Admin grant.

    The role matches, so Phase 7.20 raises FORBIDDEN (the role exists but its
    scope is insufficient) rather than SCOPE_MISSING. Either way it is 403 and
    the dashboard is unreachable — platform authority is not inherited.
    """
    with _authenticated(PLATFORM_SCOPED_ADMIN):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] in (
        "FORBIDDEN",
        "SCOPE_MISSING",
        "SCOPE_INCONSISTENT",
    )


def test_inactive_institution_is_denied() -> None:
    with _authenticated(ADMIN_A_USER, institution_active=False):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_INACTIVE"


def test_inactive_account_is_denied() -> None:
    with _authenticated(INACTIVE_ADMIN):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


# ============================================================================
# 9. Zero-data institution.
# ============================================================================


def test_zero_data_institution_renders_successfully() -> None:
    """0 students / 0 documents / 0 FAQs / 0 notices is a normal 200, not an error."""
    empty = build_dashboard(name="Fresh University", code="FRESH", status="active")

    def _empty(*, institution_id, **kwargs):
        assert str(institution_id) == INST_B
        return empty

    with _authenticated(ADMIN_B_USER, dashboard_response=_empty):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["students"] == {
        "total": 0,
        "pending_approvals": 0,
        "approved": 0,
        "active": 0,
    }
    assert body["knowledge"]["documents_total"] == 0
    assert body["knowledge"]["failed_processing_runs"] is None
    assert body["communication"]["active_faqs"] == 0
    assert body["communication"]["active_notices"] == 0
    assert body["communication"]["recent_notices"] == []
    assert body["academics"] == {
        "attendance_records": 0,
        "test_results": 0,
        "results": 0,
    }


# ============================================================================
# 10-13. Access control.
# ============================================================================


@pytest.mark.parametrize(
    ("principal", "label"),
    [
        (STUDENT_USER, "student"),
        (STAFF_USER, "staff"),
        (FACULTY_USER, "faculty"),
    ],
)
def test_non_admin_roles_cannot_access_the_admin_dashboard(principal, label) -> None:
    """§15 — student/staff/faculty are not defined as dashboard consumers.

    Staff keeps its Phase 6.4/6.18 approval-queue exception only; it gains no
    dashboard access from this phase.
    """
    with _authenticated(principal):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403, label
    assert response.json()["error"]["code"] in ("FORBIDDEN", "SCOPE_MISSING")


def test_super_admin_does_not_inherit_university_admin_dashboard() -> None:
    """§15 — platform authority is a separate surface, never inherited."""
    with _authenticated(SUPER_ADMIN_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] in ("FORBIDDEN", "SCOPE_MISSING")


def test_super_admin_platform_surface_is_unchanged() -> None:
    """The dashboard work must not disturb the separate Super Admin surface."""
    db = MagicMock()
    db.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
    app.dependency_overrides[get_current_user] = lambda: SUPER_ADMIN_USER
    with (
        patch(
            "app.db.supabase.get_super_admin_authorization",
            new=AsyncMock(
                return_value={"status": "active", "has_platform_grant": True}
            ),
        ),
        patch(
            "app.services.platform_institutions.get_admin_client", return_value=db
        ),
    ):
        response = client.get("/api/v1/platform/institutions", headers=AUTH_HEADERS)
    app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 200
    assert response.json() == {"institutions": []}


def test_unauthenticated_dashboard_request_is_rejected() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_ADMIN, None)
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


# ============================================================================
# 14. Internal errors are normalized, never leaked.
# ============================================================================


def test_internal_dashboard_error_is_normalized() -> None:
    """A backend blow-up must surface as the project's safe 500 envelope."""
    def _explode(**_kwargs):
        raise RuntimeError(
            "connection to server at 10.0.0.5 failed: SELECT * FROM students"
        )

    with _authenticated(ADMIN_A_USER, dashboard_response=_explode):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "SELECT" not in response.text
    assert "10.0.0.5" not in response.text
    assert "students" not in response.text


def test_response_model_reprojects_and_drops_stray_service_fields() -> None:
    """A service returning extra keys cannot widen the public contract.

    ``response_model=DashboardResponse`` re-projects the payload, so anything
    the service invents beyond the declared sections is dropped rather than
    forwarded to the client.
    """
    leaky_payload = {
        **build_dashboard().model_dump(),
        "service_role_key": "sk-live-should-never-appear",
        "institution_id": INST_B,
        "raw_rows": [{"secret": "value"}],
    }

    with _authenticated(
        ADMIN_A_USER, dashboard_response=lambda **_kwargs: leaky_payload
    ):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert set(response.json()) == EXPECTED_TOP_LEVEL
    assert "sk-live-should-never-appear" not in response.text
    assert INST_B not in response.text
    assert "raw_rows" not in response.text


# ============================================================================
# 18. Response contract scanning.
# ============================================================================

EXPECTED_TOP_LEVEL = {
    "institution",
    "students",
    "knowledge",
    "communication",
    "academics",
    "quick_actions",
}

FORBIDDEN_KEYS = {
    "institution_id",
    "organization_id",
    "user_id",
    "auth_user_id",
    "actor_user_id",
    "audit_id",
    "notice_id",
    "faq_id",
    "student_id",
    "record_id",
    "record_data",
    "ip_address",
    "user_agent",
    "scope_type",
    "scope_id",
    "roles",
    "role_assignments",
    "service_role",
    "service_role_key",
    "password",
    "token",
    "api_key",
    "authorization_context",
    "counts",
    "recent_audit",
}


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


def test_response_contains_no_unexpected_internal_fields() -> None:
    """§18 — walk the whole payload; no key may be on the deny-list."""
    with _authenticated(ADMIN_A_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    body = response.json()
    assert set(body) == EXPECTED_TOP_LEVEL
    for key in _walk_keys(body):
        assert key not in FORBIDDEN_KEYS, f"forbidden key in dashboard: {key}"

    assert set(body["institution"]) == {"name", "code", "status"}
    assert set(body["students"]) == {"total", "pending_approvals", "approved", "active"}
    assert set(body["knowledge"]) == {
        "sources_total",
        "sources_active",
        "documents_total",
        "failed_processing_runs",
    }
    assert set(body["communication"]) == {
        "active_faqs",
        "active_notices",
        "recent_notices",
    }
    assert set(body["academics"]) == {"attendance_records", "test_results", "results"}


class _RecordingClient:
    """Service-role client double that records every ``.eq()`` tenant filter."""

    def __init__(self):
        self.filters: dict[str, list[tuple]] = {}
        self.tables: list[str] = []
        self.selects: list[tuple[str, tuple]] = []

    def table(self, name):
        self.tables.append(name)
        counts = MagicMock(count=0, data=[])
        m = MagicMock()
        sel = m.select.return_value

        def _select(*args, **kwargs):
            self.selects.append((name, args, kwargs))
            return sel

        m.select.side_effect = _select

        def _eq(*args, **kwargs):
            self.filters.setdefault(name, []).append(args)
            return sel

        sel.eq.side_effect = _eq
        sel.in_.side_effect = lambda *a, **k: sel
        sel.execute.return_value = counts
        sel.eq.return_value.execute.return_value = counts
        sel.eq.return_value.eq.return_value.execute.return_value = counts
        sel.eq.return_value.in_.return_value.execute.return_value = counts
        return m


@contextmanager
def _real_service(db: _RecordingClient | None = None, notices=None):
    """Stub ONLY the data layer so the REAL dashboard service executes.

    ``app.services.authorization`` and ``app.services.admin_dashboard`` both hold
    a reference to the SAME ``app.repositories.tenancy`` module, so a single
    patch covers both: the row must satisfy the authorization lifecycle check
    (``status``/``is_active``) AND carry the display fields the dashboard reads.
    """
    db = db if db is not None else _RecordingClient()
    app.dependency_overrides[get_current_user] = lambda: ADMIN_A_USER
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch(
            "app.repositories.tenancy.get_institution_by_id",
            return_value=_institution_row(),
        ),
        patch("app.services.admin_dashboard.get_admin_client", return_value=db),
        patch(
            "app.services.admin_dashboard.knowledge_repo.list_notices",
            return_value=notices if notices is not None else [],
        ),
    ):
        yield db
    app.dependency_overrides.pop(get_current_user, None)


def _institution_row() -> dict:
    return {
        "institution_id": INST_A,
        "name": "Alpha University",
        "code": "ALPHA",
        "status": "active",
        "is_active": True,
    }


def test_real_service_projects_recent_notices_without_identifiers() -> None:
    """End-to-end through the real service: no ids, no body content."""
    notice_rows = [
        {
            "notice_id": "secret-notice-id",
            "institution_id": INST_B,
            "title": "Exam schedule",
            "content": "internal body",
            "category": "academic",
            "priority": "high",
            "is_active": True,
            "is_published": True,
            "is_pinned": False,
            "published_at": "2026-01-01T00:00:00Z",
            "created_by": "secret-user-id",
        }
    ]
    db = _RecordingClient()
    with _real_service(db, notices=notice_rows):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert len(body["communication"]["recent_notices"]) == 1
    assert set(body["communication"]["recent_notices"][0]) == {
        "title",
        "category",
        "priority",
        "published_at",
    }
    assert "secret-notice-id" not in response.text
    assert "secret-user-id" not in response.text
    assert "internal body" not in response.text


def test_real_service_issues_bounded_queries_for_one_institution() -> None:
    """Performance: query count is fixed by the metric count, not the data size.

    Several metrics legitimately share a table (four student-status counts all
    read ``students``); what matters is that the count is CONSTANT regardless of
    how many rows the institution has, i.e. there is no per-row (N+1) query, and
    that every one of them carries the tenant filter.
    """
    db = _RecordingClient()
    # Capture the recent-notice call so the bound can be asserted.
    with _real_service(db), patch(
        "app.services.admin_dashboard.knowledge_repo.list_notices",
        return_value=[],
    ) as notices_mock:
        first = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert "admin_audit_log" not in db.tables

    # Bounded: the recent-notice list is the only list read, and it is limited.
    assert notices_mock.call_args.kwargs["limit"] == 5

    # No repeated per-metric listing of students: the students table is only
    # ever COUNT-aggregated, never selected row-by-row.
    student_selects = [kwargs for name, _, kwargs in db.selects if name == "students"]
    assert student_selects, "expected student counts"
    assert all(kwargs.get("count") == "exact" for kwargs in student_selects), student_selects

    # Every directly-owned table carries the resolved tenant, and only that one.
    for name in ("students", "knowledge_sources", "faqs", "notices"):
        tenants = {f[1] for f in db.filters.get(name, []) if f[0] == "institution_id"}
        assert tenants == {INST_A}, (name, tenants)


def test_quick_actions_reference_existing_admin_capabilities() -> None:
    """Every quick action must be a real, already-implemented admin surface."""
    from app.services.admin_dashboard import QUICK_ACTIONS

    existing_views = {
        "approvals",
        "students",
        "attendance",
        "results",
        "test-results",
        "notices",
        "documents",
        "faqs",
    }
    # Run the REAL service so the shipped quick actions are what is asserted.
    db = _RecordingClient()
    with _real_service(db):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    actions = response.json()["quick_actions"]
    assert len(actions) == len(QUICK_ACTIONS)
    assert actions, "quick actions must not be empty"
    for action in actions:
        assert set(action) == {"view", "label", "description"}
        assert action["view"] in existing_views
        assert action["label"] and action["description"]


def _dashboard_routes() -> list:
    """Return the admin dashboard routes from the admin router itself.

    FastAPI's ``include_router`` wraps routes in ``_IncludedRouter`` objects
    that are not part of the public route model, so the admin router is
    inspected directly. This is the authoritative registration point for the
    endpoint contract.
    """
    from app.api.admin import router as admin_router

    return [route for route in admin_router.routes if route.path.endswith("/dashboard")]


def test_dashboard_is_the_only_dashboard_endpoint() -> None:
    """§5 — one coherent dashboard response, not several competing ones."""
    routes = _dashboard_routes()
    assert len(routes) == 1
    assert routes[0].path == "/admin/dashboard"
    # And the OpenAPI document publishes exactly one dashboard path.
    published = [
        path
        for path in app.openapi()["paths"]
        if "dashboard" in path and path.startswith("/api/v1/admin")
    ]
    assert published == ["/api/v1/admin/dashboard"]


def test_dashboard_route_declares_an_explicit_response_model() -> None:
    """§18 — explicit response schema, never an arbitrary row."""
    from app.schemas.admin_dashboard import DashboardResponse

    (route,) = _dashboard_routes()
    assert route.response_model is DashboardResponse


def test_dashboard_route_accepts_no_institution_parameter() -> None:
    """§6 — no client-supplied tenant exists for the dashboard to read."""
    (route,) = _dashboard_routes()
    query_params = {param.name for param in route.dependant.query_params}
    assert "institution_id" not in query_params
    assert query_params == set()
