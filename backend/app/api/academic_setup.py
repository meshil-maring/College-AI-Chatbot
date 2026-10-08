"""Academic setup inside the existing institution Admin API."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.core.errors import AppError
from app.core.security import authorize_permissions, require_institution_roles
from app.schemas.academic_setup import Entity, validate_payload
from app.services import academic_setup as service

_SCOPE = require_institution_roles("admin")
router = APIRouter(prefix="/admin/academic-setup", tags=["admin-academic-setup"])


@router.get("")
def get_catalogue(user: dict = Depends(_SCOPE)) -> dict:
    return service.catalogue(user)


def validated(user, entity, payload, updating):
    authorize_permissions(user, f"{service.RESOURCES[entity]}.manage")
    try:
        return validate_payload(entity, payload, updating)
    except ValidationError as error:
        raise AppError("Check required fields, values and immutable academic relationships", 422, "ACADEMIC_INPUT_INVALID") from error


@router.post("/{entity}", status_code=201)
def create_record(entity: Entity, payload: dict, user: dict = Depends(_SCOPE)) -> dict:
    return service.save(user, entity, validated(user, entity, payload, False))


@router.patch("/{entity}/{record_id}")
def update_record(entity: Entity, record_id: UUID, payload: dict, user: dict = Depends(_SCOPE)) -> dict:
    return service.save(user, entity, validated(user, entity, payload, True), record_id)
