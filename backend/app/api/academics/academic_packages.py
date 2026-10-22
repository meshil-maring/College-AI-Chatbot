"""Academic package setup and student choices with server-resolved scope."""

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.core.errors import AppError
from app.core.security import require_institution_roles
from app.schemas.academics.academic_packages import COMMAND_MODELS, validate_command
from app.services.academics import academic_packages as service

router = APIRouter(prefix="/academic-packages", tags=["academic-packages"])
_SCOPE = require_institution_roles("admin", "staff", "faculty", "student")


@router.get("")
def get_catalogue(user: dict = Depends(_SCOPE)) -> dict:
    return service.catalogue(user)


@router.post("/{operation}")
def execute_command(operation: str, payload: dict,
                    user: dict = Depends(_SCOPE)) -> dict:
    if operation not in COMMAND_MODELS:
        raise AppError("Unknown academic package operation", 404,
                       "ACADEMIC_PACKAGE_OPERATION_UNKNOWN")
    try:
        validated = validate_command(operation, payload)
    except ValidationError as error:
        raise AppError("Check the academic package fields and values", 422,
                       "ACADEMIC_PACKAGE_INPUT_INVALID") from error
    return service.command(user, operation, validated)
