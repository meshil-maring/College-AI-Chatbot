"""Faculty self-service views limited to server-owned active assignments."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import PlainTextResponse

from app.core.security import authorize_permissions, require_institution_roles
from app.schemas.faculty_attendance import ManualAttendanceRequest, RosterStudentInput, RosterUpdateRequest
from app.services import faculty_attendance
from app.services.phase81_rbac import list_own_faculty_assignments

router = APIRouter(prefix="/faculty", tags=["faculty"])
_FACULTY = require_institution_roles("faculty")


@router.get("/assignments")
def get_my_assignments(
    current_user: dict = Depends(_FACULTY),
) -> list[dict]:
    authorize_permissions(current_user, "faculty.assignments.read")
    return list_own_faculty_assignments(current_user)


@router.get('/attendance/assignments')
def attendance_assignments(current_user: dict = Depends(_FACULTY)) -> list[dict]:
    authorize_permissions(current_user, 'attendance.read')
    return faculty_attendance.list_assignments(current_user)


@router.get('/attendance/sections/{section_id}/roster')
def attendance_roster(
    section_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=128),
    current_user: dict = Depends(_FACULTY),
) -> list[dict]:
    authorize_permissions(current_user, 'attendance.read')
    return faculty_attendance.list_roster(current_user, section_id, limit=limit, offset=offset, search=search)


@router.post('/attendance/sections/{section_id}/roster', status_code=201)
def add_roster_student(section_id: UUID, payload: RosterStudentInput, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    created = faculty_attendance.create_manual(current_user, section_id, payload)
    from app.repositories.admin_audit import record_admin_action
    from app.schemas.admin import AdminAuditLogCreate
    record_admin_action(
        faculty_attendance.get_admin_client(),
        AdminAuditLogCreate(
            actor_user_id=UUID(str(current_user['user_id'])),
            institution_id=UUID(str(current_user['institution_id'])),
            action='attendance.roster.create',
            table_name='faculty_attendance_rosters',
            record_id=str(created['roster_id']),
            record_data=created,
        ),
    )
    return created


@router.patch('/attendance/roster/{roster_id}')
def edit_roster(roster_id: UUID, payload: RosterUpdateRequest, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    updated = faculty_attendance.update_roster(current_user, roster_id, payload)
    from app.api.admin import _record_audit
    _record_audit(current_user, 'attendance.roster.update', 'faculty_attendance_rosters', str(roster_id), payload.model_dump(exclude_unset=True))
    return updated


@router.delete('/attendance/roster/{roster_id}')
def remove_roster(roster_id: UUID, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    deleted = faculty_attendance.delete_roster(current_user, roster_id)
    from app.repositories.admin_audit import record_admin_action
    from app.schemas.admin import AdminAuditLogCreate
    record_admin_action(faculty_attendance.get_admin_client(), AdminAuditLogCreate(actor_user_id=UUID(str(current_user['user_id'])), institution_id=UUID(str(current_user['institution_id'])), action='attendance.roster.delete', table_name='faculty_attendance_rosters', record_id=str(roster_id), record_data=deleted))
    return {'deleted': True, 'roster': deleted}


@router.post('/attendance/sections/{section_id}/mark')
def mark_attendance(section_id: UUID, payload: ManualAttendanceRequest, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    result = faculty_attendance.mark_attendance(current_user, section_id, payload)
    from app.api.admin import _record_audit
    _record_audit(current_user, 'attendance.session.mark', 'faculty_attendance_sessions', result['session_id'], {'section_id': str(section_id), 'session_date': payload.session_date.isoformat(), 'record_count': result['record_count']})
    return result


@router.post('/attendance/sections/{section_id}/imports')
async def upload_attendance(
    section_id: UUID,
    semester_id: UUID = Form(...),
    ai_confirmed: bool = Form(False),
    file: UploadFile = File(...),
    current_user: dict = Depends(_FACULTY),
) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    content = await file.read()
    result = faculty_attendance.upload_import(current_user, section_id, semester_id, file.filename or '', content, ai_confirmed, file.content_type)
    from app.api.admin import _record_audit
    _record_audit(current_user, 'attendance.import.process', 'faculty_attendance_imports', result['import_id'], {'filename': file.filename, 'summary': result['summary']})
    return result


@router.get('/attendance/imports/{import_id}/review')
def import_review(import_id: UUID, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.read')
    return faculty_attendance.review_import(current_user, import_id)


@router.get('/attendance/sections/{section_id}/imports')
def import_history(section_id: UUID, current_user: dict = Depends(_FACULTY)) -> list[dict]:
    authorize_permissions(current_user, 'attendance.read')
    return faculty_attendance.list_imports(current_user, section_id)


@router.get('/attendance/imports/{import_id}/errors.csv', response_class=PlainTextResponse)
def import_errors(import_id: UUID, current_user: dict = Depends(_FACULTY)) -> str:
    authorize_permissions(current_user, 'attendance.read')
    return faculty_attendance.error_report(current_user, import_id)


@router.post('/attendance/imports/{import_id}/commit')
def import_commit(import_id: UUID, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    result = faculty_attendance.commit_import(current_user, import_id)
    from app.api.admin import _record_audit
    _record_audit(current_user, 'attendance.import.commit', 'faculty_attendance_imports', str(import_id), result)
    return result
