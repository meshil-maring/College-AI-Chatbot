"""Organization and institution foundation regressions: scope resolution."""

from __future__ import annotations

from .support import (
    INST_A1,
    MagicMock,
    ORG_A,
    ORG_B,
    USER_ID,
    UUID,
    authz,
    patch,
    tenancy_repo,
)


def test_resolve_authorization_context_links_user_to_organization_and_institution() -> None:
    """JWT sub -> users.id -> user_roles.user_id (+scope) -> institution -> organization."""
    rows = [
        {
            "role_id": "e0000000-0000-0000-0000-000000000001",
            "role_name": "admin",
            "is_active": True,
            "scope_type": "institution",
            "scope_id": INST_A1,
            "scope_organization_id": ORG_A,
        }
    ]
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ) as resolver,
    ):
        context = authz.resolve_authorization_context(
            {"user_id": USER_ID, "institution_id": None}
        )

    assert context["roles"] == ["admin"]
    assert context["scope_type"] == "institution"
    assert context["scope_id"] == INST_A1
    assert context["institution_id"] == INST_A1
    assert context["organization_id"] == ORG_A
    resolver.assert_called_once()


def test_resolve_authorization_context_prefers_the_widest_privilege_scope() -> None:
    rows = [
        {
            "role_name": "faculty",
            "is_active": True,
            "scope_type": "institution",
            "scope_id": INST_A1,
            "scope_organization_id": ORG_A,
        },
        {
            "role_name": "admin",
            "is_active": True,
            "scope_type": "organization",
            "scope_id": ORG_A,
            "scope_organization_id": ORG_A,
        },
    ]
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
    ):
        context = authz.resolve_authorization_context(
            {"user_id": USER_ID, "institution_id": INST_A1}
        )

    assert context["scope_type"] == "organization"
    assert context["scope_id"] == ORG_A
    assert context["organization_id"] == ORG_A
    assert set(context["roles"]) == {"admin", "faculty"}


def test_organization_scope_is_taken_from_the_database_not_the_request() -> None:
    """A client-injected organization/scope id is never trusted."""
    rows = [
        {
            "role_name": "student",
            "is_active": True,
            "scope_type": None,
            "scope_id": None,
            "scope_organization_id": None,
        }
    ]
    client_supplied = {
        "user_id": USER_ID,
        "institution_id": INST_A1,
        # Attacker-controlled fields that must be ignored:
        "scope_type": "organization",
        "scope_id": ORG_B,
        "organization_id": ORG_B,
    }
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        context = authz.resolve_authorization_context(client_supplied)

    # Resolved server-side: the student's own institution (A1) inside org A.
    assert context["scope_id"] == INST_A1
    assert context["organization_id"] == ORG_A
    assert context["scope_id"] != ORG_B
    assert context["organization_id"] != ORG_B


def test_institution_scope_organization_comes_from_the_institution_row() -> None:
    """A stale/hostile denormalised scope_organization_id cannot widen the scope."""
    rows = [
        {
            "role_name": "admin",
            "is_active": True,
            "scope_type": "institution",
            "scope_id": INST_A1,
            "scope_organization_id": ORG_B,
        }
    ]
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        context = authz.resolve_authorization_context(
            {"user_id": USER_ID, "institution_id": None}
        )

    assert context["organization_id"] == ORG_A
    assert context["scope_id"] == INST_A1
