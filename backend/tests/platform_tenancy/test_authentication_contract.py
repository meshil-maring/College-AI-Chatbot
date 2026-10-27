"""Organization and institution foundation regressions: authentication contract."""

from __future__ import annotations

from .support import (
    AppError,
    AsyncMock,
    INST_A1,
    ORG_A,
    USER_ID,
    asyncio,
    get_current_user,
    patch,
    pytest,
    require_roles,
)


def test_get_current_user_projects_the_authoritative_contract() -> None:
    """Phase 7.20: auth projects server-owned role grants for scoped authorization.

    The projection now carries the account lifecycle plus the ``user_roles``
    grant rows so downstream institution-scoped dependencies can resolve an
    authoritative tenant. A non-student institution binding is derived ONLY from
    the primary role's institution grant - never from a client field or from an
    unrelated student profile.
    """
    with pytest.raises(AppError) as excinfo:
        asyncio.run(get_current_user(None))
    assert (excinfo.value.status_code, excinfo.value.code) == (401, "AUTH_REQUIRED")

    with (
        patch(
            "app.core.security.tokens.verify_jwt",
            return_value={"sub": "auth-1", "email": "user@example.com"},
        ),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(
                return_value={
                    "user_id": USER_ID,
                    "auth_user_id": "auth-1",
                    "email": "user@example.com",
                    "status": "active",
                    "roles": ["admin"],
                    # No student profile: the tenant must come from user_roles.
                    "institution_id": None,
                    "student_institution_id": None,
                    "role_assignments": [
                        {
                            "role": "admin",
                            "scope_type": "institution",
                            "scope_id": INST_A1,
                            "scope_organization_id": ORG_A,
                            "is_active": True,
                            "permissions": [],
                        }
                    ],
                    "effective_permissions": [],
                    "permissions_resolved": True,
                    "scoped_permissions_resolved": True,
                    "direct_permission_grants": [],
                }
            ),
        ),
    ):
        current_user = asyncio.run(get_current_user("Bearer test.token"))

    assert current_user == {
        "user_id": USER_ID,
        "auth_user_id": "auth-1",
        "email": "user@example.com",
        "roles": ["admin"],
        "status": "active",
        "institution_id": INST_A1,
        "role_assignments": [
            {
                "role": "admin",
                "scope_type": "institution",
                "scope_id": INST_A1,
                "scope_organization_id": ORG_A,
                "is_active": True,
                "permissions": [],
            }
        ],
        "effective_permissions": [],
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
        "direct_permission_grants": [],
        "auth_methods": [],
        "auth_session_id": None,
        "token_issued_at": None,
    }


def test_require_roles_is_unchanged_by_the_scope_extension() -> None:
    dependency = require_roles("admin")
    institution_admin = {
        "user_id": USER_ID,
        "roles": ["admin"],
        "institution_id": INST_A1,
    }
    # An institution-scoped admin still passes role-based RBAC; narrowing is
    # enforced by the Phase 6.13 authorization layer, not by require_roles().
    assert asyncio.run(dependency(institution_admin)) is institution_admin

    with pytest.raises(AppError) as excinfo:
        asyncio.run(dependency({"user_id": USER_ID, "roles": ["student"]}))
    assert (excinfo.value.status_code, excinfo.value.code) == (403, "FORBIDDEN")
