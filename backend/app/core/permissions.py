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

PERMISSIONS: tuple[str, ...] = (
    "profile.own.read", "profile.own.update",
    "notifications.own.read", "notifications.own.update",
    "users.read", "users.create", "users.update", "users.delete",
    "roles.read", "roles.manage", "permissions.read", "permissions.manage",
    "students.read", "students.create", "students.update", "students.delete",
    "students.approve", "students.reject", "students.suspend",
    "faculty.read", "faculty.create", "faculty.update", "faculty.approve", "faculty.suspend",
    "staff.read", "staff.create", "staff.update", "staff.approve", "staff.suspend",
    "departments.read", "departments.manage", "courses.read", "courses.manage",
    "subjects.read", "subjects.manage", "semesters.read", "semesters.manage",
    "academic_years.read", "academic_years.manage",
    "attendance.read", "attendance.manage", "attendance.own.read",
    "results.read", "results.manage", "results.own.read",
    "documents.read", "documents.create", "documents.update", "documents.delete",
    "notices.read", "notices.create", "notices.update", "notices.delete",
    "ai.chat", "ai.knowledge.read", "ai.knowledge.create", "ai.knowledge.update",
    "ai.knowledge.delete", "ai.configuration.manage",
    "institution.read", "institution.update", "institution.settings.manage",
    "organizations.manage", "faculty.assignments.read", "faculty.assignments.manage",
    "institutions.read", "institutions.create", "institutions.update", "institutions.delete",
    "platform.read", "platform.manage", "platform.settings.manage", "platform.audit.read",
    "audit.read",
)

_UNIVERSITY_ADMIN = frozenset({
    "profile.own.read", "profile.own.update", "institution.read", "institution.update",
    "institution.settings.manage", "users.read", "users.create", "users.update",
    "organizations.manage", "faculty.assignments.manage",
    "roles.read", "roles.manage", "permissions.read", "permissions.manage",
    "students.read", "students.create", "students.update", "students.delete",
    "students.approve", "students.reject", "students.suspend",
    "faculty.read", "faculty.create", "faculty.update", "faculty.approve", "faculty.suspend",
    "staff.read", "staff.create", "staff.update", "staff.approve", "staff.suspend",
    "departments.read", "departments.manage", "courses.read", "courses.manage",
    "subjects.read", "subjects.manage", "semesters.read", "semesters.manage",
    "academic_years.read", "academic_years.manage", "attendance.read", "attendance.manage",
    "results.read", "results.manage", "documents.read", "documents.create",
    "documents.update", "documents.delete", "notices.read", "notices.create",
    "notices.update", "notices.delete", "ai.chat", "ai.knowledge.read",
    "ai.knowledge.create", "ai.knowledge.update", "ai.knowledge.delete", "audit.read",
})

DEFAULT_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    # Platform permissions are deliberately explicit: super_admin is not
    # implicitly entitled to tenant academic data.
    "super_admin": frozenset({
        "profile.own.read", "platform.read", "platform.manage",
        "platform.settings.manage", "platform.audit.read", "institutions.read",
        "institutions.create", "institutions.update", "institutions.delete",
        "users.read", "users.create", "users.update", "users.delete",
        "roles.read", "roles.manage", "permissions.read", "permissions.manage",
        "audit.read",
    }),
    "university_admin": _UNIVERSITY_ADMIN,
    "admin": _UNIVERSITY_ADMIN | {"platform.manage"},  # legacy platform scope is still scope-checked
    "faculty": frozenset({
        "profile.own.read", "profile.own.update", "notifications.own.read",
        "notifications.own.update", "ai.chat", "ai.knowledge.read",
        "ai.knowledge.create",
        "faculty.assignments.read",
        "students.read", "attendance.read", "attendance.manage", "attendance.own.read",
        "results.read", "results.manage", "results.own.read", "documents.read",
        "documents.create", "notices.read",
    }),
    # Staff is intentionally conservative; institution admins can configure
    # additional job-function grants through role/direct permission management.
    "staff": frozenset({
        "profile.own.read", "profile.own.update", "notifications.own.read",
        "notifications.own.update", "ai.chat", "ai.knowledge.create",
        "students.read",
        "students.update", "students.approve", "students.reject", "attendance.read",
        "attendance.manage", "results.read", "documents.read", "documents.create",
        "documents.update", "notices.read", "notices.create", "notices.update",
    }),
    "student": frozenset({
        "profile.own.read", "profile.own.update", "notifications.own.read",
        "notifications.own.update", "ai.chat", "attendance.own.read",
        "results.own.read", "documents.read", "notices.read",
    }),
}

DELEGABLE_STAFF_PERMISSIONS: frozenset[str] = frozenset({
    "ai.knowledge.create",
    "attendance.read", "attendance.manage",
    "results.read", "results.manage",
    "students.read", "students.update",
    "documents.read", "documents.create", "documents.update",
    "notices.read", "notices.create", "notices.update",
})


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
