"""Phase 6.8 — Test / exam results security tests.

Covers the result functionality built on the locked Phase 6.1-6.7 identity,
tenant, authentication, and RBAC baseline over the EXISTING Phase Admin-1
result tables:

  * schema / database contract (Phase 6.8 migration: tenant column, CHECKs,
    guard triggers, indexes; no new table)
  * server-side derivation (institution_id from the STUDENT record;
    percentage from scored/max; letter-grade normalization)
  * score validation (negative, over-max, non-positive max)
  * academic-context validation (student / academic year / semester /
    course / program / section chains, cross-tenant context)
  * duplicate + concurrency protection at the database boundary
  * role enforcement (admin-only mutation; staff/faculty/student -> 403;
    unauthenticated -> 401)
  * tenant isolation for institution-bound admins; platform-admin policy
    consistent with the locked Phase 6.4/6.6 behavior
  * student self-service strictly scoped to the JWT-derived profile, with no
    existence leak for foreign results
  * request-schema strictness (extra='forbid', malformed UUIDs)
  * audit logging for privileged mutations

Physical (live-database) constraint verification lives in a skip-by-default
class at the bottom of this file, mirroring the project's existing
``test_physical_validation_phase_4_4.py`` opt-in convention.
"""

from __future__ import annotations

import itertools
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.repositories import results as results_repo
from app.repositories.results import STUDENT_RESULT_COLUMNS, TEST_RESULT_COLUMNS
from app.services import results as results_svc
from app.services.admin_academics import (
    RESULT_STATUSES,
    RESULT_TYPES,
    TEST_RESULT_STATUSES,
    TEST_TYPES,
    ResultCreate,
    ResultItemCreate,
    ResultUpdate,
    TestResultCreate,
    TestResultUpdate,
)

client = TestClient(app, raise_server_exceptions=False)

# ----------------------------------------------------------------------------
# Shared constants & helpers
# ----------------------------------------------------------------------------

TENANT_A = "a1111111-0000-0000-0000-000000000001"
TENANT_B = "b2222222-0000-0000-0000-000000000002"
STUDENT_ID = "30000000-0000-0000-0000-000000000151"
OTHER_STUDENT_ID = "30000000-0000-0000-0000-000000000152"
COURSE_ID = "30000000-0000-0000-0000-0000000000c1"
AY_ID = "30000000-0000-0000-0000-000000000022"
SEM_ID = "30000000-0000-0000-0000-000000000033"
PROGRAM_ID = "30000000-0000-0000-0000-000000000011"
SECTION_ID = "30000000-0000-0000-0000-000000000099"
TEST_RESULT_ID = "40000000-0000-0000-0000-000000000601"
RESULT_ID = "40000000-0000-0000-0000-000000000701"

_ROOT = Path(__file__).resolve().parents[2]
PHASE_6_8_MIGRATION = (
    _ROOT / "supabase" / "migrations" / "20260913010000_phase_6_8_results.sql"
)
PHASE_ADMIN_1_MIGRATION = (
    _ROOT
    / "supabase"
    / "migrations"
    / "20260909000000_phase_admin_1_admin_student_schema.sql"
)


def _user(tenant=None, roles=("admin",)):
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "results@example.com",
        "roles": list(roles),
        "institution_id": tenant,
    }


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    _clear()


def _student_context(institution_id=TENANT_A, student_id=STUDENT_ID) -> dict:
    return {
        "student_id": student_id,
        "institution_id": institution_id,
        "program_id": PROGRAM_ID,
    }


def _test_result_row(institution_id=TENANT_A) -> dict:
    return {
        "test_result_id": TEST_RESULT_ID,
        "student_id": STUDENT_ID,
        "course_id": COURSE_ID,
        "section_id": SECTION_ID,
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "test_name": "Quiz 1",
        "test_type": "quiz",
        "max_marks": 20,
        "scored_marks": 18,
        "percentage": 90.0,
        "letter_grade": "A",
        "conducted_at": None,
        "status": "published",
        "institution_id": institution_id,
    }


def _test_result_create(**overrides) -> TestResultCreate:
    data = {
        "student_id": STUDENT_ID,
        "course_id": COURSE_ID,
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "test_name": "Quiz 1",
        "test_type": "quiz",
        "max_marks": 20,
        "scored_marks": 18,
    }
    data.update(overrides)
    return TestResultCreate(**data)


def _test_create_payload(**overrides) -> dict:
    payload = {
        "student_id": STUDENT_ID,
        "course_id": COURSE_ID,
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "test_name": "Quiz 1",
        "test_type": "quiz",
        "max_marks": 20,
        "scored_marks": 18,
    }
    payload.update(overrides)
    return payload


def _context_patches(
    institution_id=TENANT_A, student_id=STUDENT_ID, ay=AY_ID, sem=SEM_ID
):
    """Patch the academic-context lookups used by the Phase 6.8 service."""
    return (
        patch(
            "app.repositories.results.get_student_context",
            return_value=_student_context(institution_id, student_id),
        ),
        patch(
            "app.repositories.results.get_academic_year_context",
            return_value={"academic_year_id": ay, "institution_id": institution_id},
        ),
        patch(
            "app.repositories.results.get_semester_context",
            return_value={"semester_id": sem, "academic_year_id": ay},
        ),
        patch(
            "app.repositories.results.get_course_institution",
            return_value=institution_id,
        ),
        patch(
            "app.repositories.results.get_program_institution",
            return_value=institution_id,
        ),
    )


