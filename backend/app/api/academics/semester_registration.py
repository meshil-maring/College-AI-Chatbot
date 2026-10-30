"""Curriculum option setup, section assignment and student self-registration."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_institution_roles
from app.schemas.academics.semester_registration import (
    ChoiceGroupWrite, SemesterAssignment, SemesterSelection,
)
from app.services.academics import semester_registration as service


router = APIRouter(tags=["semester-registration"])
_ADMIN = require_institution_roles("admin")
_BASE = "/admin/academic-registration"


@router.get(_BASE)
def registration_catalogue(user: dict = Depends(_ADMIN)):
    return service.catalogue(user)


@router.post(_BASE + "/option-groups", status_code=201)
def create_group(body: ChoiceGroupWrite, user: dict = Depends(_ADMIN)):
    return service.save_group(user, body.model_dump(mode="json"))


@router.patch(_BASE + "/option-groups/{group_id}")
def update_group(group_id: UUID, body: ChoiceGroupWrite, user: dict = Depends(_ADMIN)):
    return service.save_group(user, body.model_dump(mode="json"), str(group_id))


@router.delete(_BASE + "/option-groups/{group_id}")
def delete_group(group_id: UUID, user: dict = Depends(_ADMIN)):
    return service.save_group(user, {}, str(group_id), delete=True)


@router.post(_BASE + "/assignments", status_code=201)
def assign_student(body: SemesterAssignment, user: dict = Depends(_ADMIN)):
    return service.assign_student(user, body.model_dump(mode="json"))


@router.get("/students/me/semester-registrations")
def my_semesters(user: dict = Depends(get_current_user)):
    return service.own_semesters(user)


@router.post("/students/me/semester-registrations/{registration_id}/complete")
def complete_semester(registration_id: UUID, body: SemesterSelection, user: dict = Depends(get_current_user)):
    return service.complete(user, str(registration_id), [str(item) for item in body.selected_option_ids])
