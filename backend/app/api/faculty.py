"""Faculty self-service views limited to server-owned active assignments."""

from fastapi import APIRouter, Depends

from app.core.security import authorize_permissions, require_institution_roles
from app.services.phase81_rbac import list_own_faculty_assignments

router = APIRouter(prefix="/faculty", tags=["faculty"])
_FACULTY = require_institution_roles("faculty")


@router.get("/assignments")
def get_my_assignments(
    current_user: dict = Depends(_FACULTY),
) -> list[dict]:
    authorize_permissions(current_user, "faculty.assignments.read")
    return list_own_faculty_assignments(current_user)