# ============================================================================
# DATABASE — schema contract
# ============================================================================


def test_result_projections_include_phase68_tenant_column() -> None:
    assert "institution_id" in TEST_RESULT_COLUMNS
    assert "institution_id" in STUDENT_RESULT_COLUMNS
    assert [c.strip() for c in TEST_RESULT_COLUMNS.split(",")][0] == "test_result_id"


def test_result_vocabularies_match_existing_check_constraints() -> None:
    assert TEST_TYPES == [
        "quiz",
        "assignment",
        "midterm",
        "final",
        "project",
        "internal",
        "external",
    ]
    assert TEST_RESULT_STATUSES == ["draft", "published", "withheld"]
    assert RESULT_TYPES == ["semester", "supplementary", "final", "provisional"]
    assert RESULT_STATUSES == ["draft", "published", "withheld"]


def test_migration_adds_hardening_without_creating_tables() -> None:
    sql = PHASE_6_8_MIGRATION.read_text(encoding="utf-8")
    # No new result table is created — only the existing Admin-1 tables.
    assert "CREATE TABLE" not in sql
    # Server-derived tenant columns + institutions FKs.
    assert sql.count('ADD COLUMN "institution_id"') == 2
    assert "test_results_institution_id_fkey" in sql
    assert "student_results_institution_id_fkey" in sql
    assert 'REFERENCES "public"."institutions"' in sql
    # Score / credit integrity CHECKs.
    assert "test_results_score_marks_check" in sql
    assert "student_results_credits_earned_max_check" in sql


def test_migration_defines_guard_triggers_and_ownership_immutability() -> None:
    sql = PHASE_6_8_MIGRATION.read_text(encoding="utf-8")
    assert "test_results_tenant_guard" in sql
    assert "student_results_tenant_guard" in sql
    # Two triggers + the header comment mentioning the same phrase.
    assert sql.count("BEFORE INSERT OR UPDATE") >= 2
    # Trigger-overridden tenant, never client-trusted (PL/pgSQL record variable NEW,
    # not a quoted identifier — fixed from "NEW"."institution_id" to NEW."institution_id").
    assert 'NEW."institution_id" := v_student_institution_id' in sql
    # Academic-context invariants (fail closed).
    assert "test result academic year does not exist" in sql
    assert "test result student and academic year belong to different institutions" in sql
    assert "test result student and course belong to different institutions" in sql
    assert "test result student and section belong to different institutions" in sql
    assert "test result academic context must match the section offering" in sql
    assert "result semester must belong to the result academic year" in sql
    assert "result student and program belong to different institutions" in sql
    # Ownership immutability + updated_at freshness.
    assert "test result ownership fields cannot be changed" in sql
    assert "result ownership fields cannot be changed" in sql
    assert 'NEW."updated_at" := "now"()' in sql


def test_migration_preserves_admin1_unique_constraints() -> None:
    """The Admin-1 uniqueness rules are the duplicate protection and must be
    retained (the locked Admin-1 migration is not modified)."""
    admin1 = PHASE_ADMIN_1_MIGRATION.read_text(encoding="utf-8")
    assert "test_results_student_course_test_sem_key" in admin1
    assert "student_results_student_sem_ay_prog_key" in admin1


def test_migration_defines_query_indexes() -> None:
    sql = PHASE_6_8_MIGRATION.read_text(encoding="utf-8")
    assert "idx_test_results_institution_id" in sql
    assert "idx_test_results_student_conducted" in sql
    assert "idx_test_results_ay_semester" in sql
    assert "idx_student_results_institution_id" in sql
    assert "idx_student_results_student_issued" in sql
    assert "idx_student_results_ay_semester" in sql


# ============================================================================
# TEST RESULTS — service behavior
# ============================================================================


def test_create_test_result_derives_tenant_and_percentage() -> None:
    """institution_id and percentage on the row are server-derived, never
    client input (TestResultCreate has no institution_id field; percentage is
    excluded from the persisted payload and recomputed)."""
    db = MagicMock()
    created = _test_result_row()
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.insert_test_result", return_value=created
        ) as insert_mock,
    p_student, p_year, p_sem, p_course, p_prog,
    ):
        row = results_svc.create_test_result(
            _test_result_create(percentage=5.0)  # client value must be ignored
        )

    assert row["institution_id"] == TENANT_A
    persisted = insert_mock.call_args.args[1]
    assert persisted["institution_id"] == TENANT_A
    assert persisted["percentage"] == 90.0  # 18 / 20 * 100


def test_create_test_result_percentage_none_without_score() -> None:
    db = MagicMock()
    created = _test_result_row()
    created["scored_marks"] = None
    created["percentage"] = None
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.insert_test_result", return_value=created
        ) as insert_mock,
    p_student, p_year, p_sem, p_course, p_prog,
    ):
        results_svc.create_test_result(_test_result_create(scored_marks=None))
    assert insert_mock.call_args.args[1]["percentage"] is None


