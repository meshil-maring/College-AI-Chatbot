"""Phase 6.11 — Student notification service.

Business logic and tenant-safe orchestration over student notifications.

Authorization is enforced by the API layer (authentication, student context,
tenant isolation — locked Phase 6.9). This service validates ownership and
derives every security-relevant value server-side — never from the client.
"""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import student_notifications as notifications_repo
from app.schemas.student_notifications import (
    NOTIFICATION_TYPES,
    Notification,
    NotificationCreate,
    NotificationCreateResult,
    NotificationListResponse,
)


def create_notification_for_student(
    student_id: UUID | str,
    institution_id: UUID | str,
    notification_type: str,
    title: str,
    message: str,
    source_type: str = "academic_event",
    source_record_id: UUID | None = None,
    client: Any = None,
) -> NotificationCreateResult:
    """Create one notification for a student from an authoritative event.

    Called by authorized backend workflows (attendance, results, admin).
    The caller MUST supply the correct student_id and institution_id
    derived from the authoritative academic context.

    Duplicate protection: if a notification for the same (student_id,
    source_record_id, notification_type) already exists, the UNIQUE
    constraint raises a conflict that maps to NOTIFICATION_DUPLICATE (409).
    """
    db = client or get_admin_client()
    _validate_notification_type(notification_type)

    payload = NotificationCreate(
        student_id=UUID(student_id),
        institution_id=UUID(institution_id),
        notification_type=notification_type,
        title=title,
        message=message,
        source_type=source_type,
        source_record_id=source_record_id,
    )

    try:
        return notifications_repo.create_notification(db, payload)
    except Exception as exc:
        return _map_creation_error(exc)


def _validate_notification_type(notification_type: str) -> None:
    if notification_type not in NOTIFICATION_TYPES:
        raise AppError(
            f"Invalid notification type: {notification_type}",
            status_code=422,
            code="INVALID_NOTIFICATION_TYPE",
        )


def _map_creation_error(exc: Exception) -> AppError:
    message = str(exc).lower()
    if "23505" in message or "duplicate" in message:
        return AppError(
            "A notification for this event already exists",
            status_code=409,
            code="NOTIFICATION_DUPLICATE",
        )
    return AppError(
        "Notification creation failed",
        status_code=409,
        code="NOTIFICATION_CREATE_FAILED",
    )


def get_own_notifications(
    student_id: UUID | str,
    page: int = 1,
    page_size: int = 20,
    client: Any = None,
) -> NotificationListResponse:
    """Return a paginated list of the authenticated student's own notifications.

    Ordering is deterministic: newest first by created_at DESC.
    """
    if page < 1:
        raise AppError("Page must be >= 1", status_code=422, code="INVALID_PAGE")
    if page_size < 1 or page_size > 100:
        raise AppError(
            "Page size must be between 1 and 100",
            status_code=422,
            code="INVALID_PAGE_SIZE",
        )

    db = client or get_admin_client()
    offset = (page - 1) * page_size
    rows = notifications_repo.list_notifications(
        db, student_id, limit=page_size, offset=offset
    )
    total = notifications_repo.count_notifications_by_student(db, student_id)

    items = [Notification(**row) for row in rows]
    has_more = offset + len(rows) < total

    return NotificationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


def get_own_notification(
    current_student_id: UUID | str,
    notification_id: UUID | str,
    client: Any = None,
) -> Notification:
    """Return one notification belonging to the authenticated student.

    Raises 404 NOTIFICATION_NOT_FOUND when the notification does not exist
    OR belongs to another student (same error to prevent enumeration).
    """
    db = client or get_admin_client()

    row = notifications_repo.get_notification(db, notification_id)
    if row is None:
        raise AppError(
            "Notification not found", status_code=404, code="NOTIFICATION_NOT_FOUND"
        )
    if str(row.get("student_id")) != str(current_student_id):
        raise AppError(
            "Notification not found", status_code=404, code="NOTIFICATION_NOT_FOUND"
        )

    return Notification(**row)


def mark_own_notification_read(
    current_student_id: UUID | str,
    notification_id: UUID | str,
    client: Any = None,
) -> Notification:
    """Mark the authenticated student's own notification as read.

    Raises 404 NOTIFICATION_NOT_FOUND when the notification does not exist
    OR belongs to another student.
    """
    db = client or get_admin_client()

    if not notifications_repo.notification_belongs_to_student(
        db, notification_id, current_student_id
    ):
        raise AppError(
            "Notification not found", status_code=404, code="NOTIFICATION_NOT_FOUND"
        )

    updated = notifications_repo.mark_notification_read(db, notification_id)
    if updated is None:
        raise AppError(
            "Notification not found", status_code=404, code="NOTIFICATION_NOT_FOUND"
        )

    return Notification(**updated)


def get_unread_count(student_id: UUID | str, client: Any = None) -> int:
    """Return the unread notification count for one student."""
    db = client or get_admin_client()
    return notifications_repo.count_unread_by_student(db, student_id)