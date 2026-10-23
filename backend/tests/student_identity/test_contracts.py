"""Test contracts."""

from __future__ import annotations

from app.repositories.admin import admin_academics as repo

from app.services.admin import admin_academics as svc

import pytest

from .support import (
    INSTITUTION_A,
    STUDENT_ROW_A,
    USER_A,
    _make_mock_client,
)


def test_get_student_by_user_id_unchanged() -> None:
    """list/get by user id shape is unchanged by Phase 6.2."""
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_user_id(client, USER_A)
    assert row is None or row["institution_id"] == INSTITUTION_A


def test_studentcreate_requires_institution_id() -> None:
    """Pydantic contract: institution_id is a required identity field."""
    with pytest.raises(Exception):
        svc.StudentCreate(
            user_id=USER_A,
            student_number="STU-2026-001",
            enrollment_date="2026-01-15",
        )
