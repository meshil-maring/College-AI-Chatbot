"""Organization and institution foundation regressions: scope management."""

from __future__ import annotations

from .support import (
    INST_A1,
    INST_A2,
    INST_B1,
    MagicMock,
    ORG_A,
    ORG_B,
    USER_ID,
    UUID,
    _context,
    _expect,
    authz,
    patch,
    tenancy_repo,
)


def test_org_admin_can_manage_its_own_organization() -> None:
    authz.assert_can_manage_organization(
        {"user_id": USER_ID},
        _context(scope_type=authz.ORGANIZATION, organization_id=ORG_A),
        ORG_A,
    )


def test_org_admin_cannot_manage_another_organization() -> None:
    _expect(
        "ORGANIZATION_MISMATCH",
        authz.assert_can_manage_organization,
        {"user_id": USER_ID},
        _context(scope_type=authz.ORGANIZATION, organization_id=ORG_A),
        ORG_B,
    )


def test_institution_admin_cannot_manage_its_own_organization() -> None:
    """Institution admins manage THEIR institution, never the organization."""
    _expect(
        "FORBIDDEN",
        authz.assert_can_manage_organization,
        {"user_id": USER_ID},
        _context(
            scope_type=authz.INSTITUTION,
            organization_id=ORG_A,
            institution_id=INST_A1,
        ),
        ORG_A,
    )


def test_non_admins_can_manage_neither_organization_nor_institution() -> None:
    staff = _context(
        role="staff",
        scope_type=authz.INSTITUTION,
        organization_id=ORG_A,
        institution_id=INST_A1,
    )
    _expect(
        "FORBIDDEN",
        authz.assert_can_manage_organization,
        {"user_id": USER_ID},
        staff,
        ORG_A,
    )
    _expect(
        "FORBIDDEN",
        authz.assert_can_manage_institution,
        {"user_id": USER_ID},
        staff,
        INST_A1,
    )


def test_platform_scope_keeps_its_unrestricted_authority() -> None:
    platform = _context(scope_type=authz.PLATFORM)
    authz.assert_can_manage_organization({"user_id": USER_ID}, platform, ORG_B)
    authz.assert_can_manage_institution({"user_id": USER_ID}, platform, INST_B1)


def test_org_admin_manages_only_institutions_of_its_own_organization() -> None:
    context = _context(scope_type=authz.ORGANIZATION, organization_id=ORG_A)
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        authz.assert_can_manage_institution({"user_id": USER_ID}, context, INST_A1)

    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_B)
        ),
    ):
        _expect(
            "ORGANIZATION_MISMATCH",
            authz.assert_can_manage_institution,
            {"user_id": USER_ID},
            context,
            INST_B1,
        )


def test_institution_admin_manages_only_its_own_institution() -> None:
    context = _context(
        scope_type=authz.INSTITUTION,
        organization_id=ORG_A,
        institution_id=INST_A1,
    )
    authz.assert_can_manage_institution({"user_id": USER_ID}, context, INST_A1)
    _expect(
        "TENANT_MISMATCH",
        authz.assert_can_manage_institution,
        {"user_id": USER_ID},
        context,
        INST_A2,
    )
    _expect(
        "TENANT_MISMATCH",
        authz.assert_can_manage_institution,
        {"user_id": USER_ID},
        context,
        INST_B1,
    )


def test_org_b_admin_cannot_manage_org_a_institutions() -> None:
    context = _context(scope_type=authz.ORGANIZATION, organization_id=ORG_B)
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        _expect(
            "ORGANIZATION_MISMATCH",
            authz.assert_can_manage_institution,
            {"user_id": USER_ID},
            context,
            INST_A1,
        )
