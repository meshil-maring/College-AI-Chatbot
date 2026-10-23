"""Shared account/content fixtures and test doubles."""

import pytest

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.errors import AppError

from app.core.security import get_current_user

from app.main import app

from app.schemas.students.student_notifications import NOTIFICATION_TYPES

from app.services.students import student_notifications as notifications_service

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "a1111111-0000-0000-0000-000000000001"

TENANT_B = "b2222222-0000-0000-0000-000000000002"

STUDENT_USER_ID = "71000000-0000-0000-0000-000000000001"

STUDENT_AUTH_USER_ID = "61000000-0000-0000-0000-000000000001"

STUDENT_ID = "30000000-0000-0000-0000-000000000151"

OTHER_STUDENT_ID = "30000000-0000-0000-0000-000000000152"

NOTIFICATION_ID = "50000000-0000-0000-0000-000000000001"

SOURCE_RECORD_ID = "90000000-0000-0000-0000-000000000001"


def _student_user(
    user_id=STUDENT_USER_ID,
    tenant=TENANT_A,
    auth_user_id=STUDENT_AUTH_USER_ID,
    email="student@college.edu",
):
    return {
        "user_id": user_id,
        "auth_user_id": auth_user_id,
        "email": email,
        "roles": ["student"],
        "institution_id": tenant,
    }


def _approved_student_profile():
    return {
        "student_id": STUDENT_ID,
        "user_id": STUDENT_USER_ID,
        "institution_id": TENANT_A,
        "student_number": "STU100",
        "approval_status": "approved",
        "is_active": True,
        "email": "student@college.edu",
        "status": "active",
        "auth_user_id": STUDENT_AUTH_USER_ID,
    }


def _notification_row(
    notification_id=NOTIFICATION_ID,
    student_id=STUDENT_ID,
    institution_id=TENANT_A,
    notification_type="academic_admin",
    title="Test notification",
    message="Test message",
    is_read=False,
    source_type="academic_event",
    source_record_id=None,
    created_at="2026-09-14T10:00:00+00:00",
    read_at=None,
):
    return {
        "notification_id": notification_id,
        "student_id": student_id,
        "institution_id": institution_id,
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "is_read": is_read,
        "source_type": source_type,
        "source_record_id": source_record_id,
        "created_at": created_at,
        "read_at": read_at,
    }


def _db_with_student_profile(profile=None):
    db = MagicMock()
    if profile is None:
        profile = _approved_student_profile()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=profile
    )
    return db


def _db_without_profile():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=None
    )
    return db


def _count_response(count):
    resp = MagicMock()
    resp.count = count
    resp.data = []
    return resp


_MISSING = object()


def _db_with_notification_row(row=_MISSING):
    db = MagicMock()
    if row is _MISSING:
        row = _notification_row()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        _count_response(1)
    )
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=row
    )
    db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
        data=[row] if row is not None else []
    )
    db.table.return_value.insert.return_value.select.return_value.single.return_value.execute.return_value = MagicMock(
        data=row
    )
    if row is not None:
        db.table.return_value.update.return_value.eq.return_value.select.return_value.single.return_value.execute.return_value = MagicMock(
            data={**row, "is_read": True, "read_at": "2026-09-14T11:00:00+00:00"}
        )
    return db


def _db_with_notifications(rows=None):
    db = MagicMock()
    if rows is None:
        rows = []
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=None
    )
    db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
        data=rows
    )
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        _count_response(len(rows))
    )
    return db


@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _fake_repo_create(client, payload):
    """Return a notification row that mirrors what the service intended to
    insert — used to exercise the real integration + service orchestration
    without touching a live database."""
    row = dict(_notification_row())
    data = payload.model_dump(mode="json")
    for key, value in data.items():
        if value is not None:
            row[key] = value
    return row
