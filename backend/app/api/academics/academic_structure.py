"""Additive academic structure routes; existing catalogue routes stay stable."""

from uuid import UUID

from fastapi import APIRouter, Body, Depends
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.security import require_institution_roles
from app.schemas.academics.academic_structure import StructureEntity, StructureResponse
from app.services.academics import academic_structure as service


router = APIRouter(prefix="/admin/academic-structure", tags=["academic-setup"])
_ADMIN = require_institution_roles("admin")


@router.get("", response_model=StructureResponse)
def get_academic_structure(user: dict = Depends(_ADMIN)):
    return service.get_structure(user)


def _write(user, entity, body, record_id=None):
    try:
        return service.manage_record(user, entity, body, record_id)
    except ValidationError as exc:
        errors = [{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]
        raise RequestValidationError(errors) from exc


@router.post("/{entity}", status_code=201)
def create_structure_record(entity: StructureEntity, body: dict = Body(...), user: dict = Depends(_ADMIN)):
    return _write(user, entity, body)


@router.patch("/{entity}/{record_id}")
def update_structure_record(entity: StructureEntity, record_id: UUID, body: dict = Body(...), user: dict = Depends(_ADMIN)):
    return _write(user, entity, body, str(record_id))


@router.delete("/academic_sections/{record_id}", summary="Delete an unused class section")
def delete_section(record_id: UUID, user: dict = Depends(_ADMIN)):
    return service.delete_section(user, str(record_id))
