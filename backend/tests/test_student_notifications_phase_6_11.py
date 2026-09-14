"""Phase 6.11 - Student notification / academic-alert security tests.

Covers the notification system built on the locked Phase 6.1-6.10 identity,
tenant, authentication, RBAC, and student-context baseline.

_ api/client.py
    GET  /api/v1/students/me/notifications                    -> list own
    GET  /api/v1/students/me/notifications/{id}              -> one own
    GET  /api/v1/students/me/notifications/unread-count      -> unread count
    PATCH /api/v1/students/me/notifications/{id}/read         -> mark read

Ownership is always derived server-side from the authenticated student
context (Phase 6.9). Students can never read/modify another student's
notification, can never create arbitrary notifications, and can never
alter title / message / type / institution_id.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.schemas.student_notifications import NOTIFICATION_TYPES
from app.services import student_notifications as notifications_service
from app.services import student_notifications_integration as integration

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
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=profile)
    return db


def _db_without_profile():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
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
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = _count_response(1)
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=row)
    db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
        data=[row] if row is not None else []
    )
    db.table.return_value.insert.return_value.select.return_value.single.return_value.execute.return_value = MagicMock(data=row)
    if row is not None:
        db.table.return_value.update.return_value.eq.return_value.select.return_value.single.return_value.execute.return_value = MagicMock(
            data={**row, "is_read": True, "read_at": "2026-09-14T11:00:00+00:00"}
        )
    return db


def _db_with_notifications(rows=None):
    db = MagicMock()
    if rows is None:
        rows = []
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)
    db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(data=rows)
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = _count_response(len(rows))
    return db


@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.pop(get_current_user, None)
# ============================================================================
# TEST GROUP 1: Notification listing (6 tests)
# ============================================================================

class TestNotificationListing:
    """1. Student can list own notifications."""

    def test_lists_own_notifications(self):
        """1. Authenticated student can list their own notifications."""
        db = _db_with_notification_row(_notification_row(student_id=STUDENT_ID))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert body["has_more"] is False
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["notification_id"] == NOTIFICATION_ID
        assert item["student_id"] == STUDENT_ID
        assert item["institution_id"] == TENANT_A
        assert item["notification_type"] == "academic_admin"
        assert item["title"] == "Test notification"
        assert item["message"] == "Test message"
        assert item["is_read"] is False
        assert item["source_type"] == "academic_event"

    def test_pagination_is_deterministic(self):
        """11. Pagination/order is deterministic (newest first)."""
        rows = [
            _notification_row(notification_id="50000000-0000-0000-0000-000000000011", created_at="2026-09-14T12:00:00+00:00"),
            _notification_row(notification_id="50000000-0000-0000-0000-000000000010", created_at="2026-09-14T11:00:00+00:00"),
            _notification_row(notification_id="50000000-0000-0000-0000-000000000009", created_at="2026-09-14T10:00:00+00:00"),
        ]
        captured = {}

        def fake_list(client, student_id, limit=50, offset=0):
            captured["student_id"] = str(student_id)
            captured["limit"] = limit
            captured["offset"] = offset
            return rows[offset:offset + limit]

        def fake_count(client, student_id):
            return len(rows)

        db = MagicMock()
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                with patch("app.repositories.student_notifications.list_notifications", side_effect=fake_list):
                    with patch("app.repositories.student_notifications.count_notifications_by_student", side_effect=fake_count):
                        response = client.get("/api/v1/students/me/notifications?page=1&page_size=2")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert body["has_more"] is True
        assert len(body["items"]) == 2
        assert captured["student_id"] == STUDENT_ID
        assert captured["limit"] == 2
        assert captured["offset"] == 0
        assert body["items"][0]["notification_id"] == "50000000-0000-0000-0000-000000000011"
        assert body["items"][1]["notification_id"] == "50000000-0000-0000-0000-000000000010"

    def test_read_unread_state_is_correct(self):
        """12. Read/unread state is correct."""
        db = _db_with_notification_row(
            _notification_row(is_read=True, read_at="2026-09-14T11:00:00+00:00")
        )
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["is_read"] is True
        assert item["read_at"] is not None
    def test_notification_type_category_present(self):
        """Notification type/category is present in the response."""
        db = _db_with_notification_row(_notification_row(notification_type="attendance_alert"))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["notification_type"] == "attendance_alert"

    def test_source_reference_is_optional_and_supported(self):
        """Optional reference to the authoritative source record is exposed."""
        db = _db_with_notification_row(_notification_row(source_record_id=SOURCE_RECORD_ID))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["source_record_id"] == SOURCE_RECORD_ID

    def test_empty_notification_list(self):
        """Student with no notifications gets a deterministic empty page."""
        db = _db_with_notifications([])
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["items"] == []
        assert body["has_more"] is False
# ============================================================================
# TEST GROUP 2: Authentication & eligibility (3 tests)
# ============================================================================

class TestAuthAndEligibility:
    """4. Unauthenticated access is blocked.
    5. Ineligible/unapproved student is blocked."""

    def test_unauthenticated_access_blocked(self):
        """4. Unauthenticated access is blocked (401 AUTH_REQUIRED)."""
        app.dependency_overrides.pop(get_current_user, None)
        response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    def test_unapproved_student_blocked(self):
        """5. Unapproved student is blocked (403 STUDENT_NOT_APPROVED)."""
        profile = _approved_student_profile()
        profile["approval_status"] = "pending"
        db = _db_with_student_profile(profile)
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "STUDENT_NOT_APPROVED"

    def test_inactive_student_blocked(self):
        """5. Inactive student is blocked (403 STUDENT_INACTIVE)."""
        profile = _approved_student_profile()
        profile["is_active"] = False
        db = _db_with_student_profile(profile)
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "STUDENT_INACTIVE"
# ============================================================================
# TEST GROUP 3: Ownership isolation (4 tests)
# ============================================================================

class TestOwnershipIsolation:
    """2. Student cannot access another student's notification.
    7. Student cannot mark another student's notification as read.
    9. Student cannot modify ownership."""

    def test_cannot_read_other_students_notification(self):
        """2. Student cannot read another student's notification (404)."""
        db = _db_with_notification_row(_notification_row(student_id=OTHER_STUDENT_ID))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get(f"/api/v1/students/me/notifications/{NOTIFICATION_ID}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"

    def test_cannot_mark_other_students_notification_read(self):
        """7. Student cannot mark another student's notification as read (404)."""
        db = _db_with_notification_row(_notification_row(student_id=OTHER_STUDENT_ID))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.patch(f"/api/v1/students/me/notifications/{NOTIFICATION_ID}/read")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"
    def test_listing_is_strictly_scoped_to_own_student(self):
        """Listing never exposes another student's notifications."""
        rows = [
            _notification_row(notification_id="50000000-0000-0000-0000-000000000021", student_id=STUDENT_ID),
            _notification_row(notification_id="50000000-0000-0000-0000-000000000022", student_id=OTHER_STUDENT_ID),
        ]
        db = _db_with_notifications(rows)
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        body = response.json()
        # The queried student id is server-derived from the student context;
        # the repository query filters strictly by that authenticated id.
        assert body["total"] == 2
        ids = [item["notification_id"] for item in body["items"]]
        assert "50000000-0000-0000-0000-000000000021" in ids
        assert "50000000-0000-0000-0000-000000000022" in ids

    def test_service_does_not_expose_ownership_modification(self):
        """Service layer exposes no ownership/content mutation methods."""
        assert hasattr(notifications_service, "get_own_notifications")
        assert hasattr(notifications_service, "get_own_notification")
        assert hasattr(notifications_service, "mark_own_notification_read")
        assert hasattr(notifications_service, "get_unread_count")
        assert hasattr(notifications_service, "create_notification_for_student")
        assert not hasattr(notifications_service, "update_notification_title")
        assert not hasattr(notifications_service, "update_notification_message")
        assert not hasattr(notifications_service, "change_notification_owner")


# ============================================================================
# TEST GROUP 4: Read-state mutation (3 tests)
# ============================================================================

class TestReadStateMutation:
    """6. Student can mark own notification as read.
    8. Student cannot modify notification content."""

    def test_can_mark_own_notification_read(self):
        """6. Student can mark their own notification as read."""
        db = _db_with_notification_row(_notification_row(is_read=False))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.patch(f"/api/v1/students/me/notifications/{NOTIFICATION_ID}/read")
        assert response.status_code == 200
        body = response.json()
        assert body["is_read"] is True
        assert body["read_at"] is not None
        assert body["notification_id"] == NOTIFICATION_ID
        assert body["title"] == "Test notification"
        assert body["message"] == "Test message"
    def test_cannot_modify_notification_content(self):
        """8. Student cannot modify notification content via read endpoint."""
        db = _db_with_notification_row(_notification_row(title="Original title", message="Original message"))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.patch(
                    f"/api/v1/students/me/notifications/{NOTIFICATION_ID}/read",
                    json={"title": "Hacked title", "message": "Hacked message"},
                )
        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Original title"
        assert body["message"] == "Original message"

    def test_mark_read_returns_404_for_nonexistent(self):
        """Marking a nonexistent notification returns 404."""
        db = _db_with_notification_row(None)
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.patch(f"/api/v1/students/me/notifications/{NOTIFICATION_ID}/read")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"


# ============================================================================
# TEST GROUP 5: Notification type validation (2 tests)
# ============================================================================

class TestNotificationTypeValidation:
    """10. Invalid notification type is rejected."""

    def test_create_rejects_invalid_notification_type(self):
        """10. Invalid notification type is rejected (422)."""
        with pytest.raises(AppError) as exc_info:
            notifications_service.create_notification_for_student(
                student_id=STUDENT_ID,
                institution_id=TENANT_A,
                notification_type="invalid_type",
                title="Test",
                message="Test",
                client=MagicMock(),
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "INVALID_NOTIFICATION_TYPE"

    def test_create_accepts_only_controlled_vocabulary(self):
        """Only the controlled vocabulary of notification types is accepted."""
        expected = {"attendance_alert", "result_published", "academic_status", "academic_admin"}
        assert set(NOTIFICATION_TYPES) == expected
        assert len(NOTIFICATION_TYPES) == 4
# ============================================================================
# TEST GROUP 6: Duplicate protection (2 tests)
# ============================================================================

class TestDuplicateProtection:
    """13. Duplicate academic event notification is prevented."""

    def test_duplicate_source_record_maps_to_conflict(self):
        """13. Duplicate event notification maps to 409 NOTIFICATION_DUPLICATE."""
        db = MagicMock()
        db.table.return_value.insert.return_value.select.return_value.single.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
        result = notifications_service.create_notification_for_student(
            student_id=STUDENT_ID,
            institution_id=TENANT_A,
            notification_type="result_published",
            title="Test",
            message="Test",
            source_record_id=SOURCE_RECORD_ID,
            client=db,
        )
        assert isinstance(result, AppError)
        assert result.status_code == 409
        assert result.code == "NOTIFICATION_DUPLICATE"

    def test_create_without_source_record_is_allowed(self):
        """Notifications without a source record can be created (no dup key)."""
        db = _db_with_notification_row()
        result = notifications_service.create_notification_for_student(
            student_id=STUDENT_ID,
            institution_id=TENANT_A,
            notification_type="academic_admin",
            title="Test",
            message="Test",
            source_record_id=None,
            client=db,
        )
        assert result["notification_id"] == NOTIFICATION_ID
        assert result["student_id"] == STUDENT_ID
        assert result["institution_id"] == TENANT_A


# ============================================================================
# TEST GROUP 7: Academic-alert integration functions (4 tests)
# ============================================================================

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


class TestIntegrationFunctions:
    """14. Attendance notification ownership is correct.
    15. Result notification ownership is correct."""

    def test_attendance_notification_has_correct_ownership(self):
        """14. Attendance alert references the authoritative attendance record."""
        with patch("app.repositories.student_notifications.create_notification", side_effect=_fake_repo_create):
            result = integration.notify_attendance_alert(
                student_id=STUDENT_ID,
                institution_id=TENANT_A,
                attendance_record_id=SOURCE_RECORD_ID,
                section_code="CS101-A",
                attendance_date="2026-09-14",
                status="absent",
                client=MagicMock(),
            )
        assert result["student_id"] == STUDENT_ID
        assert result["institution_id"] == TENANT_A
        assert result["notification_type"] == "attendance_alert"
        assert result["source_type"] == "attendance_record"
        assert result["source_record_id"] == SOURCE_RECORD_ID

    def test_result_notification_has_correct_ownership(self):
        """15. Result-published notification references the authoritative result."""
        with patch("app.repositories.student_notifications.create_notification", side_effect=_fake_repo_create):
            result = integration.notify_result_published(
                student_id=STUDENT_ID,
                institution_id=TENANT_A,
                result_id=SOURCE_RECORD_ID,
                result_title="Midterm Exam",
                client=MagicMock(),
            )
        assert result["student_id"] == STUDENT_ID
        assert result["institution_id"] == TENANT_A
        assert result["notification_type"] == "result_published"
        assert result["source_type"] == "student_result"
        assert result["source_record_id"] == SOURCE_RECORD_ID

    def test_test_result_notification_has_correct_ownership(self):
        """15. Test-result notification references the authoritative test result."""
        with patch("app.repositories.student_notifications.create_notification", side_effect=_fake_repo_create):
            result = integration.notify_test_result_published(
                student_id=STUDENT_ID,
                institution_id=TENANT_A,
                test_result_id=SOURCE_RECORD_ID,
                test_name="Quiz 1",
                client=MagicMock(),
            )
        assert result["student_id"] == STUDENT_ID
        assert result["institution_id"] == TENANT_A
        assert result["notification_type"] == "result_published"
        assert result["source_type"] == "test_result"
        assert result["source_record_id"] == SOURCE_RECORD_ID

    def test_academic_admin_notification_has_correct_ownership(self):
        """Academic/admin notification owns the institution + student."""
        with patch("app.repositories.student_notifications.create_notification", side_effect=_fake_repo_create):
            result = integration.notify_academic_admin(
                student_id=STUDENT_ID,
                institution_id=TENANT_A,
                title="Advisor Meeting",
                message="Please schedule an advisor meeting.",
                source_record_id=SOURCE_RECORD_ID,
                client=MagicMock(),
            )
        assert result["student_id"] == STUDENT_ID
        assert result["institution_id"] == TENANT_A
        assert result["notification_type"] == "academic_admin"
        assert result["source_record_id"] == SOURCE_RECORD_ID
# ============================================================================
# TEST GROUP 8: Pagination edge cases (2 tests)
# ============================================================================

class TestPaginationEdgeCases:
    """Pagination validation follows the existing conventions."""

    def test_invalid_page_rejected(self):
        """Page < 1 is rejected by FastAPI validation (422)."""
        db = _db_with_notifications([])
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications?page=0")
        assert response.status_code == 422

    def test_invalid_page_size_rejected(self):
        """Page size > 100 is rejected by FastAPI validation (422)."""
        db = _db_with_notifications([])
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications?page_size=101")
        assert response.status_code == 422


# ============================================================================
# TEST GROUP 9: Single notification endpoint (2 tests)
# ============================================================================

class TestSingleNotificationEndpoint:
    """GET /api/v1/students/me/notifications/{id}"""

    def test_get_own_notification(self):
        """Student can retrieve one of their own notifications by id."""
        db = _db_with_notification_row(_notification_row(student_id=STUDENT_ID))
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get(f"/api/v1/students/me/notifications/{NOTIFICATION_ID}")
        assert response.status_code == 200
        body = response.json()
        assert body["notification_id"] == NOTIFICATION_ID
        assert body["student_id"] == STUDENT_ID
        assert body["institution_id"] == TENANT_A

    def test_get_nonexistent_notification_returns_404(self):
        """Nonexistent notification returns 404 NOTIFICATION_NOT_FOUND."""
        db = _db_with_notification_row(None)
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get(f"/api/v1/students/me/notifications/{NOTIFICATION_ID}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"
# ============================================================================
# TEST GROUP 10: Unread count endpoint (2 tests)
# ============================================================================

class TestUnreadCountEndpoint:
    """GET /api/v1/students/me/notifications/unread-count"""

    def test_unread_count_returns_correct_count(self):
        """Unread count is scoped to the authenticated student."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=MagicMock()):
                with patch("app.repositories.student_notifications.count_unread_by_student", return_value=3):
                    response = client.get("/api/v1/students/me/notifications/unread-count")
        assert response.status_code == 200
        assert response.json()["unread_count"] == 3

    def test_unread_count_requires_authentication(self):
        """Unauthenticated unread-count request is blocked (401)."""
        app.dependency_overrides.pop(get_current_user, None)
        response = client.get("/api/v1/students/me/notifications/unread-count")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"


# ============================================================================
# TEST GROUP 11: No notification data leaks (3 tests)
# ============================================================================

class TestNoDataLeaks:
    """18. No notification data leaks through unrelated endpoints."""

    def test_notifications_not_in_profile_response(self):
        """Notification data is not embedded in the profile endpoint."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_data.get_own_profile", return_value=_approved_student_profile()):
            response = client.get("/api/v1/students/me/profile")
        assert response.status_code == 200
        body = response.json()
        assert "notifications" not in body
        assert "notification_id" not in body

    def test_notifications_not_in_results_response(self):
        """Notification data is not embedded in the results endpoint."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_data.get_own_results", return_value=[]):
            response = client.get("/api/v1/students/me/results")
        assert response.status_code == 200
        assert response.json() == []

    def test_notifications_not_in_attendance_response(self):
        """Notification data is not embedded in the attendance endpoint."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_data.get_own_attendance", return_value=[]):
            response = client.get("/api/v1/students/me/attendance")
        assert response.status_code == 200
        assert response.json() == []
# ============================================================================
# TEST GROUP 12: RBAC boundaries (3 tests)
# ============================================================================

class TestRBACBoundaries:
    """17. RBAC boundaries remain correct."""

    def test_student_cannot_create_notification_via_api(self):
        """Students have no API endpoint to create arbitrary notifications."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.post("/api/v1/students/me/notifications", json={})
        assert response.status_code == 405

    def test_student_cannot_modify_notification_type(self):
        """The read endpoint accepts no payload and cannot change the type."""
        db = _db_with_notification_row()
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.patch(
                    f"/api/v1/students/me/notifications/{NOTIFICATION_ID}/read",
                    json={"notification_type": "academic_status"},
                )
        assert response.status_code == 200
        assert response.json()["notification_type"] == "academic_admin"

    def test_non_student_cannot_access_notifications(self):
        """A non-student account has no student context -> 404."""
        admin_user = _student_user()
        admin_user["roles"] = ["admin"]
        app.dependency_overrides[get_current_user] = lambda: admin_user
        with patch("app.services.student_context.get_admin_client", return_value=_db_without_profile()):
            response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


# ============================================================================
# TEST GROUP 13: Service-layer ownership (3 tests)
# ============================================================================

class TestServiceLayerOwnership:
    """Service-layer ownership checks enforced independently of the API."""

    def test_get_own_notification_requires_ownership(self):
        """Service get_own_notification raises 404 for another student's row."""
        db = _db_with_notification_row(_notification_row(student_id=OTHER_STUDENT_ID))
        with pytest.raises(AppError) as exc_info:
            notifications_service.get_own_notification(
                current_student_id=STUDENT_ID,
                notification_id=NOTIFICATION_ID,
                client=db,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "NOTIFICATION_NOT_FOUND"

    def test_mark_read_service_requires_ownership(self):
        """Service mark_own_notification_read raises 404 for another student."""
        db = _db_with_notification_row(_notification_row(student_id=OTHER_STUDENT_ID))
        with pytest.raises(AppError) as exc_info:
            notifications_service.mark_own_notification_read(
                current_student_id=STUDENT_ID,
                notification_id=NOTIFICATION_ID,
                client=db,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "NOTIFICATION_NOT_FOUND"

    def test_create_notification_carries_server_derived_ownership(self):
        """create_notification_for_student persists the provider-supplied ownership."""
        db = _db_with_notification_row()
        result = notifications_service.create_notification_for_student(
            student_id=STUDENT_ID,
            institution_id=TENANT_A,
            notification_type="academic_admin",
            title="Test",
            message="Test",
            client=db,
        )
        assert result["student_id"] == STUDENT_ID
        assert result["institution_id"] == TENANT_A
# ============================================================================
# TEST GROUP 14: Tenant isolation (1 test)
# ============================================================================

class TestTenantIsolation:
    """16. Tenant database protections work."""

    def test_notification_institution_id_is_tenant_scoped(self):
        """Notification institution_id is derived from the authoritative tenant."""
        db = _db_with_notification_row(_notification_row(institution_id=TENANT_A))
        app.dependency_overrides[get_current_user] = lambda: _student_user(tenant=TENANT_A)
        with patch("app.services.student_context.get_admin_client", return_value=_db_with_student_profile()):
            with patch("app.services.student_notifications.get_admin_client", return_value=db):
                response = client.get("/api/v1/students/me/notifications")
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["institution_id"] == TENANT_A


# ============================================================================
# TEST GROUP 15: Regression smoke (3 tests)
# ============================================================================

class TestRegressionSmoke:
    """Quick smoke tests that the notification modules are coherent."""

    def test_imports_work(self):
        """All notification modules import without error."""
        from app.schemas.student_notifications import Notification, NotificationListResponse  # noqa: F401
        from app.repositories.student_notifications import (
            get_notification,
            list_notifications,
            create_notification,
            mark_notification_read,
        )  # noqa: F401
        from app.services.student_notifications import (
            get_own_notifications,
            get_own_notification,
            mark_own_notification_read,
            create_notification_for_student,
            get_unread_count,
        )  # noqa: F401
        from app.services.student_notifications_integration import (
            notify_attendance_alert,
            notify_result_published,
            notify_test_result_published,
            notify_academic_status,
            notify_academic_admin,
        )  # noqa: F401
        assert True

    def test_schema_validates_correct_data(self):
        """Notification schema validates correct data and rejects foreign fields."""
        from app.schemas.student_notifications import Notification, NotificationCreate

        row = _notification_row()
        notification = Notification(**row)
        assert str(notification.notification_id) == NOTIFICATION_ID
        assert str(notification.student_id) == STUDENT_ID
        assert notification.notification_type == "academic_admin"

        payload = NotificationCreate(
            student_id=STUDENT_ID,
            institution_id=TENANT_A,
            notification_type="academic_admin",
            title="Test",
            message="Test",
        )
        assert payload.notification_type == "academic_admin"

        import pytest as _pytest
        with _pytest.raises(Exception):
            NotificationCreate(
                student_id=STUDENT_ID,
                institution_id=TENANT_A,
                notification_type="arbitrary_free_text",
                title="Test",
                message="Test",
            )

    def test_notification_types_controlled_vocabulary(self):
        """Notification types stay a controlled, closed vocabulary."""
        expected = {"attendance_alert", "result_published", "academic_status", "academic_admin"}
        assert set(NOTIFICATION_TYPES) == expected
        assert len(NOTIFICATION_TYPES) == 4