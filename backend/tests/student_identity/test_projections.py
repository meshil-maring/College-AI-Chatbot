"""Test projections."""

from __future__ import annotations

from app.repositories.admin import admin_academics as repo


def test_student_identity_columns_projection_exposes_phase62_fields() -> None:
    """STUDENT_IDENTITY_COLUMNS exposes the Phase 6.2 identity fields."""
    cols = repo.STUDENT_IDENTITY_COLUMNS
    assert "email" in cols
    assert "register_number" in cols
    assert "university_roll_number" in cols
    assert "approval_status" in cols
    assert "institution_id" in cols


def test_student_identity_columns_still_contains_core_identity() -> None:
    """Identity projection still includes the core tenant + student identity."""
    cols = repo.STUDENT_IDENTITY_COLUMNS
    for field in (
        "student_id",
        "user_id",
        "institution_id",
        "student_number",
        "status",
        "is_active",
    ):
        assert field in cols, f"{field} missing from STUDENT_IDENTITY_COLUMNS"


def test_identity_projection_has_no_tenant_id() -> None:
    """institution_id remains the sole tenant key — no tenant_id anywhere."""
    assert "tenant_id" not in repo.STUDENT_IDENTITY_COLUMNS
    assert "tenant_id" not in repo.STUDENT_COLUMNS
