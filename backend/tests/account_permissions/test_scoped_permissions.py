"""Scope provenance, operation roles and request-time revocation regressions."""

from copy import deepcopy

from app.core.security.dependencies import require_institution_roles
from app.core.security.scoped_permissions import permissions_for_scope

from .support import (
    ACTOR,
    TENANT_A,
    TENANT_B,
    AsyncMock,
    MagicMock,
    SimpleNamespace,
    asyncio,
    get_current_user,
    patch,
    pytest,
    client,
)
from app.main import app


def _grant(role, tenant, permissions, *, scope="institution"):
    return {
        "role": role,
        "scope_type": scope,
        "scope_id": tenant,
        "is_active": True,
        "permissions": permissions,
    }


def _record(grants, direct=()):
    return {
        "user_id": ACTOR,
        "roles": list({g["role"] for g in grants}),
        "status": "active",
        "institution_id": None,
        "role_assignments": grants,
        "direct_permission_grants": list(direct),
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
        "effective_permissions": ["*"],
    }


def _authenticate(record):
    with (
        patch("app.core.security.tokens.verify_jwt", return_value={"sub": "auth"}),
        patch(
            "app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=record)
        ),
    ):
        return asyncio.run(get_current_user("Bearer token"))


def test_identity_does_not_borrow_permissions_from_another_tenant_or_scope():
    record = _record(
        [
            _grant("admin", TENANT_A, ["users.read"]),
            _grant("faculty", TENANT_B, ["documents.create"]),
            _grant("staff", TENANT_A, ["platform.manage"], scope="organization"),
        ]
    )
    assert _authenticate(record)["effective_permissions"] == ["users.read"]


def test_ambiguous_primary_role_scope_has_no_permission_union():
    record = _record(
        [
            _grant("admin", TENANT_A, ["users.read"]),
            _grant("admin", TENANT_B, ["users.update"]),
        ]
    )
    assert _authenticate(record)["effective_permissions"] == []


def test_scope_permissions_restrict_roles_and_direct_staff_grants():
    record = _record(
        [
            _grant("admin", TENANT_A, ["users.read"]),
            _grant("staff", TENANT_A, ["students.read"]),
            _grant("faculty", TENANT_A, ["documents.create"]),
        ],
        [
            {"institution_id": TENANT_A, "permission": "notices.create"},
            {"institution_id": TENANT_B, "permission": "documents.delete"},
        ],
    )
    assert permissions_for_scope(
        record, "institution", TENANT_A, allowed_roles=["admin"]
    ) == ["users.read"]
    assert permissions_for_scope(
        record, "institution", TENANT_A, allowed_roles=["staff"]
    ) == [
        "notices.create",
        "students.read",
    ]


def test_institution_dependency_recalculates_for_its_actual_operation_role():
    record = _record(
        [
            _grant("admin", TENANT_A, ["users.read"]),
            _grant("faculty", TENANT_B, ["documents.create"]),
        ]
    )
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={"status": "active", "is_active": True}
    )
    with patch("app.services.auth.authorization.get_admin_client", return_value=db):
        scoped = asyncio.run(require_institution_roles("faculty")(record))
    assert scoped["institution_id"] == TENANT_B
    assert scoped["effective_permissions"] == ["documents.create"]


@pytest.mark.parametrize("change", ["permission", "role", "direct"])
def test_next_authentication_observes_permission_or_role_revocation(change):
    before = _record(
        [_grant("staff", TENANT_A, ["students.read"])],
        [
            {"institution_id": TENANT_A, "permission": "documents.create"},
        ],
    )
    after = deepcopy(before)
    if change == "permission":
        after["role_assignments"][0]["permissions"] = []
    elif change == "role":
        after["role_assignments"][0]["is_active"] = False
    else:
        after["direct_permission_grants"] = []
    assert _authenticate(before)["effective_permissions"] == [
        "documents.create",
        "students.read",
    ]
    expected = {
        "permission": ["documents.create"],
        "role": [],
        "direct": ["students.read"],
    }
    assert _authenticate(after)["effective_permissions"] == expected[change]


def test_admin_route_cannot_use_faculty_permission_in_the_same_tenant():
    record = _record(
        [
            _grant("admin", TENANT_A, []),
            _grant("faculty", TENANT_A, ["students.read"]),
        ]
    )
    app.dependency_overrides[get_current_user] = lambda: record
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={"status": "active", "is_active": True}
    )
    try:
        with (
            patch("app.services.auth.authorization.get_admin_client", return_value=db),
            patch(
                "app.services.admin.admin_academics.list_pending_approvals"
            ) as pending,
        ):
            response = client.get("/api/v1/admin/students/pending")
        assert response.status_code == 403
        pending.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("provenance", ["missing", None, False, 0, 1, "true", [], {}])
def test_unresolved_scope_never_uses_aggregate_permissions(provenance):
    record = _record([_grant("admin", TENANT_A, ["users.read"])])
    if provenance == "missing":
        record.pop("scoped_permissions_resolved")
    else:
        record["scoped_permissions_resolved"] = provenance
    assert permissions_for_scope(
        record, "institution", TENANT_A, allowed_roles=["admin"]
    ) == []


@pytest.mark.parametrize("scope", ["platform", "organization", "institution"])
def test_exact_scope_grants_ignore_aggregate_and_other_scope_permissions(scope):
    scope_id = None if scope == "platform" else TENANT_A
    other_scope = "organization" if scope != "organization" else "institution"
    record = _record(
        [
            _grant("admin", scope_id, ["users.read"], scope=scope),
            _grant("faculty", scope_id, ["documents.create"], scope=scope),
            _grant("admin", TENANT_B, ["users.delete"], scope=scope),
            _grant("admin", scope_id, ["platform.manage"], scope=other_scope),
        ]
    )
    assert permissions_for_scope(
        record, scope, scope_id, allowed_roles=["admin"]
    ) == ["users.read"]
