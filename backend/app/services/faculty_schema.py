"""Report pending faculty migrations without exposing database diagnostics."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from postgrest.exceptions import APIError

from app.core.errors import AppError

logger = logging.getLogger(__name__)
P = ParamSpec("P")
R = TypeVar("R")

_SCHEMA_OBJECTS = (
    "responsibility_definitions", "responsibility_permissions",
    "faculty_responsibilities", "faculty_section_assignments",
    "manage_faculty_responsibility", "update_faculty_teaching_validity",
    "create_faculty_teaching_assignment", "phase81_manage_faculty_section_assignment",
    "manage_scoped_faculty_teaching_assignment",
)
_MISSING_SCHEMA_CODES = {
    "PGRST200", "PGRST202", "PGRST204", "PGRST205", "42P01", "42703", "42883",
}


def faculty_schema_required(operation: Callable[P, R]) -> Callable[P, R]:
    @wraps(operation)
    def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return operation(*args, **kwargs)
        except APIError as error:
            if error.code not in _MISSING_SCHEMA_CODES or not any(
                name in error.message for name in _SCHEMA_OBJECTS
            ):
                raise
            logger.warning(
                "event=faculty_schema_unavailable database_code=%s "
                "required_migration=20261011000000_faculty_responsibilities_and_validity.sql",
                error.code,
            )
            raise AppError(
                "Faculty assignments and responsibilities are unavailable until the database update is applied. "
                "Please contact your administrator.",
                503,
                "FACULTY_SCHEMA_UNAVAILABLE",
            ) from error

    return guarded
