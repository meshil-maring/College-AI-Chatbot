"""Faculty self-service views limited to server-owned active assignments."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import PlainTextResponse

from app.api.faculty.faculty_tests import router as tests_router
from app.core.security import authorize_permissions, require_institution_roles
from app.schemas.faculty.faculty_attendance import (
    ImportRowCorrection,
    ManualAttendanceRequest,
    RosterStudentInput,
    RosterUpdateRequest,
)
from app.schemas.faculty.faculty_responsibilities import AssignmentValidity, ScopedTeachingAssignmentCreate
from app.services.faculty import faculty_attendance
from app.services.faculty import faculty_responsibilities
from app.services.faculty import faculty_attendance_reporting as reporting
from app.services.auth.phase81_rbac import list_own_faculty_assignments
from app.schemas.students.student_registrations import StudentRegistrationCreate
from app.services.students import student_registrations

router = APIRouter(prefix="/faculty", tags=["faculty"])
router.include_router(tests_router)
_FACULTY = require_institution_roles("faculty")


@router.get('/student-registrations/sections/{scope_section_id}/batches')
def registration_batches(scope_section_id: UUID, include_inactive: bool = False, current_user: dict = Depends(_FACULTY)) -> list[dict]:
    return student_registrations.available_batches(current_user, scope_section_id, include_inactive=include_inactive)


@router.get('/student-registrations/sections/{scope_section_id}')
def class_registrations(scope_section_id: UUID, limit: int = Query(100, ge=1, le=500),
                        offset: int = Query(0, ge=0),
                        registration: Literal['UNREGISTERED', 'PENDING_APPROVAL', 'ACTIVE', 'INACTIVE'] | None = None,
                        batch_id: UUID | None = None, search: str = Query('', max_length=128),
                        sort: Literal['register_number', 'student_name'] = 'register_number',
                        current_user: dict = Depends(_FACULTY)) -> dict:
    return student_registrations.list_registrations(current_user, scope_section_id, limit=limit, offset=offset,
        registration=registration, batch_id=batch_id, search=search, sort=sort)


@router.post('/student-registrations/sections/{scope_section_id}', status_code=201)
def register_class_student(scope_section_id: UUID, payload: StudentRegistrationCreate,
                           current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    created = student_registrations.create_registration(current_user, scope_section_id, payload)
    from app.repositories.admin.admin_audit import record_admin_action
    from app.schemas.admin.admin import AdminAuditLogCreate
    record_admin_action(student_registrations.get_admin_client(), AdminAuditLogCreate(
        actor_user_id=UUID(str(current_user['user_id'])), institution_id=UUID(str(current_user['institution_id'])),
        action='students.registration.create', table_name='student_registrations',
        record_id=str(created['registration_id']), record_data=created))
    return created


@router.post('/student-registrations/sections/{scope_section_id}/{registration_id}/invitation')
def send_student_registration_invitation(scope_section_id: UUID, registration_id: UUID,
                                         current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    from app.services.invitations.student_registration_invitations import send_invitation
    return send_invitation(current_user, scope_section_id, registration_id)


@router.get("/context")
def get_faculty_context(current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, "profile.own.read")
    return faculty_responsibilities.faculty_context(current_user)


@router.get("/responsibilities/{responsibility_id}/report")
def get_responsibility_report(responsibility_id: UUID, current_user: dict = Depends(_FACULTY)) -> dict:
    return faculty_responsibilities.responsibility_report(current_user, responsibility_id)


@router.get("/assignments")
def get_my_assignments(
    current_user: dict = Depends(_FACULTY),
) -> list[dict]:
    authorize_permissions(current_user, "faculty.assignments.read")
    return list_own_faculty_assignments(current_user)


@router.get("/teaching-assignments/management")
def get_scoped_teaching_assignments(current_user: dict = Depends(_FACULTY)) -> dict:
    return faculty_responsibilities.scoped_teaching_management_data(current_user)


@router.post("/teaching-assignments/management", status_code=201)
def create_scoped_teaching_assignment(
    payload: ScopedTeachingAssignmentCreate,
    current_user: dict = Depends(_FACULTY),
) -> dict:
    return faculty_responsibilities.manage_scoped_teaching(
        current_user,
        faculty_user_id=payload.faculty_user_id,
        section_id=payload.section_id,
        validity=payload,
    )


@router.patch("/teaching-assignments/management/{assignment_id}")
def update_scoped_teaching_assignment(
    assignment_id: UUID,
    payload: AssignmentValidity,
    current_user: dict = Depends(_FACULTY),
) -> dict:
    return faculty_responsibilities.manage_scoped_teaching_by_id(
        current_user, assignment_id, validity=payload
    )


@router.post("/teaching-assignments/management/{assignment_id}/revoke")
def revoke_scoped_teaching_assignment(
    assignment_id: UUID,
    current_user: dict = Depends(_FACULTY),
) -> dict:
    return faculty_responsibilities.manage_scoped_teaching_by_id(
        current_user, assignment_id, revoke=True
    )


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
    return faculty_attendance.list_roster(current_user, section_id, limit=limit, offset=offset, search=search)


@router.get('/attendance/resources')
def attendance_resources(current_user: dict = Depends(_FACULTY)) -> list[dict]:
    return reporting.resources(current_user)


@router.get('/attendance/sections/{section_id}/overview')
def attendance_overview(section_id: UUID, current_user: dict = Depends(_FACULTY)) -> dict:
    return reporting.overview(current_user, section_id)


@router.get('/attendance/sections/{section_id}/students')
def attendance_students(section_id: UUID, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
    search: str = Query('', max_length=128),
    registration: Literal['UNREGISTERED','PENDING_APPROVAL','ACTIVE','INACTIVE'] | None = None,
    low_only: bool = False, sort: Literal['register_number','student_name','attendance_percentage','record_count'] = 'register_number',
    descending: bool = False, batch_id: UUID | None = None, current_user: dict = Depends(_FACULTY)) -> dict:
    return reporting.students_page(current_user, section_id, limit=limit, offset=offset, search=search,
        registration=registration, low_only=low_only, sort=sort, descending=descending, batch_id=batch_id)


@router.get('/attendance/roster/{roster_id}/profile')
def attendance_profile(roster_id: UUID, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
    current_user: dict = Depends(_FACULTY)) -> dict:
    return reporting.student_profile(current_user, roster_id, limit=limit, offset=offset)


@router.get('/attendance/sections/{section_id}/registration-history')
def student_registration_history(
    section_id: UUID,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str = Query('', max_length=128),
    current_user: dict = Depends(_FACULTY),
) -> dict:
    from app.services.faculty.faculty_students import registration_history
    return registration_history(current_user, section_id, limit=limit, offset=offset, search=search)


@router.get('/attendance/sections/{section_id}/sessions')
def attendance_sessions(section_id: UUID, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
    current_user: dict = Depends(_FACULTY)) -> dict:
    return reporting.sessions_page(current_user, section_id, limit=limit, offset=offset)


@router.post('/attendance/sections/{section_id}/roster', status_code=201)
def add_roster_student(section_id: UUID, payload: RosterStudentInput, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    created = faculty_attendance.create_manual(current_user, section_id, payload)
    from app.repositories.admin.admin_audit import record_admin_action
    from app.schemas.admin.admin import AdminAuditLogCreate
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
    from app.api.admin.common import record_audit as _record_audit
    _record_audit(current_user, 'attendance.roster.update', 'faculty_attendance_rosters', str(roster_id), updated)
    return updated


@router.delete('/attendance/roster/{roster_id}')
def remove_roster(roster_id: UUID, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    deleted = faculty_attendance.delete_roster(current_user, roster_id)
    from app.repositories.admin.admin_audit import record_admin_action
    from app.schemas.admin.admin import AdminAuditLogCreate
    record_admin_action(faculty_attendance.get_admin_client(), AdminAuditLogCreate(actor_user_id=UUID(str(current_user['user_id'])), institution_id=UUID(str(current_user['institution_id'])), action='attendance.roster.delete', table_name='faculty_attendance_rosters', record_id=str(roster_id), record_data=deleted))
    return {'deleted': True, 'roster': deleted}


@router.post('/attendance/sections/{section_id}/mark')
def mark_attendance(section_id: UUID, payload: ManualAttendanceRequest, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    result = faculty_attendance.mark_attendance(current_user, section_id, payload)
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
    from starlette.concurrency import run_in_threadpool

    from app.services.knowledge.ingestion import read_upload_limited
    faculty_attendance._assert_assigned(current_user, section_id)
    content = await read_upload_limited(file, faculty_attendance.MAX_IMPORT_BYTES)
    result = await run_in_threadpool(faculty_attendance.upload_import, current_user, section_id, semester_id, file.filename or '', content, ai_confirmed, file.content_type)
    return result


@router.get('/attendance/imports/{import_id}/review')
def import_review(import_id: UUID, current_user: dict = Depends(_FACULTY)) -> dict:
    return faculty_attendance.review_import(current_user, import_id)


@router.patch('/attendance/imports/{import_id}/rows/{row_number}')
def correct_import(import_id: UUID, row_number: int, payload: ImportRowCorrection, current_user: dict = Depends(_FACULTY)) -> dict:
    return faculty_attendance.correct_import_row(current_user, import_id, row_number, payload.data)


@router.get('/attendance/sections/{section_id}/imports')
def import_history(section_id: UUID, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0), current_user: dict = Depends(_FACULTY)) -> list[dict]:
    return faculty_attendance.list_imports(current_user, section_id, limit=limit, offset=offset)


@router.get('/attendance/imports/{import_id}/errors.csv', response_class=PlainTextResponse)
def import_errors(import_id: UUID, current_user: dict = Depends(_FACULTY)) -> str:
    return faculty_attendance.error_report(current_user, import_id)


@router.post('/attendance/imports/{import_id}/commit')
def import_commit(import_id: UUID, current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    result = faculty_attendance.commit_import(current_user, import_id)
    return result
