"""Bootstrap role defaults and the narrow staff delegation catalogue.

Runtime authorization remains database-authoritative; these defaults support
migrations, generated reference policy and dependency-overridden tests.
"""

_UNIVERSITY_ADMIN = frozenset(
    {
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
        "institution.read",
        "institution.update",
        "institution.settings.manage",
        "users.read",
        "users.create",
        "users.update",
        "organizations.manage",
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
        "audit.read",
    }
)

DEFAULT_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    # Platform permissions are deliberately explicit: super_admin is not
    # implicitly entitled to tenant academic data.
    "super_admin": frozenset(
        {
            "profile.own.read",
            "platform.read",
            "platform.manage",
            "platform.settings.manage",
            "platform.audit.read",
            "institutions.read",
            "institutions.create",
            "institutions.update",
            "institutions.delete",
            "users.read",
            "users.create",
            "users.update",
            "users.delete",
            "roles.read",
            "roles.manage",
            "permissions.read",
            "permissions.manage",
            "audit.read",
        }
    ),
    "university_admin": _UNIVERSITY_ADMIN,
    "admin": _UNIVERSITY_ADMIN
    | {"platform.manage"},  # legacy platform scope is still scope-checked
    "faculty": frozenset(
        {
            "profile.own.read",
            "profile.own.update",
            "notifications.own.read",
            "notifications.own.update",
            "ai.chat",
            "ai.knowledge.read",
            "ai.knowledge.create",
            "students.read",
            "documents.read",
            "documents.create",
            "notices.read",
        }
    ),
    # Staff is intentionally conservative; institution admins can configure
    # additional job-function grants through role/direct permission management.
    "staff": frozenset(
        {
            "profile.own.read",
            "profile.own.update",
            "notifications.own.read",
            "notifications.own.update",
            "ai.chat",
            "ai.knowledge.create",
            "students.read",
            "students.update",
            "students.approve",
            "students.reject",
            "documents.read",
            "documents.create",
            "documents.update",
            "notices.read",
            "notices.create",
            "notices.update",
        }
    ),
    "student": frozenset(
        {
            "registration.own.read",
            "registration.own.manage",
            "profile.own.read",
            "profile.own.update",
            "notifications.own.read",
            "notifications.own.update",
            "ai.chat",
            "documents.read",
            "notices.read",
        }
    ),
}

DELEGABLE_STAFF_PERMISSIONS: frozenset[str] = frozenset(
    {
        "ai.knowledge.create",
        "students.read",
        "students.update",
        "documents.read",
        "documents.create",
        "documents.update",
        "notices.read",
        "notices.create",
        "notices.update",
    }
)
