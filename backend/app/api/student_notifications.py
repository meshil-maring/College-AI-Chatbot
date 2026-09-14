"""Phase 6.11 — Student notification API.

Student self-service notification endpoints.

All endpoints authenticate with the existing get_current_user dependency.
The student identity is resolved server-side from the authenticated JWT;
the client can never supply another student's id or institution_id.

Endpoints:
    GET  /api/v1/students/me/notifications            — list own notifications
    GET  /api/v1/students/me/notifications/unread-count — unread count
    GET  /api/v1/students/me/notifications/{id}      — one own notification
    PATCH /api/v1/students/me/notifications/{id}/read — mark own notification read

No endpoint allows a student to create arbitrary notifications.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from app.core.security import get_current_user
from app.schemas.student_notifications import Notification, NotificationListResponse
from app.services import student_context as student_context_service
from app.services import student_notifications as notifications_service

router = APIRouter(prefix="/students", tags=["students"])

# Default page size for notification listing.
_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Notification listing
# ---------------------------------------------------------------------------


@router.get("/me/notifications", response_model=NotificationListResponse)
def list_my_notifications(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        _DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE, description="Items per page"
    ),
    current_user: dict = Depends(get_current_user),
) -> NotificationListResponse:
    """Return a paginated list of the authenticated student's own notifications.

    Notifications are ordered newest-first by created_at.
    Each notification is scoped to the authenticated student only.
    """
    student_ctx = student_context_service.get_student_context(current_user)
    return notifications_service.get_own_notifications(
        student_ctx["student_id"],
        page=page,
        page_size=page_size,
    )


@router.get("/me/notifications/unread-count")
def unread_notification_count(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return the unread notification count for the authenticated student."""
    student_ctx = student_context_service.get_student_context(current_user)
    count = notifications_service.get_unread_count(student_ctx["student_id"])
    return {"unread_count": count}


# ---------------------------------------------------------------------------
# Single notification read
# ---------------------------------------------------------------------------


@router.get(
    "/me/notifications/{notification_id}",
    response_model=Notification,
)
def get_my_notification(
    notification_id: UUID = Path(..., description="Notification ID"),
    current_user: dict = Depends(get_current_user),
) -> Notification:
    """Return one notification belonging to the authenticated student.

    Returns 404 when the notification does not exist OR belongs to another
    student (same error to prevent enumeration).
    """
    student_ctx = student_context_service.get_student_context(current_user)
    return notifications_service.get_own_notification(
        student_ctx["student_id"],
        notification_id,
    )


# ---------------------------------------------------------------------------
# Read-state mutation
# ---------------------------------------------------------------------------


@router.patch(
    "/me/notifications/{notification_id}/read",
    response_model=Notification,
)
def mark_my_notification_read(
    notification_id: UUID = Path(..., description="Notification ID"),
    _body: dict = Depends(lambda: {}),  # No body accepted — read-state is implicit
    current_user: dict = Depends(get_current_user),
) -> Notification:
    """Mark the authenticated student's own notification as read.

    The student can only mark their OWN notifications as read.
    Returns 404 when the notification does not exist OR belongs to another
    student.

    No other fields (title, message, type, ownership) can be modified.
    """
    student_ctx = student_context_service.get_student_context(current_user)
    return notifications_service.mark_own_notification_read(
        student_ctx["student_id"],
        notification_id,
    )