def test_create_test_result_normalizes_letter_grade() -> None:
    db = MagicMock()
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.insert_test_result",
            return_value=_test_result_row(),
        ) as insert_mock,
    p_student, p_year, p_sem, p_course, p_prog,
    ):
        results_svc.create_test_result(_test_result_create(letter_grade="   "))
    assert insert_mock.call_args.args[1]["letter_grade"] is None


@pytest.mark.parametrize(
    ("overrides", "detail"),
    [
        # Schema-layer rejection (pydantic Field constraints).
        ({"scored_marks": -1}, "greater_than_equal"),
        ({"max_marks": 0}, "greater_than"),
        ({"max_marks": -5}, "greater_than"),
        # Service-layer rejection.
        ({"scored_marks": 25, "max_marks": 20}, "INVALID_SCORES"),
    ],
)
def test_create_test_result_rejects_invalid_scores(overrides, detail) -> None:
    with pytest.raises((AppError, ValidationError)) as exc:
        results_svc.create_test_result(_test_result_create(**overrides))
    if isinstance(exc.value, AppError):
        assert exc.value.code == "INVALID_SCORES"
        assert "max_marks" in exc.value.message
    else:
        assert detail in str(exc.value)


def test_create_test_result_rejects_invalid_type_and_status() -> None:
    with pytest.raises(AppError) as exc:
        results_svc.create_test_result(_test_result_create(test_type="bogus"))
    assert exc.value.code == "INVALID_TEST_TYPE"

    with pytest.raises(AppError) as exc:
        results_svc.create_test_result(_test_result_create(status="bogus"))
    assert exc.value.code == "INVALID_TEST_RESULT_STATUS"


def test_create_test_result_rejects_unknown_student() -> None:
    db = MagicMock()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_student_context", return_value=None
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "STUDENT_NOT_FOUND"
    assert exc.value.status_code == 404


# ============================================================================
# TEST RESULTS — academic-context validation (fail closed)
# ============================================================================


def _patch_section_context(return_value):
    return patch(
        "app.repositories.attendance.get_section_academic_context",
        return_value=return_value,
    )


def _section_context(institution_id=TENANT_A):
    return {
        "section_id": SECTION_ID,
        "section_code": "AIDS-CS101-A",
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "program_id": PROGRAM_ID,
        "course_id": COURSE_ID,
        "institution_id": institution_id,
    }


