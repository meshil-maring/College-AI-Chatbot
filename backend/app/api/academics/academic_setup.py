"""Institution-admin Academic Setup for the supplied SQL export."""

from uuid import UUID

from fastapi import APIRouter, Body, Depends
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.security import require_institution_roles
from app.schemas.academics.academic_setup import AcademicEntity, AcademicSetupResponse
from app.services.academics import academic_setup as service


router = APIRouter(prefix="/admin/academic-setup", tags=["academic-setup"])
_ADMIN = require_institution_roles("admin")


@router.get("", response_model=AcademicSetupResponse, summary="Read institution Academic Setup",
            description="Departments, programs, academic years, dated semesters, courses, program-course links, offerings and sections. Tenant context is server-selected.")
def get_academic_setup(user: dict = Depends(_ADMIN)):
    return service.get_setup(user)


def _write(user, entity, body, record_id=None):
    try:
        return service.manage_record(user, entity, body, record_id)
    except ValidationError as exc:
        errors = [{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]
        raise RequestValidationError(errors) from exc


@router.post("/{entity}", status_code=201, summary="Create an Academic Setup record",
             description="Semesters belong to academic years and require dates. Program-course links define curricula. Offerings select a linked course, program, academic year and semester. Sections belong to one offering.")
def create_academic_record(entity: AcademicEntity, body: dict = Body(...), user: dict = Depends(_ADMIN)):
    return _write(user, entity, body)


@router.patch("/{entity}/{record_id}", summary="Edit or deactivate an Academic Setup record",
              description="Parent references and section codes are immutable. Records are deactivated to retain history. Actor and institution cannot be supplied by the caller.")
def update_academic_record(entity: AcademicEntity, record_id: UUID, body: dict = Body(...), user: dict = Depends(_ADMIN)):
    return _write(user, entity, body, str(record_id))
