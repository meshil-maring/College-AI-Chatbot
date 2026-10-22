"""Shared Faculty role dependency, including nested registration routes."""

from app.core.security import require_institution_roles

_FACULTY = require_institution_roles('faculty')
