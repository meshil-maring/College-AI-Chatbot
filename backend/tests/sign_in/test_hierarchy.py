"""Test hierarchy."""

from __future__ import annotations

from app.core.errors import AppError

from app.services.auth.student_auth import SafeAuthFailure

from uuid import UUID, uuid4

import pytest

from .credentials import (
    assert_login_failure,
    login_api,
)

from .identity import (
    _active_institution_authorization,
)

from .support import (
    INSTITUTION_A,
    ORGANIZATION_ID,
    STAFF_EMAIL,
    institution_db,
    sign_in_account,
)


def test_25a_phase_6_13_1_hierarchy_guard_unchanged():
    """organization <-> institution consistency is still enforced server-side."""
    from app.services.auth.authorization import assert_institution_in_organization

    # Same organization -> allowed.
    assert_institution_in_organization(ORGANIZATION_ID, ORGANIZATION_ID)

    # Cross-organization -> ORGANIZATION_MISMATCH (defense in depth).
    with pytest.raises(AppError) as exc:
        assert_institution_in_organization(ORGANIZATION_ID, uuid4())
    assert exc.value.status_code == 403
    assert exc.value.code == "ORGANIZATION_MISMATCH"

    # Missing side -> denied (never silently allowed).
    with pytest.raises(AppError):
        assert_institution_in_organization(None, ORGANIZATION_ID)


def test_25b_phase_6_13_3_scope_accessors_unchanged():
    """Organization/institution ids are extracted from the resolved context."""
    from app.services.auth.authorization import (
        user_institution_id,
        user_organization_id,
    )

    context = {
        "organization_id": str(ORGANIZATION_ID),
        "institution_id": str(INSTITUTION_A),
    }
    assert user_organization_id(context) == ORGANIZATION_ID
    assert user_institution_id(context) == INSTITUTION_A
    assert user_organization_id({}) is None
    assert user_institution_id({"institution_id": None}) is None


def test_25c_phase_6_13_5_registration_gate_semantics_unchanged():
    """Registration still denies non-ACTIVE institutions (Phase 6.13.5 gate).

    The sign-in gate (Phase 6.13.6) reuses the SAME status semantics: a
    non-active institution carries ``is_active = False`` (trigger-derived), so
    both boundaries deny — registration with 403
    INSTITUTION_NOT_ACCEPTING_REGISTRATIONS, sign-in with 401
    INVALID_CREDENTIALS (anti-enumeration).
    """
    from app.services.platform.tenancy import (
        _assert_institution_active as registration_gate,
    )

    registration_gate({"status": "active", "is_active": True})  # allowed

    for status in ("pending", "rejected", "inactive"):
        with pytest.raises(AppError) as exc:
            registration_gate({"status": status, "is_active": False})
        assert exc.value.status_code == 403
        assert exc.value.code == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"

    # The sign-in gate reuses the Phase 6.5 checker on the same rows.
    from app.services.auth.student_auth import (
        _assert_institution_active as sign_in_gate,
    )

    with pytest.raises(SafeAuthFailure):
        sign_in_gate(institution_db(is_active=False), INSTITUTION_A)


def test_25d_phase_6_13_5_role_map_unchanged_no_new_roles():
    """Self-registration still grants only student/faculty/staff — no new
    roles were invented by Phase 6.13.6."""
    from app.services.auth.user_registration import ROLE_MAP

    assert ROLE_MAP == {"student": "student", "faculty": "faculty", "staff": "staff"}
    assert "admin" not in ROLE_MAP.values()


def test_25e_phase_6_13_6_single_status_seam():
    """No duplicate status logic: the sign-in guard reuses the Phase 6.5
    institution checker and defines only the 'active' literal it needs."""
    import app.services.auth.sign_in as sign_in

    assert sign_in.ACTIVE == "active"
    assert sign_in._assert_institution_active is (
        __import__(
            "app.services.auth.student_auth", fromlist=["_assert_institution_active"]
        )._assert_institution_active
    )


def test_25f_phase_6_13_5_student_login_still_requires_registered_identity():
    """A registration created in Phase 6.13.5 (pending) cannot log in until
    approved — the two phases agree on the same server-side records."""
    pending = sign_in_account(
        institution_id=str(INSTITUTION_A),
        approval_status="pending",
        student_is_active=True,
    )
    assert_login_failure(login_api(account=pending))

    # A students row missing entirely (faculty/staff) still uses email login.
    staff = sign_in_account()
    response = login_api(account=staff, email=STAFF_EMAIL)
    assert response.status_code == 200, response.text
