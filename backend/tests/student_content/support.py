"""Shared account/content fixtures and test doubles."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from .fakes import _FakeClient, _FakeQueryBuilder

from fastapi.testclient import TestClient

from app.core.errors import AppError

from app.core.security import get_current_user

from app.main import app

from app.repositories.students import student_content as dashboard_repo

from app.schemas.students.student_notices import StudentNotice, StudentNoticeList

from app.schemas.students.student_resources import StudentResource, StudentResourceList

from app.services.students import student_notices as notices_service

from app.services.students import student_resources as resources_service

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


def _student_user(user_id=STUDENT_USER_ID, tenant=TENANT_A):
    return {
        "user_id": user_id,
        "auth_user_id": STUDENT_AUTH_USER_ID,
        "email": "student@college.edu",
        "roles": ["student"],
        "status": "active",
        "institution_id": tenant,
    }


def _student_profile(
    institution_id=TENANT_A, approval_status="approved", is_active=True
):
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


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)
