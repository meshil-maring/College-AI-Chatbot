"""Student transfer requests, reviewer decisions and Head of Department appointments."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_institution_roles
from app.schemas.academics.student_transfers import (
    DepartmentHeadWrite, TransferDecision, TransferSubmit,
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


@router.get("/admin/department-heads")
def department_heads(user: dict = Depends(_ADMIN)):
    return service.department_heads(user)


@router.put("/admin/department-heads/{department_id}")
def assign_department_head(
    department_id: UUID, body: DepartmentHeadWrite, user: dict = Depends(_ADMIN),
):
    faculty = str(body.faculty_user_id) if body.faculty_user_id else None
    return service.assign_department_head(user, str(department_id), faculty)
