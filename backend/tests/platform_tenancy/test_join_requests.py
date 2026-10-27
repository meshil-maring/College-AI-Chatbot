"""Organization and institution foundation regressions: join requests."""

from __future__ import annotations

from .support import (
    INST_A1,
    ORG_A,
    ORG_B,
    _context,
    _expect,
    authz,
)


def test_institution_scoped_account_can_never_decide_join_requests() -> None:
    """Approving an institution join is the EXCLUSIVE right of the org admin."""
    context = _context(
        scope_type=authz.INSTITUTION,
        organization_id=ORG_A,
        institution_id=INST_A1,
    )
    _expect(
        "ORGANIZATION_MISMATCH",
        authz.assert_can_decide_join_request,
        context,
        {"organization_id": ORG_A, "institution_id": INST_A1},
    )


def test_join_request_decisions_are_limited_to_the_owning_organization() -> None:
    context = _context(scope_type=authz.ORGANIZATION, organization_id=ORG_A)
    authz.assert_can_decide_join_request(context, {"organization_id": ORG_A})
    _expect(
        "ORGANIZATION_MISMATCH",
        authz.assert_can_decide_join_request,
        context,
        {"organization_id": ORG_B},
    )


def test_join_request_decision_requires_the_admin_role() -> None:
    _expect(
        "FORBIDDEN",
        authz.assert_can_decide_join_request,
        _context(role="faculty", scope_type=authz.ORGANIZATION, organization_id=ORG_A),
        {"organization_id": ORG_A},
    )


def test_platform_admin_can_decide_any_join_request() -> None:
    authz.assert_can_decide_join_request(
        _context(scope_type=authz.PLATFORM), {"organization_id": ORG_A}
    )


def test_assert_institution_in_organization_rejects_cross_organization() -> None:
    authz.assert_institution_in_organization(ORG_A, ORG_A)
    _expect(
        "ORGANIZATION_MISMATCH", authz.assert_institution_in_organization, ORG_A, ORG_B
    )
    _expect(
        "ORGANIZATION_MISMATCH", authz.assert_institution_in_organization, None, ORG_A
    )
    _expect(
        "ORGANIZATION_MISMATCH", authz.assert_institution_in_organization, ORG_A, None
    )
