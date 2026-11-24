"""Known database rules become specific messages; unknown errors stay generic."""

import re
from pathlib import Path

import pytest
from postgrest.exceptions import APIError

from app.services.academics.database_errors import translate_database_error
from app.services.academics.database_rule_messages import RULE_MESSAGES

MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"


def failure(code, message, details=None):
    return APIError({"code": code, "message": message, "details": details, "hint": None})


def test_batch_rule_gets_its_own_code_and_actionable_message():
    error = translate_database_error(failure("23514", "Batch cannot run longer than its program duration"))
    assert (error.status_code, error.code) == (422, "ACADEMIC_BATCH_TOO_LONG")
    assert "program duration" in error.message


def test_dependent_records_are_a_conflict():
    error = translate_database_error(failure("23514", "Deactivate dependent degree programs first"))
    assert (error.status_code, error.code) == (409, "ACADEMIC_HAS_ACTIVE_DEPENDENTS")
    assert error.message == "Deactivate this department's programs first."


def test_surrounding_whitespace_is_ignored():
    error = translate_database_error(failure("23514", "  Published curriculum mappings are immutable \n"))
    assert error.code == "ACADEMIC_CURRICULUM_LOCKED"


@pytest.mark.parametrize("message", [
    'new row for relation "admission_cohorts" violates check constraint "admission_cohorts_years_check"',
    "Some future rule",
    "",
])
def test_unknown_rule_messages_stay_generic_and_hide_database_details(message):
    error = translate_database_error(failure("23514", message, details="Failing row contains (secret)"))
    assert error.code == "ACADEMIC_HIERARCHY_INVALID"
    assert "admission_cohorts" not in error.message and "secret" not in error.message


def test_known_text_under_an_unrelated_code_is_not_reinterpreted():
    error = translate_database_error(failure("42501", "Active department required"))
    assert error.code == "FORBIDDEN"


def test_every_mapped_message_is_still_raised_by_a_migration():
    raised = set()
    for path in MIGRATIONS.glob("*.sql"):
        raised.update(re.findall(r"RAISE EXCEPTION\s+'([^']+)'", path.read_text(encoding="utf-8")))
    missing = sorted(set(RULE_MESSAGES) - raised)
    assert not missing, f"Rule messages no longer raised by any migration: {missing}"


@pytest.mark.parametrize("status,code,message", RULE_MESSAGES.values())
def test_public_messages_are_sentences_without_database_names(status, code, message):
    assert status in {409, 422} and re.fullmatch(r"[A-Z_]+", code)
    assert message.endswith(".") and "_" not in message
