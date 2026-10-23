"""Test lookups."""

from __future__ import annotations

from app.repositories.admin import admin_academics as repo

from .support import (
    INSTITUTION_A,
    STUDENT_ID_A,
    STUDENT_ROW_A,
    _make_mock_client,
)


def test_get_student_by_email_resolves_within_institution() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_email(client, INSTITUTION_A, "student.a@collegea.test")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_email_is_case_insensitive() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_email(client, INSTITUTION_A, "STUDENT.A@COLLEGEA.TEST")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_email_returns_none_when_missing() -> None:
    client = _make_mock_client()
    row = repo.get_student_by_email(client, INSTITUTION_A, "missing@collegea.test")
    assert row is None


def test_get_student_by_register_number_resolves_within_institution() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_register_number(client, INSTITUTION_A, "1001")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_register_number_trims_input() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_register_number(client, INSTITUTION_A, "  1001 ")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_register_number_returns_none_when_missing() -> None:
    client = _make_mock_client()
    row = repo.get_student_by_register_number(client, INSTITUTION_A, "9999")
    assert row is None


def test_get_student_by_university_roll_number_resolves_within_institution() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_university_roll_number(client, INSTITUTION_A, "2026-1001")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_university_roll_number_returns_none_when_missing() -> None:
    client = _make_mock_client()
    row = repo.get_student_by_university_roll_number(
        client, INSTITUTION_A, "no-such-roll"
    )
    assert row is None


def test_resolve_student_by_identifier_email_match() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.resolve_student_by_identifier(
        client, INSTITUTION_A, "student.a@collegea.test"
    )
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_resolve_student_by_identifier_register_number_match() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.resolve_student_by_identifier(client, INSTITUTION_A, "1001")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_resolve_student_by_identifier_university_roll_match() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.resolve_student_by_identifier(client, INSTITUTION_A, "2026-1001")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_resolve_student_by_identifier_empty_returns_none() -> None:
    client = _make_mock_client()
    row = repo.resolve_student_by_identifier(client, INSTITUTION_A, "   ")
    assert row is None
    row = repo.resolve_student_by_identifier(client, INSTITUTION_A, "")
    assert row is None