def test_create_test_result_rejects_unknown_academic_year() -> None:
    with (
        patch("app.services.results.get_admin_client", return_value=MagicMock()),
        patch(
            "app.repositories.results.get_student_context",
            return_value=_student_context(),
        ),
        patch(
            "app.repositories.results.get_academic_year_context", return_value=None
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "ACADEMIC_CONTEXT_INVALID"
    assert exc.value.status_code == 404


def test_create_test_result_rejects_cross_tenant_academic_year() -> None:
    with (
        patch("app.services.results.get_admin_client", return_value=MagicMock()),
        patch(
            "app.repositories.results.get_student_context",
            return_value=_student_context(TENANT_A),
        ),
        patch(
            "app.repositories.results.get_academic_year_context",
            return_value={"academic_year_id": AY_ID, "institution_id": TENANT_B},
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "TENANT_MISMATCH"
    assert exc.value.status_code == 403


def test_create_test_result_rejects_unknown_and_mismatched_semester() -> None:
    db = MagicMock()
    student = _student_context()
    year = {"academic_year_id": AY_ID, "institution_id": TENANT_A}
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.repositories.results.get_student_context", return_value=student),
        patch(
            "app.repositories.results.get_academic_year_context", return_value=year
        ),
        patch("app.repositories.results.get_semester_context", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "ACADEMIC_CONTEXT_INVALID"

    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.repositories.results.get_student_context", return_value=student),
        patch(
            "app.repositories.results.get_academic_year_context", return_value=year
        ),
        patch(
            "app.repositories.results.get_semester_context",
            return_value={"semester_id": SEM_ID, "academic_year_id": str(uuid4())},
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "ACADEMIC_CONTEXT_MISMATCH"


def test_create_test_result_rejects_unknown_and_cross_tenant_course() -> None:
    db = MagicMock()
    student = _student_context()
    year = {"academic_year_id": AY_ID, "institution_id": TENANT_A}
    semester = {"semester_id": SEM_ID, "academic_year_id": AY_ID}
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.repositories.results.get_student_context", return_value=student),
        patch(
            "app.repositories.results.get_academic_year_context", return_value=year
        ),
        patch(
            "app.repositories.results.get_semester_context", return_value=semester
        ),
        patch("app.repositories.results.get_course_institution", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "COURSE_NOT_FOUND"

    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.repositories.results.get_student_context", return_value=student),
        patch(
            "app.repositories.results.get_academic_year_context", return_value=year
        ),
        patch(
            "app.repositories.results.get_semester_context", return_value=semester
        ),
        patch(
            "app.repositories.results.get_course_institution", return_value=TENANT_B
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "TENANT_MISMATCH"


def test_create_test_result_validates_attached_section() -> None:
    db = MagicMock()
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.insert_test_result",
            return_value=_test_result_row(),
        ),
    p_student, p_year, p_sem, p_course, p_prog,
        _patch_section_context(_section_context()),
    ):
        row = results_svc.create_test_result(
            _test_result_create(section_id=SECTION_ID)
        )
    assert row["test_result_id"] == TEST_RESULT_ID

    # Unknown section / broken chain -> 404 (fail closed).
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
        _patch_section_context(None),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(
                _test_result_create(section_id=SECTION_ID)
            )
    assert exc.value.code == "SECTION_NOT_FOUND"

    # Cross-tenant section -> 403.
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
        _patch_section_context(_section_context(TENANT_B)),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(
                _test_result_create(section_id=SECTION_ID)
            )
    assert exc.value.code == "TENANT_MISMATCH"

    # Section offering describing a different course/year/semester -> 422.
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
        _patch_section_context({**_section_context(), "semester_id": str(uuid4())}),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(
                _test_result_create(section_id=SECTION_ID)
            )
    assert exc.value.code == "ACADEMIC_CONTEXT_MISMATCH"


# ============================================================================
# TEST RESULTS — update / delete / duplicate / concurrency
# ============================================================================


def test_update_test_result_rederives_percentage_and_validates() -> None:
    db = MagicMock()
    existing = _test_result_row()
    updated = {**existing, "scored_marks": 10, "max_marks": 20, "percentage": 50.0}
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_test_result_row", return_value=existing
        ),
        patch(
            "app.repositories.results.update_test_result_row",
            return_value=updated,
        ) as update_mock,
    ):
        row = results_svc.update_test_result(
            TEST_RESULT_ID,
            TestResultUpdate(scored_marks=10, percentage=99.0),  # client pct ignored
        )
    assert row["percentage"] == 50.0
    fields = update_mock.call_args.args[2]
    assert fields["percentage"] == 50.0

    # Merged score validation: existing max 20 + update to 25 -> over max.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_test_result_row", return_value=existing
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.update_test_result(
                TEST_RESULT_ID, TestResultUpdate(scored_marks=25)
            )
    assert exc.value.code == "INVALID_SCORES"

    # Empty update -> 422.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_test_result_row", return_value=existing
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.update_test_result(TEST_RESULT_ID, TestResultUpdate())
    assert exc.value.code == "EMPTY_UPDATE"

    # 404 for an unknown row.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.repositories.results.get_test_result_row", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.update_test_result(
                TEST_RESULT_ID, TestResultUpdate(status="draft")
            )
    assert exc.value.code == "TEST_RESULT_NOT_FOUND"


def test_update_test_result_revalidates_changed_section() -> None:
    db = MagicMock()
    existing = _test_result_row()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_test_result_row", return_value=existing
        ),
        patch(
            "app.repositories.results.update_test_result_row",
            return_value=existing,
        ),
        _patch_section_context(None),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.update_test_result(
                TEST_RESULT_ID, TestResultUpdate(section_id=SECTION_ID)
            )
    assert exc.value.code == "SECTION_NOT_FOUND"


def test_delete_test_result_404_and_delete() -> None:
    db = MagicMock()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.repositories.results.get_test_result_row", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.delete_test_result(TEST_RESULT_ID)
    assert exc.value.code == "TEST_RESULT_NOT_FOUND"

    existing = _test_result_row()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_test_result_row", return_value=existing
        ),
        patch("app.repositories.results.delete_test_result_row") as delete_mock,
    ):
        row = results_svc.delete_test_result(TEST_RESULT_ID)
    assert row["test_result_id"] == TEST_RESULT_ID
    delete_mock.assert_called_once()


def test_duplicate_test_result_maps_to_stable_conflict() -> None:
    """A UNIQUE-constraint violation from the database is mapped to the
    stable 409 TEST_RESULT_DUPLICATE; other failures stay generic."""
    db = MagicMock()
    duplicate = Exception(
        'duplicate key value violates unique constraint '
        '"test_results_student_course_test_sem_key"'
    )
    other = Exception('insert or update on table "test_results" violates FK')
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
        patch(
            "app.repositories.results.insert_test_result", side_effect=duplicate
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "TEST_RESULT_DUPLICATE"
    assert exc.value.status_code == 409

    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
        patch("app.repositories.results.insert_test_result", side_effect=other),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_test_result(_test_result_create())
    assert exc.value.code == "TEST_RESULT_CREATE_FAILED"


def test_concurrent_duplicate_creation_is_handled_safely() -> None:
    """Two concurrent creates of the same (student, course, test, term): the
    database UNIQUE constraint guarantees exactly one wins and the loser is
    mapped to TEST_RESULT_DUPLICATE — never a silent double insert."""
    db = MagicMock()
    state = {"inserted": 0}
    lock = threading.Lock()

    def fake_insert(_client, row):
        with lock:
            state["inserted"] += 1
            if state["inserted"] > 1:
                raise Exception(
                    'duplicate key value violates unique constraint '
                    '"test_results_student_course_test_sem_key" (SQLSTATE 23505)'
                )
        return _test_result_row()

    barrier = threading.Barrier(2)

    def attempt():
        barrier.wait()
        try:
            results_svc.create_test_result(_test_result_create())
            return "ok"
        except AppError as exc:
            return exc.code

    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        p_student,
        p_year,
        p_sem,
        p_course,
        p_prog,
        patch(
            "app.repositories.results.insert_test_result",
            side_effect=fake_insert,
        ),
    ):
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = sorted(pool.map(lambda _: attempt(), range(2)))

    assert outcomes == ["TEST_RESULT_DUPLICATE", "ok"]


