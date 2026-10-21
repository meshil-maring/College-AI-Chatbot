"""Admin faculty endpoints."""

from uuid import UUID

from fastapi import Depends

from app.core.security import user_tenant_id
from app.schemas.auth.phase81 import FacultyAssignmentCreate, FacultyAssignmentRevoke
from app.schemas.faculty.faculty_responsibilities import (
    AssignmentValidity,
    ResponsibilityCreate,
    ResponsibilityUpdate,
)
from app.services.faculty import faculty_responsibilities
from app.services.auth import phase81_rbac
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/faculty-assignments")
def get_faculty_assignments(
    current_user: dict = Depends(_ADMIN),
) -> dict:
    return phase81_rbac.list_institution_assignments(
        UUID(str(user_tenant_id(current_user)))
    )


@router.get("/faculty-responsibilities")
def get_faculty_responsibilities(current_user: dict = Depends(_ADMIN)) -> dict:
    return faculty_responsibilities.management_data(current_user, UUID(str(user_tenant_id(current_user))))


@router.post("/faculty-responsibilities", status_code=201)
def create_responsibility(body: ResponsibilityCreate, current_user: dict = Depends(_ADMIN)) -> dict:
    return faculty_responsibilities.change_responsibility(current_user, UUID(str(user_tenant_id(current_user))), body)


@router.patch("/faculty-responsibilities/{responsibility_id}")
def update_responsibility(responsibility_id: UUID, body: ResponsibilityUpdate, current_user: dict = Depends(_ADMIN)) -> dict:
    return faculty_responsibilities.change_responsibility(current_user, UUID(str(user_tenant_id(current_user))), body, responsibility_id=responsibility_id)


@router.delete("/faculty-responsibilities/{responsibility_id}")
def delete_responsibility(responsibility_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    return faculty_responsibilities.change_responsibility(current_user, UUID(str(user_tenant_id(current_user))), None, responsibility_id=responsibility_id, revoke=True)


@router.patch("/faculty-assignments/{assignment_id}")
def update_teaching_assignment(assignment_id: UUID, body: AssignmentValidity, current_user: dict = Depends(_ADMIN)) -> dict:
    return faculty_responsibilities.update_teaching(current_user, UUID(str(user_tenant_id(current_user))), assignment_id, body)


@router.post("/faculty-assignments", status_code=201)
def create_faculty_assignment(
    body: FacultyAssignmentCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    if body.start_at is not None:
        return faculty_responsibilities.create_teaching(current_user, UUID(str(user_tenant_id(current_user))), body)
    return phase81_rbac.manage_faculty_assignment(
        current_user,
        UUID(str(user_tenant_id(current_user))),
        body.faculty_user_id,
        body.section_id,
        revoke=False,
    )


@router.delete(
    "/faculty-assignments/{assignment_id}",
    response_model=FacultyAssignmentRevoke,
)
def revoke_faculty_assignment(
    assignment_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    return phase81_rbac.revoke_faculty_assignment(
        current_user,
        UUID(str(user_tenant_id(current_user))),
        assignment_id,
    )
