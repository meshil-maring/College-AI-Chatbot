"""Authentication identity regressions: projection."""

from __future__ import annotations

from .support import (
    FAKE_CLAIMS,
    MagicMock,
    client,
    get_user_by_auth_id,
    patch,
    pytest,
)


@pytest.mark.asyncio
async def test_get_user_by_auth_id_uses_actual_users_schema():
    client = MagicMock()
    users_table = client.table.return_value
    users_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "status": "active",
        "user_roles": [
            {
                "scope_type": "institution",
                "scope_id": "30000000-0000-0000-0000-000000000001",
                "scope_organization_id": None,
                "roles": {"name": "student", "is_active": True},
            },
            {"roles": {"name": "disabled", "is_active": False}},
        ],
        "students": [
            {"institution_id": "30000000-0000-0000-0000-000000000001"},
        ],
    }

    with patch("app.db.supabase.get_admin_client", return_value=client):
        result = await get_user_by_auth_id(FAKE_CLAIMS["sub"])

    assert result == {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "status": "active",
        "roles": ["student"],
        "institution_id": "30000000-0000-0000-0000-000000000001",
        "student_institution_id": "30000000-0000-0000-0000-000000000001",
        "role_assignments": [
            {
                "role": "student",
                "scope_type": "institution",
                "scope_id": "30000000-0000-0000-0000-000000000001",
                "scope_organization_id": None,
                "is_active": True,
                "permissions": [],
            }
        ],
    }
    users_table.select.assert_called_once_with(
        "user_id:id, auth_user_id, email, status, "
        "user_roles(scope_type, scope_id, scope_organization_id, "
        "roles(name, is_active)), "
        "students(institution_id)"
    )
    users_table.select.return_value.eq.assert_called_once_with(
        "auth_user_id", FAKE_CLAIMS["sub"]
    )


@pytest.mark.asyncio
async def test_get_user_by_auth_id_without_student_profile_has_no_tenant():
    """Platform-level accounts (no students row) resolve to institution_id=None."""
    client = MagicMock()
    users_table = client.table.return_value
    users_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "user_id": "30000000-0000-0000-0000-000000000102",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "status": "active",
        "user_roles": [
            {
                "scope_type": "platform",
                "scope_id": None,
                "scope_organization_id": None,
                "roles": {"name": "admin", "is_active": True},
            },
        ],
        "students": [],
    }

    with patch("app.db.supabase.get_admin_client", return_value=client):
        result = await get_user_by_auth_id(FAKE_CLAIMS["sub"])

    assert result["institution_id"] is None


@pytest.mark.asyncio
async def test_get_user_by_auth_id_handles_one_to_one_students_object():
    """Regression: PostgREST embeds the students relation as a single OBJECT
    (not a list) when the FK is detected as one-to-one. This is what the live
    Supabase schema returns and previously crashed with ``KeyError: 0``.
    """
    client = MagicMock()
    users_table = client.table.return_value
    users_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "user_id": "30000000-0000-0000-0000-000000000103",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "status": "active",
        "user_roles": [
            {
                "scope_type": "institution",
                "scope_id": "30000000-0000-0000-0000-000000000001",
                "scope_organization_id": None,
                "roles": {"name": "student", "is_active": True},
            },
        ],
        "students": {
            "institution_id": "30000000-0000-0000-0000-000000000001",
        },
    }

    with patch("app.db.supabase.get_admin_client", return_value=client):
        result = await get_user_by_auth_id(FAKE_CLAIMS["sub"])

    assert result == {
        "user_id": "30000000-0000-0000-0000-000000000103",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "status": "active",
        "roles": ["student"],
        "institution_id": "30000000-0000-0000-0000-000000000001",
        "student_institution_id": "30000000-0000-0000-0000-000000000001",
        "role_assignments": [
            {
                "role": "student",
                "scope_type": "institution",
                "scope_id": "30000000-0000-0000-0000-000000000001",
                "scope_organization_id": None,
                "is_active": True,
                "permissions": [],
            }
        ],
    }