# ============================================================================
# STUDENT RESULTS (consolidated summaries) — service behavior
# ============================================================================


def _result_create(**overrides) -> ResultCreate:
    data = {
        "student_id": STUDENT_ID,
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "program_id": PROGRAM_ID,
        "result_type": "semester",
        "sgpa": 8.5,
        "items": [ResultItemCreate(course_id=COURSE_ID, credits_earned=4)],
    }
    data.update(overrides)
    return ResultCreate(**data)


def _result_row(institution_id=TENANT_A) -> dict:
    return {
        "student_result_id": RESULT_ID,
        "student_id": STUDENT_ID,
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "program_id": PROGRAM_ID,
        "result_type": "semester",
        "total_credits_earned": 8,
        "total_credits_max": 8,
        "sgpa": 8.0,
        "cgpa": 8.0,
        "status": "published",
        "issued_at": None,
        "institution_id": institution_id,
    }


def test_create_result_derives_tenant_server_side() -> None:
    db = MagicMock()
    created = _result_row()
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.insert_student_result",
            return_value=created,
        ) as insert_mock,
    p_student, p_year, p_sem, p_course, p_prog,
    ):
        row = results_svc.create_result(_result_create())
    assert row["institution_id"] == TENANT_A
    persisted = insert_mock.call_args.args[1]
    assert persisted["institution_id"] == TENANT_A
    assert "items" not in persisted


def test_create_result_validates_items_and_normalizes_grades() -> None:
    db = MagicMock()
    stored_items = [{"student_result_item_id": str(uuid4())}]
    # Unknown item course -> 404 (fail closed).
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
        patch("app.repositories.results.get_course_institution", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_result(_result_create())
    assert exc.value.code == "COURSE_NOT_FOUND"

    # Happy path: item grade normalized and linked to the created result.
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.insert_student_result",
            return_value=_result_row(),
        ),
        patch(
            "app.repositories.results.insert_student_result_items",
            return_value=stored_items,
        ) as items_mock,
    p_student, p_year, p_sem, p_course, p_prog,
    ):
        row = results_svc.create_result(
            _result_create(
                items=[
                    ResultItemCreate(
                        course_id=COURSE_ID, credits_earned=4, letter_grade="  "
                    )
                ]
            )
        )
    item_rows = items_mock.call_args.args[1]
    assert item_rows[0]["letter_grade"] is None
    assert item_rows[0]["student_result_id"] == RESULT_ID
    assert row["items"] == stored_items


def test_create_result_rejects_bad_program_and_context() -> None:
    db = MagicMock()
    year = {"academic_year_id": AY_ID, "institution_id": TENANT_A}
    semester = {"semester_id": SEM_ID, "academic_year_id": AY_ID}
    # Unknown program (broken department chain) -> 404.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_student_context",
            return_value=_student_context(),
        ),
        patch(
            "app.repositories.results.get_academic_year_context", return_value=year
        ),
        patch(
            "app.repositories.results.get_semester_context", return_value=semester
        ),
        patch("app.repositories.results.get_program_institution", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_result(_result_create())
    assert exc.value.code == "PROGRAM_NOT_FOUND"

    # Cross-tenant program -> 403.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_student_context",
            return_value=_student_context(TENANT_A),
        ),
        patch(
            "app.repositories.results.get_academic_year_context", return_value=year
        ),
        patch(
            "app.repositories.results.get_semester_context", return_value=semester
        ),
        patch(
            "app.repositories.results.get_program_institution",
            return_value=TENANT_B,
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_result(_result_create())
    assert exc.value.code == "TENANT_MISMATCH"

    # Invalid result type -> 422.
    with pytest.raises(AppError) as exc:
        results_svc.create_result(_result_create(result_type="bogus"))
    assert exc.value.code == "INVALID_RESULT_TYPE"

    # Invalid status -> 422.
    with pytest.raises(AppError) as exc:
        results_svc.create_result(_result_create(status="bogus"))
    assert exc.value.code == "INVALID_RESULT_STATUS"


def test_duplicate_result_maps_to_stable_conflict() -> None:
    db = MagicMock()
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
        patch(
            "app.repositories.results.insert_student_result",
            side_effect=Exception(
                "duplicate key value violates unique constraint"
            ),
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.create_result(_result_create())
    assert exc.value.code == "RESULT_DUPLICATE"
    assert exc.value.status_code == 409


def test_update_and_delete_result_validation() -> None:
    db = MagicMock()
    existing = _result_row()
    # Unknown result -> 404.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_student_result_row", return_value=None
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.update_result(RESULT_ID, ResultUpdate(status="draft"))
    assert exc.value.code == "RESULT_NOT_FOUND"

    # Empty update -> 422.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_student_result_row",
            return_value=existing,
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.update_result(RESULT_ID, ResultUpdate())
    assert exc.value.code == "EMPTY_UPDATE"

    # Invalid status on update -> 422.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_student_result_row",
            return_value=existing,
        ),
    ):
        with pytest.raises(AppError) as exc:
            results_svc.update_result(
                RESULT_ID, ResultUpdate(status="bogus")
            )
    assert exc.value.code == "INVALID_RESULT_STATUS"

    # Successful update.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_student_result_row",
            return_value=existing,
        ),
        patch(
            "app.repositories.results.update_student_result_row",
            return_value=existing,
        ) as update_mock,
    ):
        row = results_svc.update_result(RESULT_ID, ResultUpdate(status="withheld"))
    assert row["status"] == "published"

    # Delete (items + summary) — hard delete per Admin-1 policy.
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch(
            "app.repositories.results.get_student_result_with_items",
            return_value=existing,
        ),
        patch("app.repositories.results.delete_student_result") as delete_mock,
    ):
        row = results_svc.delete_result(RESULT_ID)
    assert row["student_result_id"] == RESULT_ID
    delete_mock.assert_called_once()


