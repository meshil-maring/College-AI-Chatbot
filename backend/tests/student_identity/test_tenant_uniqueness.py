"""Test tenant uniqueness."""

from __future__ import annotations

from app.repositories.admin import admin_academics as repo

from unittest.mock import MagicMock, patch

from .support import (
    INSTITUTION_A,
    INSTITUTION_B,
    STUDENT_ID_A,
    STUDENT_ID_B,
    STUDENT_ROW_A,
    STUDENT_ROW_B,
    _make_mock_client,
)


def test_same_register_number_allowed_in_different_institutions() -> None:
    """College A register 1001 and College B register 1001 may coexist."""
    client_a = _make_mock_client([STUDENT_ROW_A])
    client_b = _make_mock_client([STUDENT_ROW_B])

    a = repo.get_student_by_register_number(client_a, INSTITUTION_A, "1001")
    b = repo.get_student_by_register_number(client_b, INSTITUTION_B, "1001")

    assert a is not None and a["student_id"] == STUDENT_ID_A
    assert b is not None and b["student_id"] == STUDENT_ID_B
    assert a["institution_id"] != b["institution_id"]
    assert a["register_number"] == b["register_number"] == "1001"


def test_same_email_allowed_in_different_institutions() -> None:
    """Two institutions may independently scope an identical email value."""
    row_a = {**STUDENT_ROW_A, "email": "shared@college.test"}
    row_b = {**STUDENT_ROW_B, "email": "shared@college.test"}
    client_a = _make_mock_client([row_a])
    client_b = _make_mock_client([row_b])

    a = repo.get_student_by_email(client_a, INSTITUTION_A, "shared@college.test")
    b = repo.get_student_by_email(client_b, INSTITUTION_B, "shared@college.test")

    assert a is not None and a["student_id"] == STUDENT_ID_A
    assert b is not None and b["student_id"] == STUDENT_ID_B


def test_same_university_roll_allowed_in_different_institutions() -> None:
    """University roll numbers are scoped per institution as well."""
    row_a = {**STUDENT_ROW_A, "university_roll_number": "2026-0001"}
    row_b = {**STUDENT_ROW_B, "university_roll_number": "2026-0001"}
    client_a = _make_mock_client([row_a])
    client_b = _make_mock_client([row_b])

    a = repo.get_student_by_university_roll_number(client_a, INSTITUTION_A, "2026-0001")
    b = repo.get_student_by_university_roll_number(client_b, INSTITUTION_B, "2026-0001")

    assert a is not None and a["student_id"] == STUDENT_ID_A
    assert b is not None and b["student_id"] == STUDENT_ID_B


def test_same_student_number_allowed_in_different_institutions() -> None:
    """student_number uniqueness is now (institution_id, student_number)."""
    row_a = {**STUDENT_ROW_A, "student_number": "1001"}
    row_b = {**STUDENT_ROW_B, "student_number": "1001"}
    client_a = _make_mock_client([row_a])
    client_b = _make_mock_client([row_b])

    a = repo.get_student(client_a, STUDENT_ID_A)
    b = repo.get_student(client_b, STUDENT_ID_B)

    assert a["institution_id"] == INSTITUTION_A
    assert b["institution_id"] == INSTITUTION_B
    assert a["student_number"] == b["student_number"] == "1001"


def test_register_number_lookup_scopes_by_institution() -> None:
    """The repo passes institution_id into the query — scoping is server-side."""
    client = MagicMock()
    builder = MagicMock()
    eq_calls = []
    builder.eq.side_effect = lambda col, val: eq_calls.append((col, val)) or builder
    builder.maybe_single.return_value.execute.return_value = MagicMock(data=None)
    client.table.return_value.select.return_value = builder

    repo.get_student_by_register_number(client, INSTITUTION_B, "1001")

    # The lookup must filter on institution_id (tenant) then register_number.
    assert ("institution_id", INSTITUTION_B) in eq_calls
    assert ("register_number", "1001") in eq_calls
