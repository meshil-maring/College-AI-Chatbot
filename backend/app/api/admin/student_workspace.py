"""Admin student workspace endpoints."""

from typing import Literal
from uuid import UUID

from fastapi import Depends, Query

from app.core.security import has_permission
from app.schemas.students.student_registrations import StudentRegistrationCreate
from app.services.students import student_registrations
from app.services.faculty import faculty_attendance_reporting as student_reporting
from app.services.faculty.faculty_students import registration_history
from app.services.auth.phase81_rbac import _active_sections
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get('/student-workspace/sections')
def student_workspace_sections(current_user: dict = Depends(_ADMIN)) -> list[dict]:
    return [{**section, 'can_manage': has_permission(current_user, 'students.create')}
            for section in _active_sections(UUID(str(current_user['institution_id'])))]


@router.get('/student-workspace/sections/{section_id}/students')
def student_workspace_roster(section_id: UUID, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
    search: str = Query('', max_length=128), registration: Literal['UNREGISTERED', 'PENDING_APPROVAL', 'ACTIVE', 'INACTIVE'] | None = None,
    sort: Literal['register_number', 'student_name', 'attendance_percentage', 'record_count'] = 'register_number',
    descending: bool = False, batch_id: UUID | None = None, current_user: dict = Depends(_ADMIN)) -> dict:
    return student_reporting.students_page(current_user, section_id, limit=limit, offset=offset,
        search=search, registration=registration, sort=sort, descending=descending, batch_id=batch_id)


@router.get('/student-workspace/roster/{roster_id}/profile')
def student_workspace_profile(roster_id: UUID, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                              current_user: dict = Depends(_ADMIN)) -> dict:
    return student_reporting.student_profile(current_user, roster_id, limit=limit, offset=offset)


@router.get('/student-workspace/sections/{section_id}/history')
def student_workspace_history(section_id: UUID, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
    search: str = Query('', max_length=128), current_user: dict = Depends(_ADMIN)) -> dict:
    return registration_history(current_user, section_id, limit=limit, offset=offset, search=search)


@router.get('/student-workspace/sections/{section_id}/registrations')
def student_workspace_registrations(section_id: UUID, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    registration: Literal['UNREGISTERED', 'PENDING_APPROVAL', 'ACTIVE', 'INACTIVE'] | None = None,
    batch_id: UUID | None = None, search: str = Query('', max_length=128),
    sort: Literal['register_number', 'student_name'] = 'register_number',
    current_user: dict = Depends(_ADMIN)) -> dict:
    return student_registrations.list_registrations(current_user, section_id, limit=limit, offset=offset,
        registration=registration, batch_id=batch_id, search=search, sort=sort)


@router.get('/student-workspace/sections/{section_id}/batches')
def student_workspace_batches(section_id: UUID, include_inactive: bool = False, current_user: dict = Depends(_ADMIN)) -> list[dict]:
    return student_registrations.available_batches(current_user, section_id, include_inactive=include_inactive)


@router.post('/student-workspace/sections/{section_id}/registrations', status_code=201)
def student_workspace_register(section_id: UUID, payload: StudentRegistrationCreate, current_user: dict = Depends(_ADMIN)) -> dict:
    created = student_registrations.create_registration(current_user, section_id, payload, permission='students.create')
    common.record_audit(current_user, 'students.registration.create', 'student_registrations', str(created['registration_id']), created)
    return created


@router.post('/student-workspace/sections/{section_id}/registrations/{registration_id}/invitation')
def student_workspace_invitation(section_id: UUID, registration_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    from app.services.invitations.student_registration_invitations import send_invitation
    return send_invitation(current_user, section_id, registration_id, permission='students.create')
