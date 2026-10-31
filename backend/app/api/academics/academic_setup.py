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


@router.delete("/departments/{record_id}", summary="Delete an unused department",
               description="Only an institution administrator with department-management permission may delete. Any linked record, including inactive records, prevents deletion.")
def delete_department(record_id: UUID, user: dict = Depends(_ADMIN)):
    return service.delete_department(user, str(record_id))


@router.delete("/programs/{record_id}", summary="Delete an unused program",
               description="Requires the institution-admin department-management grant used for programs. Any linked record, including inactive records, prevents deletion.")
def delete_program(record_id: UUID, user: dict = Depends(_ADMIN)):
    return service.delete_program(user, str(record_id))


@router.delete("/academic_years/{record_id}", summary="Delete an unused, non-current academic year")
def delete_academic_year(record_id: UUID, user: dict = Depends(_ADMIN)):
    return service.delete_period(user, AcademicEntity.academic_years, str(record_id))


@router.delete("/semesters/{record_id}", summary="Delete an unused, non-current semester")
def delete_semester(record_id: UUID, user: dict = Depends(_ADMIN)):
    return service.delete_period(user, AcademicEntity.semesters, str(record_id))