# ============================================================================
# API — authorization, tenant isolation, audit
# ============================================================================


def _audit_db(first_insert: dict):
    """Mock service-role client: the first insert returns the created entity
    row; every later insert (typically the audit-log row) returns a generic
    row (mirrors the Phase Admin-3 API test helper)."""
    db = MagicMock()
    first = MagicMock(data=[first_insert])
    audit = MagicMock(data=[{"audit_id": str(uuid4())}])
    db.table.return_value.insert.return_value.execute.side_effect = itertools.chain(
        [first], itertools.repeat(audit)
    )
    return db


def _insert_rows(db):
    return [
        call.args[0]
        for call in db.table.return_value.insert.call_args_list
        if call.args
    ]


def test_admin_result_endpoints_require_authentication() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get(f"/api/v1/admin/results/{TEST_RESULT_ID}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    response = client.post("/api/v1/admin/test-results", json={})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    response = client.post("/api/v1/admin/results", json={})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_student_role_cannot_mutate_results() -> None:
    """Students must never reach the admin result mutation paths."""
    _as(_user(roles=("student",)))
    response = client.post(
        "/api/v1/admin/test-results", json=_test_create_payload()
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    response = client.post("/api/v1/admin/results", json={})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_staff_and_faculty_roles_cannot_mutate_results() -> None:
    """Preserved product policy: staff/faculty do not get result mutation
    authority (admin-only, consistent with the locked Phase 6.6 RBAC)."""
    for role in ("staff", "faculty"):
        _as(_user(roles=(role,)))
        response = client.post(
            "/api/v1/admin/test-results", json=_test_create_payload()
        )
        assert response.status_code == 403, role
        assert response.json()["error"]["code"] == "FORBIDDEN", role


def test_platform_admin_can_create_test_results_globally() -> None:
    """Platform admins (no tenant) keep the locked global authority."""
    _as(_user(tenant=None))
    db = _audit_db({"test_result_id": TEST_RESULT_ID})
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.api.admin.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
    ):
        response = client.post(
            "/api/v1/admin/test-results", json=_test_create_payload()
        )
    assert response.status_code == 201
    assert response.json()["test_result_id"] == TEST_RESULT_ID


def test_tenant_admin_cannot_create_results_for_foreign_student() -> None:
    """Cross-tenant creation is rejected before any academic lookup."""
    _as(_user(tenant=TENANT_A))
    with patch(
        "app.services.admin_academics.get_student",
        return_value={"student_id": STUDENT_ID, "institution_id": TENANT_B},
    ):
        response = client.post(
            "/api/v1/admin/test-results", json=_test_create_payload()
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"

        response = client.post(
            "/api/v1/admin/results",
            json={
                "student_id": STUDENT_ID,
                "academic_year_id": AY_ID,
                "semester_id": SEM_ID,
                "program_id": PROGRAM_ID,
                "result_type": "semester",
            },
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_tenant_admin_cannot_touch_foreign_results_on_update_delete() -> None:
    _as(_user(tenant=TENANT_A))
    db = MagicMock()
    foreign_student = {"student_id": STUDENT_ID, "institution_id": TENANT_B}
    with (
        patch("app.api.admin.get_admin_client", return_value=db),
        patch(
            "app.services.admin_academics.get_student",
            return_value=foreign_student,
        ),
        patch(
            "app.services.results.get_test_result",
            return_value=_test_result_row(institution_id=TENANT_B),
        ),
    ):
        response = client.patch(
            f"/api/v1/admin/test-results/{TEST_RESULT_ID}", json={"status": "draft"}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"

        response = client.delete(f"/api/v1/admin/test-results/{TEST_RESULT_ID}")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"

    with (
        patch("app.api.admin.get_admin_client", return_value=db),
        patch(
            "app.services.admin_academics.get_student",
            return_value=foreign_student,
        ),
        patch(
            "app.services.results.get_result",
            return_value=_result_row(institution_id=TENANT_B),
        ),
    ):
        response = client.delete(f"/api/v1/admin/results/{RESULT_ID}")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_tenant_admin_can_manage_own_tenant_results() -> None:
    _as(_user(tenant=TENANT_A))
    db = _audit_db({"test_result_id": TEST_RESULT_ID})
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.api.admin.get_admin_client", return_value=db),
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(),
        ),
    p_student, p_year, p_sem, p_course, p_prog,
    ):
        response = client.post(
            "/api/v1/admin/test-results", json=_test_create_payload()
        )
    assert response.status_code == 201
    audit_rows = [r for r in _insert_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "test_result.create"


def test_result_creation_is_audited() -> None:
    _as(_user(tenant=None))
    db = _audit_db({"student_result_id": RESULT_ID})
    p_student, p_year, p_sem, p_course, p_prog = _context_patches()
    with (
        patch("app.services.results.get_admin_client", return_value=db),
        patch("app.api.admin.get_admin_client", return_value=db),
    p_student, p_year, p_sem, p_course, p_prog,
    ):
        response = client.post(
            "/api/v1/admin/results",
            json={
                "student_id": STUDENT_ID,
                "academic_year_id": AY_ID,
                "semester_id": SEM_ID,
                "program_id": PROGRAM_ID,
                "result_type": "semester",
                "sgpa": 8.5,
                "items": [{"course_id": COURSE_ID, "credits_earned": 4}],
            },
        )
    assert response.status_code == 201
    audit_rows = [r for r in _insert_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "result.create"
    assert audit_rows[0]["table_name"] == "student_results"


def test_malformed_uuids_are_rejected() -> None:
    _as(_user(tenant=None))
    response = client.get("/api/v1/admin/results/not-a-uuid")
    assert response.status_code == 422

    response = client.get("/api/v1/students/me/results/not-a-uuid")
    assert response.status_code == 422


def test_extra_fields_are_rejected_on_result_payloads() -> None:
    """extra='forbid': control fields (institution_id, role, user_id,
    approval_status) can never be injected as trusted security fields."""
    _as(_user(tenant=None))
    payload = _test_create_payload(institution_id=TENANT_B, role="admin")
    response = client.post("/api/v1/admin/test-results", json=payload)
    assert response.status_code == 422

    response = client.post(
        "/api/v1/admin/results",
        json={
            "student_id": STUDENT_ID,
            "academic_year_id": AY_ID,
            "semester_id": SEM_ID,
            "program_id": PROGRAM_ID,
            "result_type": "semester",
            "institution_id": TENANT_B,
        },
    )
    assert response.status_code == 422

    response = client.patch(
        f"/api/v1/admin/test-results/{TEST_RESULT_ID}",
        json={"student_id": OTHER_STUDENT_ID},
    )
    assert response.status_code == 422

    response = client.patch(
        f"/api/v1/admin/results/{RESULT_ID}",
        json={"program_id": str(uuid4())},
    )
    assert response.status_code == 422


# ============================================================================
# STUDENT SELF-SERVICE — strictly scoped to the JWT-derived profile
# ============================================================================


def _own_student(institution_id=TENANT_A):
    return {
        "student_id": STUDENT_ID,
        "institution_id": institution_id,
        "student_number": "S001",
    }


def _as_student(tenant=TENANT_A):
    _as(_user(tenant=tenant, roles=("student",)))


def test_student_can_retrieve_own_published_result() -> None:
    _as_student()
    row = {**_result_row(), "items": [{"course_id": COURSE_ID}]}
    with (
        patch(
            "app.services.student_data.get_own_student",
            return_value=_own_student(),
        ),
        patch(
            "app.repositories.results.get_student_result_with_items",
            return_value=row,
        ),
    ):
        response = client.get(f"/api/v1/students/me/results/{RESULT_ID}")
    assert response.status_code == 200
    assert response.json()["student_result_id"] == RESULT_ID
    assert response.json()["institution_id"] == TENANT_A


def test_student_cannot_retrieve_another_students_result() -> None:
    """Foreign results are indistinguishable from missing ones: the SAME
    404 RESULT_NOT_FOUND is returned, so the endpoint cannot be used to
    enumerate other students' results."""
    _as_student()
    foreign = {**_result_row(), "student_id": OTHER_STUDENT_ID}
    with (
        patch(
            "app.services.student_data.get_own_student",
            return_value=_own_student(),
        ),
        patch(
            "app.repositories.results.get_student_result_with_items",
            return_value=foreign,
        ),
    ):
        response = client.get(f"/api/v1/students/me/results/{RESULT_ID}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"

    # Genuinely missing row -> identical response.
    with (
        patch(
            "app.services.student_data.get_own_student",
            return_value=_own_student(),
        ),
        patch(
            "app.repositories.results.get_student_result_with_items",
            return_value=None,
        ),
    ):
        response = client.get(f"/api/v1/students/me/results/{RESULT_ID}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"


def test_student_cannot_retrieve_unpublished_result() -> None:
    """Draft/withheld rows stay admin-only (existing publication policy)."""
    _as_student()
    for status in ("draft", "withheld"):
        row = {**_result_row(), "status": status}
        with (
            patch(
                "app.services.student_data.get_own_student",
                return_value=_own_student(),
            ),
            patch(
                "app.repositories.results.get_student_result_with_items",
                return_value=row,
            ),
        ):
            response = client.get(f"/api/v1/students/me/results/{RESULT_ID}")
            assert response.status_code == 404, status
            assert response.json()["error"]["code"] == "RESULT_NOT_FOUND", status


def test_student_self_service_fails_safely_without_profile() -> None:
    """A missing student profile is a 404, never a silent broadening or a
    leak of another student's data."""
    _as_student()
    with patch(
        "app.services.student_data.get_own_student",
        side_effect=AppError(
            "No student profile is linked to this account",
            status_code=404,
            code="STUDENT_PROFILE_NOT_FOUND",
        ),
    ):
        response = client.get(f"/api/v1/students/me/results/{RESULT_ID}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


def test_student_self_service_tenant_guard() -> None:
    """Defense-in-depth: a stale/moved profile cannot smuggle a foreign
    tenant's result past the tenant assertion."""
    _as_student(tenant=TENANT_B)
    row = _result_row(institution_id=TENANT_A)
    with (
        patch(
            "app.services.student_data.get_own_student",
            return_value=_own_student(),
        ),
        patch(
            "app.repositories.results.get_student_result_with_items",
            return_value=row,
        ),
    ):
        response = client.get(f"/api/v1/students/me/results/{RESULT_ID}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_student_identity_params_are_never_trusted() -> None:
    """The self-service path resolves identity from the JWT only; there is
    no student_id parameter to tamper with on /me endpoints."""
    _as_student()
    openapi = client.get("/openapi.json").json()
    me_paths = [
        p
        for p in openapi["paths"]
        if p.startswith("/api/v1/students/me/")
        and "results" in p
        or p == "/api/v1/students/me/results"
    ]
    for path in me_paths:
        for method_spec in openapi["paths"][path].get("get", {}).get("parameters", []):
            assert "student_id" not in str(method_spec.get("name", ""))


# ============================================================================
# PHYSICAL (LIVE DATABASE) VALIDATION — opt-in, mirrors project convention
# ============================================================================
# These tests verify the Phase 6.8 migration against the real schema: the
# tenant backfill, the guard triggers (derivation, academic-context
# rejection, ownership immutability), the score CHECK, and the duplicate
# constraint. They are skipped in the default suite and run only when a
# reviewer opts in, matching the existing
# ``test_physical_validation_phase_4_4.py`` pattern. No credentials are
# hardcoded — the app's ``.env`` service-role config is reused.


@pytest.mark.skip(reason="Live-database validation requires explicit manual opt-in")
class TestResultsPhysicalValidationPhase68:
    """Live-database verification for Phase 6.8 constraints and triggers."""

    def test_live_schema_and_backfill(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        rows = db.table("test_results").select("*").limit(5).execute().data
        assert rows, "test_results must have seeded rows"
        assert "institution_id" in rows[0]
        for row in rows:
            student = (
                db.table("students")
                .select("institution_id")
                .eq("student_id", row["student_id"])
                .maybe_single()
                .execute()
                .data
            )
            assert row["institution_id"] == student["institution_id"]

        summaries = db.table("student_results").select("*").limit(5).execute().data
        for row in summaries:
            student = (
                db.table("students")
                .select("institution_id")
                .eq("student_id", row["student_id"])
                .maybe_single()
                .execute()
                .data
            )
            assert row["institution_id"] == student["institution_id"]

    def test_live_test_result_guard_trigger(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        seed = db.table("test_results").select("*").limit(1).execute().data[0]
        # institution_id is intentionally WRONG below — the trigger must
        # derive the tenant from the student record instead of trusting input.
        payload = {
            "student_id": seed["student_id"],
            "course_id": seed["course_id"],
            "academic_year_id": seed["academic_year_id"],
            "semester_id": seed["semester_id"],
            "test_name": "Phase 6.8 live probe",
            "test_type": "quiz",
            "max_marks": 10,
            "scored_marks": 8,
            "institution_id": "00000000-0000-0000-0000-000000000000",
        }
        row = db.table("test_results").insert(payload).execute().data[0]
        try:
            assert row["institution_id"] == seed["institution_id"]
            assert row["percentage"] is None  # derived only by the app layer

            # Score above max must be rejected at the database layer.
            bad_score = dict(payload, test_name="Phase 6.8 live probe 2",
                             scored_marks=11)
            with pytest.raises(Exception) as exc:
                db.table("test_results").insert(bad_score).execute()
            assert "score_marks_check" in str(exc.value)

            # Duplicate (same student/course/test/term) must be rejected.
            with pytest.raises(Exception) as exc2:
                db.table("test_results").insert(payload).execute()
            assert "duplicate" in str(exc2.value).lower() or "unique" in str(
                exc2.value
            ).lower()
        finally:
            db.table("test_results").delete().eq(
                "test_result_id", row["test_result_id"]
            ).execute()

    def test_live_student_result_guard_trigger(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        seed = db.table("student_results").select("*").limit(1).execute().data[0]
        payload = {
            "student_id": seed["student_id"],
            "academic_year_id": seed["academic_year_id"],
            "semester_id": seed["semester_id"],
            "program_id": seed["program_id"],
            "result_type": "semester",
            "institution_id": "00000000-0000-0000-0000-000000000000",
        }
        row = db.table("student_results").insert(payload).execute().data[0]
        try:
            assert row["institution_id"] == seed["institution_id"]

            # Ownership reassignment must be rejected at the database layer.
            other_program = (
                db.table("programs")
                .select("program_id")
                .neq("program_id", seed["program_id"])
                .limit(1)
                .execute()
                .data
            )
            if other_program:
                with pytest.raises(Exception) as exc:
                    db.table("student_results").update(
                        {"program_id": other_program[0]["program_id"]}
                    ).eq("student_result_id", row["student_result_id"]).execute()
                assert "ownership fields cannot be changed" in str(exc.value)
        finally:
            db.table("student_results").delete().eq(
                "student_result_id", row["student_result_id"]
            ).execute()