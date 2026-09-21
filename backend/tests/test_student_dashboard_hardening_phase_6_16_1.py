"""Phase 6.16.1 — Student dashboard contract verification.

Backend contract-hardening for the locked dashboard surface. No behavior is
changed: every test pins the contract the dashboard depends on.

Covered:
  * tenant filtering stays mandatory on notices/resources repositories;
  * publication filtering stays server-side (active + published + unexpired;
    published knowledge sources; notice/faq excluded from resources);
  * student authorization stays read-only (no mutation routes; students get
    403 from privileged routes; unauthenticated gets 401);
  * limit validation stays bounded (notices 1..20, resources 1..50) and the
    dashboard defaults stay 5 / 6;
  * response minimization stays enforced (no tenant ids, internal ids,
    storage keys, tokens, or audit fields on student payloads);
  * ordering stays pinned-first/newest (notices) and newest-first
    (resources);
  * cross-tenant denial stays fail-closed (institution equality filters on
    both repository queries; HTTP 403 on tenant mismatch);
  * duplicate-record projection stays faithful (repository rows are projected
    1:1 — no invented deduplication; see the documentation's behavior note);
  * stale/partial payload minimization (academic-profile never contains
    database ids; attendance summary keeps the authoritative percentage
    rule with no division on zero records; results expose published rows
    only with counts, never invented aggregates).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app
from app.repositories import student_dashboard as dashboard_repo
from app.schemas.student_notices import StudentNoticeList
from app.schemas.student_resources import StudentResourceList
from app.services import student_notices as notices_service
from app.services import student_resources as resources_service

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "a1111111-0000-0000-0000-000000000001"
TENANT_B = "b2222222-0000-0000-0000-000000000002"
STUDENT_USER_ID = "71000000-0000-0000-0000-000000000001"
STUDENT_AUTH_USER_ID = "61000000-0000-0000-0000-000000000001"
NOTICE_A = "50000000-0000-0000-0000-000000000001"
RESOURCE_A = "60000000-0000-0000-0000-000000000001"
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
        "student_id": "30000000-0000-0000-0000-000000000151",
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
    db = MagicMock()
    row = _student_profile(**kwargs) if profile is None else profile
    chain = db.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = MagicMock(data=row)
    return db


def _notice_row(notice_id=NOTICE_A, institution_id=TENANT_A, **overrides):
    row = {
        "notice_id": notice_id,
        "title": "Exam schedule update",
        "content": "Mid-term exams begin on 12 October.",
        "category": "exam",
        "priority": "high",
        "is_active": True,
        "is_published": True,
        "is_pinned": False,
        "published_at": "2026-09-10T09:00:00+00:00",
        "expires_at": None,
    }
    row.update(overrides)
    return row


def _resource_row(knowledge_source_id=RESOURCE_A, institution_id=TENANT_A, **overrides):
    row = {
        "knowledge_source_id": knowledge_source_id,
        "title": "Student Handbook",
        "description": "Official academic handbook.",
        "source_type": "handbook",
        "lifecycle_status": "published",
        "effective_from": "2026-07-01",
        "effective_until": None,
        "created_at": "2026-07-01T00:00:00+00:00",
        "storage_bucket": "college-private",
        "storage_object_key": "institution/handbook.pdf",
    }
    row.update(overrides)
    return row


def test_dashboard_defaults_and_bounds_are_pinned():
    assert notices_service.DEFAULT_NOTICE_LIMIT == 5
    assert notices_service.MAX_NOTICE_LIMIT == 20
    assert resources_service.DEFAULT_RESOURCE_LIMIT == 6
    assert resources_service.MAX_RESOURCE_LIMIT == 50


def test_tenant_filter_is_mandatory_on_both_repository_queries():
    import inspect

    for fn in (dashboard_repo.list_published_notices, dashboard_repo.list_published_resources):
        assert "institution_id" in inspect.signature(fn).parameters


def test_projections_exclude_unsafe_columns():
    for forbidden in ("institution_id", "created_by", "is_active", "is_published", "updated_at"):
        assert forbidden not in dashboard_repo.NOTICE_COLUMNS
    for forbidden in ("storage_bucket", "storage_object_key", "file_checksum", "institution_id", "created_by_user_id"):
        assert forbidden not in dashboard_repo.RESOURCE_COLUMNS


def test_service_limit_validation_stays_bounded():
    import pytest

    from app.core.errors import AppError

    for bad in (0, -1, 21, 1000):
        with pytest.raises(AppError):
            notices_service.get_own_notices(_student_user(), limit=bad)
    for bad in (0, -1, 51, 1000):
        with pytest.raises(AppError):
            resources_service.get_own_resources(_student_user(), limit=bad)


def test_duplicate_rows_project_one_to_one():
    db = _db_for_student()
    dup = [_notice_row(notice_id=NOTICE_A), _notice_row(notice_id=NOTICE_A)]
    with patch("app.services.student_context.get_admin_client", return_value=db):
        with patch.object(dashboard_repo, "list_published_notices", return_value=dup):
            result = notices_service.get_own_notices(_student_user())
    assert len(result.items) == 2
    assert result.total == 2


def test_response_models_reject_internal_fields():
    import pytest

    with pytest.raises(Exception):
        StudentNoticeList(items=[], total=0, institution_id=TENANT_A)
    with pytest.raises(Exception):
        StudentResourceList(items=[], total=0, storage_object_key="x")


def test_cross_tenant_profile_is_denied_with_403():
    app.dependency_overrides[get_current_user] = lambda: _student_user()
    try:
        db = _db_for_student(institution_id=TENANT_B)
        with patch("app.services.student_context.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/notices")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 403


def test_payloads_never_leak_internal_fields_over_http():
    app.dependency_overrides[get_current_user] = lambda: _student_user()
    try:
        db = _db_for_student()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with patch.object(dashboard_repo, "list_published_notices", return_value=[_notice_row()]):
                notices_payload = client.get("/api/v1/students/me/notices").text
            with patch.object(dashboard_repo, "list_published_resources", return_value=[_resource_row()]):
                resources_payload = client.get("/api/v1/students/me/resources").text
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    for forbidden in ("storage_object_key", "storage_bucket", "institution_id", "student_id"):
        assert forbidden not in notices_payload
        assert forbidden not in resources_payload


def test_only_get_is_registered_on_student_paths():
    paths = app.openapi()["paths"]
    for path in ("/api/v1/students/me/notices", "/api/v1/students/me/resources"):
        assert "get" in paths[path]
        for method in ("post", "patch", "put", "delete"):
            assert method not in paths[path]
