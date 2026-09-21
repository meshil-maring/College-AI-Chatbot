"""Phase 6.16 — Student experience dashboard: backend contract gap tests.

The Phase 6.16 audit found that the student dashboard's Notices and Learning
Resources sections had NO student-scoped backend read path: institution notices
and knowledge sources were reachable only through ``/api/v1/admin/*``, which is
guarded by ``require_roles("admin")``. This suite covers the two additive,
read-only, tenant-scoped endpoints that close that gap, plus the security
properties the dashboard depends on:

    GET /api/v1/students/me/notices    -> own institution's published notices
    GET /api/v1/students/me/resources  -> own institution's published resources

Covered:
  * tenant isolation (institution A can never receive institution B rows);
  * publication filtering (active + published + unexpired notices; published
    knowledge sources only; notice/faq source types excluded from resources);
  * server-side identity (no client-supplied identity parameter exists);
  * eligibility (approved + active + institution active);
  * read-only enforcement (students get 403 from every privileged route);
  * data minimization (no internal ids, storage keys, tokens, or secrets).

No existing contract, table, or authorization rule is modified by this phase.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.repositories import student_dashboard as dashboard_repo
from app.schemas.student_notices import StudentNotice, StudentNoticeList
from app.schemas.student_resources import StudentResource, StudentResourceList
from app.services import student_notices as notices_service
from app.services import student_resources as resources_service

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "a1111111-0000-0000-0000-000000000001"
TENANT_B = "b2222222-0000-0000-0000-000000000002"
STUDENT_USER_ID = "71000000-0000-0000-0000-000000000001"
STUDENT_AUTH_USER_ID = "61000000-0000-0000-0000-000000000001"
STUDENT_ID = "30000000-0000-0000-0000-000000000151"
NOTICE_A = "50000000-0000-0000-0000-000000000001"
NOTICE_B = "50000000-0000-0000-0000-000000000002"
RESOURCE_A = "60000000-0000-0000-0000-000000000001"
RESOURCE_B = "60000000-0000-0000-0000-000000000002"


# ============================================================================
# Fixtures / helpers
# ============================================================================


def _student_user(user_id=STUDENT_USER_ID, tenant=TENANT_A):
    return {
        "user_id": user_id,
        "auth_user_id": STUDENT_AUTH_USER_ID,
        "email": "student@college.edu",
        "roles": ["student"],
        "institution_id": tenant,
    }


def _student_profile(institution_id=TENANT_A, approval_status="approved", is_active=True):
    return {
        "student_id": STUDENT_ID,
        "user_id": STUDENT_USER_ID,
        "institution_id": institution_id,
        "student_number": "STU100",
        "approval_status": approval_status,
        "is_active": is_active,
        "email": "student@college.edu",
        "status": "active",
        "auth_user_id": STUDENT_AUTH_USER_ID,
    }


def _db_for_student(profile=None, **kwargs):
    """Supabase stub whose ``students`` lookup returns the given profile."""
    db = MagicMock()
    row = _student_profile(**kwargs) if profile is None else profile
    chain = db.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = MagicMock(data=row)
    return db


def _notice_row(
    notice_id=NOTICE_A,
    institution_id=TENANT_A,
    title="Exam schedule update",
    content="Mid-term exams begin on 12 October.",
    category="exam",
    priority="high",
    is_active=True,
    is_published=True,
    is_pinned=False,
    published_at="2026-09-10T09:00:00+00:00",
    expires_at=None,
):
    return {
        "notice_id": notice_id,
        "institution_id": institution_id,
        "title": title,
        "content": content,
        "category": category,
        "priority": priority,
        "is_active": is_active,
        "is_published": is_published,
        "is_pinned": is_pinned,
        "published_at": published_at,
        "expires_at": expires_at,
    }


def _resource_row(
    knowledge_source_id=RESOURCE_A,
    institution_id=TENANT_A,
    source_type="handbook",
    title="Student Handbook",
    description="Official academic handbook.",
    lifecycle_status="published",
    effective_from="2026-07-01",
    effective_until=None,
    created_at="2026-07-01T00:00:00+00:00",
):
    return {
        "knowledge_source_id": knowledge_source_id,
        "institution_id": institution_id,
        "source_type": source_type,
        "title": title,
        "description": description,
        "lifecycle_status": lifecycle_status,
        "effective_from": effective_from,
        "effective_until": effective_until,
        "created_at": created_at,
        # Columns the student projection must NEVER expose.
        "storage_bucket": "college-private",
        "storage_object_key": "institution/handbook.pdf",
        "file_checksum": "deadbeef",
        "created_by_user_id": "91000000-0000-0000-0000-000000000001",
    }


def _norm(value):
    if isinstance(value, bool):
        return str(value)
    return None if value is None else str(value)


def _or_matches(row, expression):
    """Evaluate the single PostgREST ``or_`` expression this phase builds."""
    for clause in expression.split(","):
        clause = clause.strip()
        if clause.endswith(".is.null"):
            column = clause[: -len(".is.null")]
            if row.get(column) is None:
                return True
        elif ".gte." in clause:
            column, _, threshold = clause.partition(".gte.")
            value = row.get(column)
            if value is not None and str(value) >= threshold:
                return True
        else:  # pragma: no cover - defensive: unknown clause does not filter
            return True
    return False


class _FakeQueryBuilder:
    """Minimal PostgREST query builder that really filters/orders/limits rows.

    Recording every operation lets the tests assert the exact server-side
    filters (tenant scoping, publication filter, expiry filter) instead of
    trusting the projection alone.
    """

    def __init__(self, table_name, rows, calls):
        self._table = table_name
        self._rows = list(rows)
        self._calls = calls
        self._orders: list[tuple[str, bool]] = []
        self._limit: int | None = None

    def select(self, columns):
        self._calls.append((self._table, "select", columns))
        return self

    def eq(self, column, value):
        self._calls.append((self._table, "eq", column, value))
        self._rows = [r for r in self._rows if _norm(r.get(column)) == _norm(value)]
        return self

    def neq(self, column, value):
        self._calls.append((self._table, "neq", column, value))
        self._rows = [r for r in self._rows if _norm(r.get(column)) != _norm(value)]
        return self

    def or_(self, expression):
        self._calls.append((self._table, "or_", expression))
        self._rows = [r for r in self._rows if _or_matches(r, expression)]
        return self

    def order(self, column, desc=False):
        self._calls.append((self._table, "order", column, desc))
        self._orders.append((column, desc))
        return self

    def limit(self, count):
        self._calls.append((self._table, "limit", count))
        self._limit = count
        return self

    def execute(self):
        self._calls.append((self._table, "execute"))
        rows = list(self._rows)
        # PostgREST treats the FIRST `order` as the primary sort key, so the
        # orders are applied from least to most significant (Python's sort is
        # stable, which preserves the higher-precedence keys).
        for column, desc in reversed(self._orders):
            rows.sort(
                key=lambda r, c=column: (_norm(r.get(c)) is None, _norm(r.get(c))),
                reverse=desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return MagicMock(data=rows)


class _FakeClient:
    """Fake Supabase client holding one row set per table name."""

    def __init__(self, tables=None):
        self.tables = tables or {}
        self.calls: list[tuple] = []

    def table(self, name):
        return _FakeQueryBuilder(name, self.tables.get(name, []), self.calls)

    def operations(self, table, operation):
        return [c for c in self.calls if c[0] == table and c[1] == operation]


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# 1. Repository — tenant scoping
# ============================================================================


class TestRepositoryTenantScoping:
    def test_notice_query_always_filters_on_the_given_institution(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A, institution_id=TENANT_A),
                    _notice_row(notice_id=NOTICE_B, institution_id=TENANT_B, title="Other tenant"),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(db, TENANT_A)
        assert [r["notice_id"] for r in rows] == [NOTICE_A]
        assert ("notices", "eq", "institution_id", TENANT_A) in db.calls
        assert ("notices", "eq", "institution_id", TENANT_B) not in db.calls

    def test_notice_query_never_spans_institutions(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A, institution_id=TENANT_A),
                    _notice_row(notice_id=NOTICE_B, institution_id=TENANT_B),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(db, TENANT_B)
        assert [r["notice_id"] for r in rows] == [NOTICE_B]

    def test_resource_query_always_filters_on_the_given_institution(self):
        db = _FakeClient(
            {
                "knowledge_sources": [
                    _resource_row(knowledge_source_id=RESOURCE_A, institution_id=TENANT_A),
                    _resource_row(knowledge_source_id=RESOURCE_B, institution_id=TENANT_B),
                ]
            }
        )
        rows = dashboard_repo.list_published_resources(db, TENANT_A)
        assert [r["knowledge_source_id"] for r in rows] == [RESOURCE_A]
        assert ("knowledge_sources", "eq", "institution_id", TENANT_A) in db.calls

    def test_institution_id_is_a_mandatory_argument(self):
        with pytest.raises(TypeError):
            dashboard_repo.list_published_notices(_FakeClient())
        with pytest.raises(TypeError):
            dashboard_repo.list_published_resources(_FakeClient())



# ============================================================================
# 2. Repository — publication / expiry filtering
# ============================================================================


class TestRepositoryPublicationFiltering:
    def test_notices_require_active_and_published(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A),
                    _notice_row(notice_id=NOTICE_B, is_active=False),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(db, TENANT_A)
        assert [r["notice_id"] for r in rows] == [NOTICE_A]
        assert ("notices", "eq", "is_active", True) in db.calls
        assert ("notices", "eq", "is_published", True) in db.calls

    def test_unpublished_notices_are_never_returned(self):
        db = _FakeClient({"notices": [_notice_row(is_published=False)]})
        assert dashboard_repo.list_published_notices(db, TENANT_A) == []

    def test_expired_notices_are_excluded(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A, expires_at=None),
                    _notice_row(notice_id=NOTICE_B, expires_at="2000-01-01T00:00:00+00:00"),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(
            db, TENANT_A, now="2026-09-21T00:00:00+00:00"
        )
        assert [r["notice_id"] for r in rows] == [NOTICE_A]
        expiry_filters = [c for c in db.calls if c[1] == "or_"]
        assert expiry_filters, "the expiry boundary must always be applied"
        assert "expires_at.is.null" in expiry_filters[0][2]

    def test_future_dated_expiry_is_kept(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A, expires_at="2999-01-01T00:00:00+00:00")
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(
            db, TENANT_A, now="2026-09-21T00:00:00+00:00"
        )
        assert [r["notice_id"] for r in rows] == [NOTICE_A]

    def test_pinned_notices_come_first(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(
                        notice_id=NOTICE_A,
                        is_pinned=False,
                        published_at="2026-09-20T00:00:00+00:00",
                    ),
                    _notice_row(
                        notice_id=NOTICE_B,
                        is_pinned=True,
                        published_at="2026-09-01T00:00:00+00:00",
                    ),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(db, TENANT_A)
        assert [r["notice_id"] for r in rows] == [NOTICE_B, NOTICE_A]
        assert ("notices", "order", "is_pinned", True) in db.calls
        assert ("notices", "order", "published_at", True) in db.calls

    def test_notice_limit_is_applied_server_side(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A),
                    _notice_row(notice_id=NOTICE_B),
                ]
            }
        )
        assert len(dashboard_repo.list_published_notices(db, TENANT_A, limit=1)) == 1
        assert ("notices", "limit", 1) in db.calls

    def test_resources_require_published_lifecycle_status(self):
        db = _FakeClient(
            {
                "knowledge_sources": [
                    _resource_row(
                        knowledge_source_id=RESOURCE_A, lifecycle_status="published"
                    ),
                    _resource_row(
                        knowledge_source_id=RESOURCE_B, lifecycle_status="draft"
                    ),
                ]
            }
        )
        rows = dashboard_repo.list_published_resources(db, TENANT_A)
        assert [r["knowledge_source_id"] for r in rows] == [RESOURCE_A]
        assert ("knowledge_sources", "eq", "lifecycle_status", "published") in db.calls

    def test_resources_exclude_source_types_with_their_own_student_surface(self):
        db = _FakeClient(
            {
                "knowledge_sources": [
                    _resource_row(knowledge_source_id=RESOURCE_A, source_type="handbook"),
                    _resource_row(knowledge_source_id=RESOURCE_B, source_type="notice"),
                ]
            }
        )
        rows = dashboard_repo.list_published_resources(db, TENANT_A)
        assert [r["knowledge_source_id"] for r in rows] == [RESOURCE_A]
        assert ("knowledge_sources", "neq", "source_type", "notice") in db.calls
        assert ("knowledge_sources", "neq", "source_type", "faq") in db.calls

    def test_excluded_source_types_match_the_locked_public_vocabulary(self):
        """Drift guard against the locked Phase 6.13.8 source-type vocabulary."""
        from app.services.public_chat import PUBLIC_SOURCE_TYPES

        assert set(dashboard_repo.EXCLUDED_RESOURCE_SOURCE_TYPES) <= set(
            PUBLIC_SOURCE_TYPES
        )



# ============================================================================
# 3. Repository — projections exclude unsafe columns
# ============================================================================


class TestRepositoryProjections:
    def test_notice_projection_excludes_tenant_and_audit_columns(self):
        database = _FakeClient({"notices": []})
        dashboard_repo.list_published_notices(database, TENANT_A)
        projection = database.operations("notices", "select")[0][2]
        for forbidden in ("institution_id", "created_by", "updated_at"):
            assert forbidden not in projection

    def test_resource_projection_excludes_storage_and_identity_columns(self):
        database = _FakeClient({"knowledge_sources": []})
        dashboard_repo.list_published_resources(database, TENANT_A)
        projection = database.operations("knowledge_sources", "select")[0][2]
        for forbidden in (
            "storage_bucket",
            "storage_object_key",
            "file_checksum",
            "created_by_user_id",
            "institution_id",
            "document_id",
        ):
            assert forbidden not in projection

    def test_resource_projection_selects_only_benign_labels(self):
        database = _FakeClient({"knowledge_sources": []})
        dashboard_repo.list_published_resources(database, TENANT_A)
        projection = database.operations("knowledge_sources", "select")[0][2]
        for expected in (
            "knowledge_source_id",
            "source_type",
            "title",
            "description",
            "lifecycle_status",
            "effective_from",
            "effective_until",
        ):
            assert expected in projection


# ============================================================================
# 4. Service — identity is always server-derived
# ============================================================================


class TestServiceIdentityResolution:
    def test_notices_use_the_authenticated_students_own_institution(self):
        db = _db_for_student(institution_id=TENANT_A)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(
                dashboard_repo, "list_published_notices", return_value=[_notice_row()]
            ) as repo:
                result = notices_service.get_own_notices(_student_user(), client=db)
        assert repo.call_args[0][1] == TENANT_A
        assert result.total == 1

    def test_resources_use_the_authenticated_students_own_institution(self):
        db = _db_for_student(institution_id=TENANT_B)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(
                dashboard_repo, "list_published_resources", return_value=[]
            ) as repo:
                result = resources_service.get_own_resources(
                    _student_user(tenant=TENANT_B), client=db
                )
        assert repo.call_args[0][1] == TENANT_B
        assert result.total == 0

    def test_services_expose_no_identity_parameter(self):
        """A client cannot pass an institution/student id at all."""
        with pytest.raises(TypeError):
            notices_service.get_own_notices(_student_user(), institution_id=TENANT_B)
        with pytest.raises(TypeError):
            resources_service.get_own_resources(_student_user(), student_id=STUDENT_ID)



# ============================================================================
# 5. Service — eligibility, empty data, limits
# ============================================================================


class TestServiceEligibilityAndEdges:
    def test_missing_user_id_is_rejected(self):
        with pytest.raises(AppError) as exc:
            notices_service.get_own_notices({}, client=MagicMock())
        assert exc.value.status_code == 400
        assert exc.value.code == "INVALID_USER_CONTEXT"

    def test_student_without_profile_is_404(self):
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value
        chain.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with pytest.raises(AppError) as exc:
                resources_service.get_own_resources(_student_user(), client=db)
        assert exc.value.status_code == 404
        assert exc.value.code == "STUDENT_PROFILE_NOT_FOUND"

    def test_unapproved_student_is_rejected(self):
        db = _db_for_student(approval_status="pending")
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with pytest.raises(AppError) as exc:
                notices_service.get_own_notices(_student_user(), client=db)
        assert exc.value.status_code == 403
        assert exc.value.code == "STUDENT_NOT_APPROVED"

    def test_inactive_student_is_rejected(self):
        db = _db_for_student(is_active=False)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with pytest.raises(AppError) as exc:
                resources_service.get_own_resources(_student_user(), client=db)
        assert exc.value.status_code == 403
        assert exc.value.code == "STUDENT_INACTIVE"

    def test_student_without_a_tenant_fails_closed(self):
        db = _db_for_student(institution_id=None)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with pytest.raises(AppError) as exc:
                notices_service.get_own_notices(_student_user(tenant=None), client=db)
        assert exc.value.status_code == 403
        assert exc.value.code == "TENANT_MISMATCH"

    def test_empty_data_is_an_empty_list_not_an_error(self):
        db = _db_for_student()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(dashboard_repo, "list_published_notices", return_value=[]):
                notices = notices_service.get_own_notices(_student_user(), client=db)
            with patch.object(dashboard_repo, "list_published_resources", return_value=[]):
                resources = resources_service.get_own_resources(_student_user(), client=db)
        assert notices.items == [] and notices.total == 0
        assert resources.items == [] and resources.total == 0

    @pytest.mark.parametrize("limit", [0, -1, 21])
    def test_notice_limit_out_of_range_is_422(self, limit):
        with pytest.raises(AppError) as exc:
            notices_service.get_own_notices(
                _student_user(), limit=limit, client=MagicMock()
            )
        assert exc.value.status_code == 422
        assert exc.value.code == "INVALID_FILTER"

    @pytest.mark.parametrize("limit", [0, 51])
    def test_resource_limit_out_of_range_is_422(self, limit):
        with pytest.raises(AppError) as exc:
            resources_service.get_own_resources(
                _student_user(), limit=limit, client=MagicMock()
            )
        assert exc.value.status_code == 422
        assert exc.value.code == "INVALID_FILTER"


# ============================================================================
# 6. Schemas — data minimization
# ============================================================================


class TestStudentFacingSchemas:
    def test_notice_contract_has_no_tenant_or_internal_user_fields(self):
        assert set(StudentNotice.model_fields) == {
            "notice_id",
            "title",
            "content",
            "category",
            "priority",
            "is_pinned",
            "published_at",
            "expires_at",
        }

    def test_resource_contract_has_no_storage_or_tenant_fields(self):
        assert set(StudentResource.model_fields) == {
            "resource_id",
            "title",
            "description",
            "source_type",
            "effective_from",
            "effective_until",
        }

    def test_list_contracts_reject_extra_fields(self):
        with pytest.raises(Exception):
            StudentNoticeList(items=[], total=0, institution_id=TENANT_A)
        with pytest.raises(Exception):
            StudentResourceList(items=[], total=0, storage_object_key="x")

    def test_models_reject_smuggled_internal_identifiers(self):
        with pytest.raises(Exception):
            StudentNotice(
                notice_id=NOTICE_A,
                title="t",
                content="c",
                category="general",
                priority="normal",
                institution_id=TENANT_A,
            )
        with pytest.raises(Exception):
            StudentResource(
                resource_id=RESOURCE_A,
                title="t",
                source_type="handbook",
                storage_object_key="institution/handbook.pdf",
            )



# ============================================================================
# 7. API — authentication and tenant isolation over HTTP
# ============================================================================


class TestStudentDashboardEndpoints:
    def test_notices_require_authentication(self):
        response = client.get("/api/v1/students/me/notices")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_resources_require_authentication(self):
        response = client.get("/api/v1/students/me/resources")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_notices_return_only_the_authenticated_students_institution(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student(institution_id=TENANT_A)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(
                dashboard_repo,
                "list_published_notices",
                return_value=[_notice_row(institution_id=TENANT_A)],
            ):
                response = client.get("/api/v1/students/me/notices")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Exam schedule update"

    def test_resources_return_only_the_authenticated_students_institution(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student(institution_id=TENANT_A)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(
                dashboard_repo,
                "list_published_resources",
                return_value=[_resource_row(institution_id=TENANT_A)],
            ):
                response = client.get("/api/v1/students/me/resources")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Student Handbook"

    def test_client_supplied_institution_cannot_widen_the_scope(self):
        """A smuggled institution_id query value is ignored, not honoured."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student(institution_id=TENANT_A)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(
                dashboard_repo, "list_published_notices", return_value=[]
            ) as repo:
                response = client.get(
                    f"/api/v1/students/me/notices?institution_id={TENANT_B}"
                    f"&student_id={STUDENT_ID}&user_id={STUDENT_USER_ID}"
                )
        assert response.status_code == 200
        # The ONLY tenant ever queried is the authenticated student's own.
        assert repo.call_args[0][1] == TENANT_A

    def test_out_of_range_limit_is_rejected_by_the_api(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        assert client.get("/api/v1/students/me/notices?limit=1000").status_code == 422
        assert client.get("/api/v1/students/me/resources?limit=0").status_code == 422

    def test_empty_institution_returns_an_empty_list_not_an_error(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(dashboard_repo, "list_published_notices", return_value=[]):
                with patch.object(
                    dashboard_repo, "list_published_resources", return_value=[]
                ):
                    notices = client.get("/api/v1/students/me/notices")
                    resources = client.get("/api/v1/students/me/resources")
        assert notices.status_code == 200
        assert notices.json() == {"items": [], "total": 0}
        assert resources.status_code == 200
        assert resources.json() == {"items": [], "total": 0}

    def test_responses_never_leak_storage_keys_tokens_or_internal_ids(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(
                dashboard_repo, "list_published_resources", return_value=[_resource_row()]
            ):
                payload = client.get("/api/v1/students/me/resources").text
        for forbidden in (
            "storage_object_key",
            "storage_bucket",
            "file_checksum",
            "created_by_user_id",
            "institution_id",
            "student_id",
            "Bearer",
        ):
            assert forbidden not in payload

    def test_unapproved_student_gets_403_not_data(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_for_student(approval_status="pending")
        with patch("app.services.student_context.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/notices")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "STUDENT_NOT_APPROVED"



# ============================================================================
# 8. Authorization — students are read-only and cannot reach privileged routes
# ============================================================================


class TestStudentAuthorizationRemainsServerSide:
    def test_student_cannot_list_admin_notices(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.get("/api/v1/admin/notices")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"

    def test_student_cannot_create_update_or_delete_notices(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        created = client.post(
            "/api/v1/admin/notices", json={"title": "t", "content": "c"}
        )
        updated = client.patch(
            f"/api/v1/admin/notices/{NOTICE_A}", json={"title": "t2"}
        )
        deleted = client.delete(f"/api/v1/admin/notices/{NOTICE_A}")
        for response in (created, updated, deleted):
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "FORBIDDEN"

    def test_student_cannot_publish_an_admin_faq(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.post(f"/api/v1/admin/faqs/{RESOURCE_A}/publish")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"

    def test_student_cannot_ingest_or_read_documents(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        ingest = client.post("/api/v1/documents/ingest", json={})
        listing = client.get(f"/api/v1/admin/knowledge-sources/{RESOURCE_A}/documents")
        assert ingest.status_code == 403
        assert listing.status_code == 403

    def test_student_cannot_read_the_admin_dashboard(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.get("/api/v1/admin/dashboard")
        assert response.status_code == 403

    def test_there_is_no_student_mutation_route_for_notices_or_resources(self):
        """Only GET is registered on the two new student paths."""
        paths = app.openapi()["paths"]
        assert "get" in paths["/api/v1/students/me/notices"]
        assert "get" in paths["/api/v1/students/me/resources"]
        for method in ("post", "patch", "put", "delete"):
            assert method not in paths["/api/v1/students/me/notices"]
            assert method not in paths["/api/v1/students/me/resources"]


# ============================================================================
# 9. Regression — existing contracts unchanged
# ============================================================================


class TestExistingContractsUnchanged:
    def test_the_admin_notice_boundary_still_rejects_students(self):
        import asyncio

        from app.core.security import require_roles

        with pytest.raises(AppError) as exc:
            asyncio.run(require_roles("admin")(current_user=_student_user()))
        assert exc.value.status_code == 403

    def test_the_admin_notice_boundary_still_admits_admins(self):
        import asyncio

        from app.core.security import require_roles

        admin = {
            "user_id": "1",
            "auth_user_id": "2",
            "email": None,
            "roles": ["admin"],
            "institution_id": None,
        }
        assert asyncio.run(require_roles("admin")(current_user=admin)) is admin

    def test_existing_student_endpoints_still_exist(self):
        paths = app.openapi()["paths"]
        for path in (
            "/api/v1/students/me/profile",
            "/api/v1/students/me/academic-profile",
            "/api/v1/students/me/results",
            "/api/v1/students/me/results/summary",
            "/api/v1/students/me/test-results",
            "/api/v1/students/me/test-results/summary",
            "/api/v1/students/me/attendance",
            "/api/v1/students/me/attendance/summary",
            "/api/v1/students/me/notifications",
        ):
            assert path in paths

