"""Admin attendance endpoints."""

from uuid import UUID

from fastapi import Depends

from app.services.academics import attendance
from app.services.admin.admin_academics import AttendanceCreate, AttendanceUpdate
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/students/{student_id}/attendance")
def list_student_attendance(
    student_id: UUID,
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    common.assert_student_tenant(current_user, student_id)
    return attendance.list_attendance_for_student(
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/attendance", status_code=201)
def create_attendance(
    payload: AttendanceCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_student_tenant(current_user, payload.student_id)
    created = attendance.create_attendance(payload)
    common.record_audit(
        current_user,
        "attendance.create",
        "student_attendance",
        created["student_attendance_id"],
        {
            "student_id": str(payload.student_id),
            "date": str(payload.date),
            "status": payload.status,
        },
    )
    return created


@router.patch("/attendance/{attendance_id}")
def update_attendance(
    attendance_id: UUID,
    payload: AttendanceUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    existing = attendance.get_attendance(attendance_id)
    common.assert_student_tenant(current_user, existing["student_id"])
    updated = attendance.update_attendance(attendance_id, payload)
    common.record_audit(
        current_user,
        "attendance.update",
        "student_attendance",
        str(attendance_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated


@router.delete("/attendance/{attendance_id}")
def delete_attendance(attendance_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    existing = attendance.get_attendance(attendance_id)
    common.assert_student_tenant(current_user, existing["student_id"])
    deleted = attendance.delete_attendance(attendance_id)
    common.record_audit(
        current_user,
        "attendance.delete",
        "student_attendance",
        str(attendance_id),
        None,
    )
    return {"deleted": True, "attendance": deleted}
