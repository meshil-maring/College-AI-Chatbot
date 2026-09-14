"""Phase 6.11 — Student notification repository.

Scoped database access for the student_notifications table.

All functions follow the project repository convention: the first argument
is an already-created Supabase Client (service-role client in production).

The database trigger (trg_student_notifications_tenant_guard) is the
backstop that derives institution_id from the student record and rejects
cross-student/cross-tenant writes at the database level.
"""

from uuid import UUID

from supabase import Client

from app.schemas.student_notifications import NotificationCreate, NotificationCreateResult

NOTIFICATION_COLUMNS = (
    "notification_id, student_id, institution_id, notification_type, "
    "title, message, is_read, source_type, source_record_id, "
    "created_at, read_at"
)


def get_notification(
    client: Client, notification_id: UUID | str
) -> dict | None:
    """Return one notification row, or None when it does not exist."""
    response = (
        client.table("student_notifications")
        .select(NOTIFICATION_COLUMNS)
        .eq("notification_id", str(notification_id))
        .maybe_single()
        .execute()
    )
    return response.data


def list_notifications(
    client: Client,
    student_id: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List notifications for one student, newest first.

    Deterministic ordering by created_at DESC with stable pagination.
    """
    response = (
        client.table("student_notifications")
        .select(NOTIFICATION_COLUMNS)
        .eq("student_id", str(student_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data


def count_notifications_by_student(
    client: Client, student_id: UUID | str
) -> int:
    """Return the total notification count for one student."""
    response = (
        client.table("student_notifications")
        .select("notification_id", count="exact")
        .eq("student_id", str(student_id))
        .execute()
    )
    return response.count or 0


def count_unread_by_student(
    client: Client, student_id: UUID | str
) -> int:
    """Return the unread notification count for one student."""
    response = (
        client.table("student_notifications")
        .select("notification_id", count="exact")
        .eq("student_id", str(student_id))
        .eq("is_read", False)
        .execute()
    )
    return response.count or 0


def create_notification(
    client: Client, payload: NotificationCreate
) -> NotificationCreateResult:
    """Insert one notification row and return the stored row.

    The database trigger derives institution_id from the student record
    and rejects cross-student/cross-tenant writes. The caller should map
    duplicate-source-record errors (UNIQUE violation on
    student_id + source_record_id + notification_type) to a business
    error (NOTIFICATION_DUPLICATE, 409).
    """
    row = payload.model_dump(mode="json")
    response = (
        client.table("student_notifications")
        .insert(row)
        .select(NOTIFICATION_COLUMNS)
        .single()
        .execute()
    )
    return response.data


def mark_notification_read(
    client: Client, notification_id: UUID | str
) -> dict | None:
    """Set is_read=True and read_at=now() on one notification.

    Returns the updated row, or None when the row disappeared between
    lookup and update.
    """
    response = (
        client.table("student_notifications")
        .update({"is_read": True, "read_at": "now()"})
        .eq("notification_id", str(notification_id))
        .select(NOTIFICATION_COLUMNS)
        .single()
        .execute()
    )
    return response.data


def notification_belongs_to_student(
    client: Client, notification_id: UUID | str, student_id: UUID | str
) -> bool:
    """Return True when the notification belongs to the given student.

    Used for ownership checks before mutations.
    """
    row = get_notification(client, notification_id)
    if row is None:
        return False
    return str(row.get("student_id")) == str(student_id)
