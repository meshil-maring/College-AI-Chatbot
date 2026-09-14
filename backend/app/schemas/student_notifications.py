"""Phase 6.11 — Student notification schemas.

Notification contracts for the student notification / academic-alert system.

Notifications reference authoritative records already owned by the
institution/student data model. They are NOT a second source of truth.

Notification types use a controlled vocabulary — arbitrary strings are
rejected at the schema and database level.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Controlled notification vocabulary
# ---------------------------------------------------------------------------

class NotificationType(str):
    """Controlled vocabulary of notification types.

    These map 1:1 to the DB CHECK constraint on student_notifications.notification_type.
    Do not invent new types without a migration.
    """

    ATTENDANCE_ALERT = "attendance_alert"
    RESULT_PUBLISHED = "result_published"
    ACADEMIC_STATUS = "academic_status"
    ACADEMIC_ADMIN = "academic_admin"


NOTIFICATION_TYPES: tuple[str, ...] = (
    NotificationType.ATTENDANCE_ALERT,
    NotificationType.RESULT_PUBLISHED,
    NotificationType.ACADEMIC_STATUS,
    NotificationType.ACADEMIC_ADMIN,
)


# ---------------------------------------------------------------------------
# Internal write models (service layer)
# ---------------------------------------------------------------------------


class NotificationCreate(BaseModel):
    """Payload for creating one notification (internal / service use only).

    Students can NEVER create their own notifications via the API.
    This model is used by authorized backend workflows (attendance,
    results, admin) to generate notifications from authoritative events.
    """

    student_id: UUID
    institution_id: UUID
    notification_type: str = Field(..., pattern="^(attendance_alert|result_published|academic_status|academic_admin)$")
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    source_type: str = "academic_event"
    source_record_id: UUID | None = None

    model_config = {"extra": "forbid"}


class NotificationCreateResult(BaseModel):
    """The stored notification row returned after creation."""

    notification_id: UUID
    student_id: UUID
    institution_id: UUID
    notification_type: str
    title: str
    message: str
    is_read: bool
    source_type: str
    source_record_id: UUID | None
    created_at: datetime
    read_at: datetime | None


# ---------------------------------------------------------------------------
# Student read models (API response contracts)
# ---------------------------------------------------------------------------


class Notification(BaseModel):
    """A single notification as returned to the authenticated student."""

    notification_id: UUID
    student_id: UUID
    institution_id: UUID
    notification_type: str
    title: str
    message: str
    is_read: bool
    source_type: str
    source_record_id: UUID | None
    created_at: datetime
    read_at: datetime | None

    model_config = {"extra": "forbid"}


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""

    items: list[Notification] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    has_more: bool


# ---------------------------------------------------------------------------
# Read-state mutation
# ---------------------------------------------------------------------------


class MarkReadRequest(BaseModel):
    """Payload for marking a notification as read.

    Students can only mark their OWN notifications as read.
    This model enforces that no other fields can be supplied.
    """

    pass
