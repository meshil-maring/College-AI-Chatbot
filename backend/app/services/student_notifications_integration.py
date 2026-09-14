"""Phase 6.11 — Academic event notification integration.

Service functions that authorized backend workflows can invoke to generate
notifications from authoritative academic events.

These are NOT automatic — they must be explicitly called by the attendance
or results service workflows. The notification system is NOT a second source
of truth; it references authoritative records already owned by the
institution/student data model.

This module is intentionally additive — it does NOT modify the Phase 6.7
attendance or Phase 6.8 results services. It provides integration hooks
that those services MAY call when appropriate.
"""

from typing import Any
from uuid import UUID

from app.services.student_notifications import create_notification_for_student


def notify_attendance_alert(
    student_id: UUID | str,
    institution_id: UUID | str,
    attendance_record_id: UUID | str,
    section_code: str,
    attendance_date: str,
    status: str,
    client: Any = None,
) -> dict:
    """Generate an attendance-alert notification for an attendance record.

    The notification references the authoritative attendance record via
    source_record_id for idempotency.
    """
    return create_notification_for_student(
        student_id=student_id,
        institution_id=institution_id,
        notification_type="attendance_alert",
        title=f"Attendance alert: {section_code}",
        message=(
            f"Your attendance for {section_code} on {attendance_date} "
            f"has been recorded as {status}."
        ),
        source_type="attendance_record",
        source_record_id=UUID(attendance_record_id),
        client=client,
    )


def notify_result_published(
    student_id: UUID | str,
    institution_id: UUID | str,
    result_id: UUID | str,
    result_title: str,
    client: Any = None,
) -> dict:
    """Generate a result-published notification when a new academic result
    becomes available.

    The notification references the authoritative result record via
    source_record_id for idempotency.
    """
    return create_notification_for_student(
        student_id=student_id,
        institution_id=institution_id,
        notification_type="result_published",
        title=f"Result published: {result_title}",
        message=(
            f"Your result '{result_title}' has been published and is now "
            f"available in your academic records."
        ),
        source_type="student_result",
        source_record_id=UUID(result_id),
        client=client,
    )


def notify_test_result_published(
    student_id: UUID | str,
    institution_id: UUID | str,
    test_result_id: UUID | str,
    test_name: str,
    client: Any = None,
) -> dict:
    """Generate a test-result-published notification when a new test score
    becomes available.

    The notification references the authoritative test result record via
    source_record_id for idempotency.
    """
    return create_notification_for_student(
        student_id=student_id,
        institution_id=institution_id,
        notification_type="result_published",
        title=f"Test result published: {test_name}",
        message=(
            f"Your score for '{test_name}' is now available."
        ),
        source_type="test_result",
        source_record_id=UUID(test_result_id),
        client=client,
    )


def notify_academic_status(
    student_id: UUID | str,
    institution_id: UUID | str,
    title: str,
    message: str,
    source_record_id: UUID | None = None,
    client: Any = None,
) -> dict:
    """Generate an academic-status notification for an important academic
    status change."""
    return create_notification_for_student(
        student_id=student_id,
        institution_id=institution_id,
        notification_type="academic_status",
        title=title,
        message=message,
        source_type="academic_status",
        source_record_id=source_record_id,
        client=client,
    )


def notify_academic_admin(
    student_id: UUID | str,
    institution_id: UUID | str,
    title: str,
    message: str,
    source_record_id: UUID | None = None,
    client: Any = None,
) -> dict:
    """Generate a general academic/admin notification for a specific student."""
    return create_notification_for_student(
        student_id=student_id,
        institution_id=institution_id,
        notification_type="academic_admin",
        title=title,
        message=message,
        source_type="academic_admin",
        source_record_id=source_record_id,
        client=client,
    )
