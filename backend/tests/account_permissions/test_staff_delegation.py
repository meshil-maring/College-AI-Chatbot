from .support import (
    ACTOR,
    AppError,
    AsyncMock,
    DELEGABLE_STAFF_PERMISSIONS,
    MagicMock,
    TARGET,
    TENANT_A,
    TENANT_B,
    UUID,
    _resolved_user,
    asyncio,
    get_current_user,
    patch,
    phase81_rbac,
    pytest,
)


@pytest.mark.parametrize(
    ("role", "grants", "scope", "expected"),
    [
        (
            "staff",
            [{"institution_id": TENANT_A, "permission": "documents.create"}],
            TENANT_A,
            ["documents.create"],
        ),
        (
            "staff",
            [{"institution_id": TENANT_B, "permission": "documents.create"}],
            TENANT_A,
            [],
        ),
        (
            "admin",
            [{"institution_id": TENANT_A, "permission": "documents.create"}],
            TENANT_A,
            [],
        ),
    ],
)
def test_direct_staff_grants_require_matching_active_staff_institution_scope(
    role: str, grants: list[dict], scope: str, expected: list[str]
) -> None:
    user_record = {
        "user_id": ACTOR,
        "auth_user_id": "auth-actor",
        "email": "actor@example.test",
        "status": "active",
        "roles": [role],
        "institution_id": None,
        "student_institution_id": None,
        "role_assignments": [
            {
                "role": role,
                "scope_type": "institution",
                "scope_id": scope,
                "scope_organization_id": None,
                "is_active": True,
                "permissions": [],
            }
        ],
        "effective_permissions": [],
        "direct_permission_grants": grants,
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
    }
    with (
        patch(
            "app.core.security.tokens.verify_jwt", return_value={"sub": "auth-actor"}
        ),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(return_value=user_record),
        ),
    ):
        resolved = asyncio.run(get_current_user("Bearer token"))
    assert resolved["effective_permissions"] == expected


def test_staff_permission_api_rejects_non_delegable_permission_before_rpc() -> None:
    with pytest.raises(AppError) as error:
        phase81_rbac.change_staff_permissions(
            _resolved_user("admin", ["permissions.manage"]),
            UUID(TENANT_A),
            UUID(TARGET),
            ["platform.manage"],
            grant=True,
        )
    assert error.value.code == "PERMISSION_NOT_DELEGABLE"


def test_staff_permission_api_requires_staff_target_in_same_institution() -> None:
    with (
        patch(
            "app.services.auth.phase81_rbac._staff_member",
            side_effect=AppError(
                "Active Staff member not found", 404, "STAFF_MEMBER_NOT_FOUND"
            ),
        ),
        patch("app.services.auth.phase81_rbac.get_admin_client") as get_client,
    ):
        with pytest.raises(AppError) as error:
            phase81_rbac.change_staff_permissions(
                _resolved_user("admin", ["permissions.manage"]),
                UUID(TENANT_A),
                UUID(TARGET),
                ["documents.create"],
                grant=True,
            )
    assert error.value.code == "STAFF_MEMBER_NOT_FOUND"
    get_client.assert_not_called()


def test_staff_grant_mutation_uses_atomic_rpc_and_returns_effective_sources() -> None:
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = 1
    expected = {
        "user_id": TARGET,
        "institution_id": TENANT_A,
        "permissions": [],
        "delegable_permissions": ["documents.create"],
    }
    with (
        patch(
            "app.services.auth.phase81_rbac._staff_member", return_value={"id": TARGET}
        ),
        patch("app.services.auth.phase81_rbac.get_admin_client", return_value=db),
        patch(
            "app.services.auth.phase81_rbac.list_staff_permissions",
            return_value=expected,
        ),
    ):
        result = phase81_rbac.change_staff_permissions(
            _resolved_user("admin", ["permissions.manage"]),
            UUID(TENANT_A),
            UUID(TARGET),
            ["documents.create"],
            grant=True,
        )
    db.rpc.assert_called_once_with(
        "phase81_manage_staff_permission_grants",
        {
            "p_actor_user_id": ACTOR,
            "p_institution_id": TENANT_A,
            "p_target_user_id": TARGET,
            "p_permission_codes": ["documents.create"],
            "p_grant": True,
        },
    )
    assert result["changed"] == 1
    assert result["permissions"] == expected


def test_staff_permission_catalogue_is_narrow_and_never_platform_administrative() -> (
    None
):
    assert DELEGABLE_STAFF_PERMISSIONS
    assert not any(
        code.startswith(
            ("platform.", "institutions.", "roles.", "permissions.", "users.")
        )
        for code in DELEGABLE_STAFF_PERMISSIONS
    )
