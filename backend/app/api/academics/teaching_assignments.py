"""Teaching assignments for administrators and Heads of Department."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import require_institution_roles
from app.schemas.academics.teaching_assignments import TeachingAssignmentCreate, TeachingAssignmentDecision
from app.services.academics import teaching_assignments as service


router = APIRouter(prefix="/teaching-assignments", tags=["teaching-assignments"])
# Any active admin or faculty grant reaches the service; the database admits
# only administrators and current Heads of Department.
_ACTOR = require_institution_roles("admin", "faculty")


@router.get("")
def teaching_assignments(user: dict = Depends(_ACTOR)):
    return service.overview(user)


@router.get("/options")
def teaching_options(user: dict = Depends(_ACTOR)):
    return service.options(user)


@router.post("", status_code=201)
def request_teaching(body: TeachingAssignmentCreate, user: dict = Depends(_ACTOR)):
    return service.request(user, body.model_dump())


@router.post("/{assignment_id}/decision")
def decide_teaching(assignment_id: UUID, body: TeachingAssignmentDecision, user: dict = Depends(_ACTOR)):
    return service.decide(user, str(assignment_id), body.action, body.note)


@router.post("/{assignment_id}/end")
def end_teaching(assignment_id: UUID, user: dict = Depends(_ACTOR)):
    return service.end(user, str(assignment_id))
