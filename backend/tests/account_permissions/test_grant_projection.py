from .support import (
    ACTOR,
    SimpleNamespace,
    TENANT_A,
    TENANT_B,
    asyncio,
    patch,
    pytest,
    supabase,
)


@pytest.mark.parametrize(
    ("scope_type", "expected_permissions"),
    [
        ("institution", ["faculty.assignments.manage"]),
        ("organization", ["organizations.manage"]),
        ("platform", ["faculty.assignments.manage", "organizations.manage"]),
    ],
)
def test_database_permission_projection_enforces_permission_scope(
    scope_type: str, expected_permissions: list[str]
) -> None:
    row = {
        "user_id": ACTOR,
        "auth_user_id": "auth-actor",
        "email": "actor@example.test",
        "status": "active",
        "user_roles": [
            {
                "scope_type": scope_type,
                "scope_id": TENANT_A,
                "scope_organization_id": TENANT_B
                if scope_type == "organization"
                else None,
                "roles": {
                    "name": "admin",
                    "is_active": True,
                    "role_permissions": [
                        {
                            "permissions": {
                                "code": "faculty.assignments.manage",
                                "scope": "institution",
                                "is_active": True,
                            }
                        },
                        {
                            "permissions": {
                                "code": "organizations.manage",
                                "scope": "organization",
                                "is_active": True,
                            }
                        },
                    ],
                },
            }
        ],
        "user_permission_grants": [
            {
                "institution_id": TENANT_A,
                "revoked_at": None,
                "permissions": {"code": "documents.create", "is_active": True},
            }
        ],
        "students": [],
    }

    class Query:
        def select(self, projection):
            self.projection = projection
            return self

        def eq(self, *_args):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            return SimpleNamespace(data=row)

    query = Query()
    db = SimpleNamespace(table=lambda _name: query)
    with patch("app.db.supabase.get_admin_client", return_value=db):
        resolved = asyncio.run(
            supabase.get_user_by_auth_id("auth-actor", include_permissions=True)
        )
    assert resolved is not None
    assert resolved["effective_permissions"] == expected_permissions
    assert resolved["scoped_permissions_resolved"] is True
    assert resolved["role_assignments"][0]["permissions"] == expected_permissions
    assert resolved["direct_permission_grants"] == [
        {"institution_id": TENANT_A, "permission": "documents.create"}
    ]
    assert (
        "user_permission_grants!user_permission_grants_user_id_fkey("
        in query.projection
    )
