"""Faculty class registrations and subject assignment endpoints."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.security import authorize_permissions
from app.api.faculty.dependencies import _FACULTY
from app.schemas.students.student_registrations import StudentRegistrationCreate
from app.services.students import student_registrations, subject_assignments

router = APIRouter()


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


@router.get('/student-registrations/sections/{scope_section_id}/subject-assignments')
def subject_assignment_students(scope_section_id: UUID, limit: int = Query(25, ge=1, le=100),
                                offset: int = Query(0, ge=0), batch_id: UUID | None = None,
                                search: str = Query('', max_length=128), current_user: dict = Depends(_FACULTY)) -> dict:
    return subject_assignments.unassigned_students(current_user, scope_section_id,
        limit=limit, offset=offset, batch_id=batch_id, search=search)


@router.post('/student-registrations/sections/{scope_section_id}/subject-assignments/{registration_id}')
def assign_student_subject(scope_section_id: UUID, registration_id: UUID,
                           current_user: dict = Depends(_FACULTY)) -> dict:
    authorize_permissions(current_user, 'attendance.manage')
    return subject_assignments.assign_student(current_user, scope_section_id, registration_id)


