"""Canonical Phase 8 permission catalogue and bootstrap role matrix.

The database is authoritative in production.  ``DEFAULT_ROLE_PERMISSIONS`` is
kept in code for migration/test parity and for dependency-overridden unit tests
that construct an internal ``current_user`` dictionary without executing the
authentication projection.  A real request is marked ``permissions_resolved``
by :func:`app.core.security.get_current_user` and therefore never falls back to
this matrix when database grants are absent or revoked.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.core.permission_defaults import (
    DEFAULT_ROLE_PERMISSIONS,
    DELEGABLE_STAFF_PERMISSIONS,
)

PERMISSIONS: tuple[str, ...] = (
    "registration.own.read",
    "registration.own.manage",
    "courses.read",
    "courses.manage",
    "semesters.read",
    "semesters.manage",
    "departments.read",
    "departments.manage",
    "academic_years.read",
    "academic_years.manage",
    "profile.own.read",
    "profile.own.update",
    "notifications.own.read",
    "notifications.own.update",
    "users.read",
    "users.create",
    "users.update",
    "users.delete",
    "roles.read",
    "roles.manage",
    "permissions.read",
    "permissions.manage",
    "students.read",
    "students.create",
    "students.update",
    "students.delete",
    "students.approve",
    "students.reject",
    "students.suspend",
    "faculty.read",
    "faculty.create",
    "faculty.update",
    "faculty.approve",
    "faculty.suspend",
    "staff.read",
    "staff.create",
    "staff.update",
    "staff.approve",
    "staff.suspend",
    "documents.read",
    "documents.create",
    "documents.update",
    "documents.delete",
    "notices.read",
    "notices.create",
    "notices.update",
    "notices.delete",
    "ai.chat",
    "ai.knowledge.read",
    "ai.knowledge.create",
    "ai.knowledge.update",
    "ai.knowledge.delete",
    "ai.configuration.manage",
    "institution.read",
    "institution.update",
    "institution.settings.manage",
    "organizations.manage",
    "institutions.read",
    "institutions.create",
    "institutions.update",
    "institutions.delete",
    "platform.read",
    "platform.manage",
    "platform.settings.manage",
    "platform.audit.read",
    "audit.read",
)

def permission_matches(granted: Iterable[str], required: str) -> bool:
    """Return whether an exact or ``resource.*`` grant covers ``required``."""
    grants = frozenset(granted)
    if required in grants or "*" in grants:
        return True
    resource, separator, _action = required.partition(".")
    return bool(separator and f"{resource}.*" in grants)


def fallback_permissions_for_roles(roles: Iterable[str]) -> frozenset[str]:
    """Union defaults only for dependency-overridden/internal test contexts."""
    result: set[str] = set()
    for role in roles:
        result.update(DEFAULT_ROLE_PERMISSIONS.get(role, ()))
    return frozenset(result)
