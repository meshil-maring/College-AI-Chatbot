"""Student transfer requests, reviewer decisions and Head of Department appointments."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_institution_roles
from app.schemas.academics.student_transfers import (
    DepartmentHeadAdd, DepartmentHeadPolicy, DepartmentHeadTerm, DepartmentHeadWrite, DirectTransfer,
    TransferDecision, TransferSubmit,
)
from app.services.academics import student_transfers as service


router = APIRouter(tags=["student-transfers"])
_REVIEWER = require_institution_roles("admin", "faculty")
_ADMIN = require_institution_roles("admin")
_OWN = "/students/me/transfer-requests"


@router.get(_OWN)
def my_transfers(user: dict = Depends(get_current_user)):
    return service.own_transfers(user)


@router.post(_OWN, status_code=201)
def submit_transfer(body: TransferSubmit, user: dict = Depends(get_current_user)):
    return service.submit(user, body.model_dump(mode="json"))


@router.post(_OWN + "/{request_id}/cancel")
def cancel_transfer(request_id: UUID, user: dict = Depends(get_current_user)):
    return service.cancel(user, str(request_id))


@router.get("/transfer-reviews")
def transfer_reviews(
    status: Literal["open", "all"] = "open", user: dict = Depends(_REVIEWER),
):
    return service.reviews(user, status == "open")


@router.post("/transfer-reviews/{request_id}/decision")
def decide_transfer(request_id: UUID, body: TransferDecision, user: dict = Depends(_REVIEWER)):
    return service.decide(user, str(request_id), body.model_dump(mode="json"))


@router.get("/transfer-direct/students")
def direct_transfer_students(user: dict = Depends(_REVIEWER)):
    return service.direct_students(user)


@router.get("/transfer-direct/students/{student_id}")
def direct_transfer_options(student_id: UUID, user: dict = Depends(_REVIEWER)):
    return service.direct_options(user, str(student_id))


@router.post("/transfer-direct", status_code=201)
def direct_transfer(body: DirectTransfer, user: dict = Depends(_REVIEWER)):
    return service.direct_transfer(user, body.model_dump(mode="json"))


@router.get("/admin/department-heads")
def department_heads(user: dict = Depends(_ADMIN)):
    return service.department_heads(user)


# Replaces every current head with one faculty member, or removes them all.
@router.put("/admin/department-heads/{department_id}")
def assign_department_head(
    department_id: UUID, body: DepartmentHeadWrite, user: dict = Depends(_ADMIN),
):
    faculty = str(body.faculty_user_id) if body.faculty_user_id else None
    return service.assign_department_head(user, str(department_id), faculty)


# A department may have several equal heads, and one faculty member may head
# several departments. These add or end a single appointment.
@router.post("/admin/department-heads/{department_id}/heads", status_code=201)
def add_department_head(
    department_id: UUID, body: DepartmentHeadAdd, user: dict = Depends(_ADMIN),
):
    return service.add_department_head(
        user, str(department_id), str(body.faculty_user_id), body.starts_on, body.planned_end_on
    )


@router.put("/admin/department-heads/{department_id}/heads/{faculty_user_id}/term")
def set_department_head_term(
    department_id: UUID, faculty_user_id: UUID, body: DepartmentHeadTerm, user: dict = Depends(_ADMIN),
):
    return service.set_department_head_term(
        user, str(department_id), str(faculty_user_id), body.starts_on, body.planned_end_on
    )


# Its own path so it never collides with /admin/department-heads/{department_id}.
@router.put("/admin/department-head-policy")
def set_department_head_policy(body: DepartmentHeadPolicy, user: dict = Depends(_ADMIN)):
    return service.set_department_head_policy(user, body.allow_multi_department_hod)


@router.delete("/admin/department-heads/{department_id}/heads/{faculty_user_id}")
def end_department_head(
    department_id: UUID, faculty_user_id: UUID, user: dict = Depends(_ADMIN),
):
    return service.end_department_head(user, str(department_id), str(faculty_user_id))
