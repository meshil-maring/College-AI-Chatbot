"""Principals."""

from __future__ import annotations

from app.main import app

from fastapi.testclient import TestClient


client = TestClient(app, raise_server_exceptions=False)


INST_A = "72400000-0000-0000-0000-00000000000a"


INST_B = "72400000-0000-0000-0000-00000000000b"


STAFF_A = "72500000-0000-0000-0000-00000000000a"


FACULTY_A = "72500000-0000-0000-0000-00000000000b"


ADMIN_A = "72500000-0000-0000-0000-00000000000c"


STUDENT_A = "72500000-0000-0000-0000-00000000000d"


SUPER_ADMIN = "72500000-0000-0000-0000-00000000000e"


STUDENT_A_ROW = "72600000-0000-0000-0000-00000000000a"


STUDENT_B_ROW = "72600000-0000-0000-0000-00000000000b"


KNOWLEDGE_SOURCE_A = "72700000-0000-0000-0000-00000000000a"


KNOWLEDGE_SOURCE_B = "72700000-0000-0000-0000-00000000000b"


AUTH_HEADERS = {"Authorization": "Bearer phase724.token"}


STAFF_OR_FACULTY = ("staff", "faculty")


def _grant(role: str, institution_id: str | None) -> dict:
    return {
        "role": role,
        "scope_type": "institution" if institution_id else "platform",
        "scope_id": institution_id,
        "scope_organization_id": None,
        "is_active": True,
    }


def _principal(
    user_id: str,
    role: str,
    institution_id: str | None,
    *,
    status: str = "active",
) -> dict:
    """A principal shaped exactly like ``get_current_user`` after Phase 7.20.

    The top-level ``institution_id`` is deliberately ``None``: the dependency
    must re-derive the tenant from ``role_assignments.scope_id`` and must
    never trust a client-controlled tenant.
    """
    return {
        "user_id": user_id,
        "auth_user_id": user_id,
        "email": f"{role}@example.edu",
        "status": status,
        "roles": [role],
        "institution_id": None,
        "role_assignments": [_grant(role, institution_id)],
    }


STAFF_A_USER = _principal(STAFF_A, "staff", INST_A)


FACULTY_A_USER = _principal(FACULTY_A, "faculty", INST_A)


ADMIN_A_USER = _principal(ADMIN_A, "admin", INST_A)


STUDENT_A_USER = _principal(STUDENT_A, "student", INST_A)


SUPER_ADMIN_USER = _principal(SUPER_ADMIN, "super_admin", None)


DEACTIVATED_STAFF_USER = _principal(STAFF_A, "staff", INST_A, status="deactivated")


DEACTIVATED_FACULTY_USER = _principal(
    FACULTY_A, "faculty", INST_A, status="deactivated"
)


STAFF_AND_FACULTY_USERS = [(STAFF_A_USER, "staff"), (FACULTY_A_USER, "faculty")]
