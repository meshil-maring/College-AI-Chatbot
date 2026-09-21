"""Phase 6.16.3 — Student information & learning-resource experience guards.

The student-facing information surfaces completed by Phase 6.16.3 (Notices
page, Learning Resources page, Profile page) read the Phase 6.16 / 6.14.1
endpoints, whose full security behaviour is already covered by
``tests/test_student_experience_dashboard_phase_6_16.py`` and
``tests/test_academic_profile_6141.py``. This suite pins the ADDITIONAL
contracts the 6.16.3 pages depend on:

* the page limit boundaries the frontend requests (notices 20, resources 20)
  are accepted, and one past the backend maximum is rejected with 422;
* a knowledge source with a source type OUTSIDE the known vocabulary is still
  projected safely (the frontend renders unknown types gracefully, so the
  backend must neither crash on nor silently drop such rows);
* internal storage/tenant metadata on a source row can never reach the
  student contract (explicit projection + ``extra="forbid"``);
* there is NO student-owned mutation route for the profile, notices, or
  resources — the Profile page is intentionally READ-ONLY.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.errors import AppError
from app.main import app
from app.services import student_notices as notices_service
from app.services import student_resources as resources_service

TENANT_A = "a1111111-0000-0000-0000-000000000001"
STUDENT_ID = "30000000-0000-0000-0000-000000000151"


@pytest.fixture
def authorized_student(monkeypatch):
    """Stub server-side identity/tenant resolution to the student's own tenant."""
    from app.services import student_context as student_context_service

    monkeypatch.setattr(
        student_context_service,
        "get_student_context",
        lambda current_user, **kwargs: {
            "student_id": STUDENT_ID,
            "institution_id": TENANT_A,
        },
    )
    monkeypatch.setattr(
        student_context_service,
        "assert_student_context_tenant",
        lambda current_user, ctx: None,
    )


def _student_user() -> dict:
    return {
        "user_id": "71000000-0000-0000-0000-000000000001",
        "email": "student@college.edu",
        "roles": ["student"],
        "institution_id": TENANT_A,
    }


def _chained_db(rows: list[dict]) -> MagicMock:
    """Supabase stub whose query-builder chain resolves to ``rows``."""
    db = MagicMock()
    builder = db.table.return_value.select.return_value
    builder.eq.return_value = builder
    builder.or_.return_value = builder
    builder.neq.return_value = builder
    builder.order.return_value = builder
    builder.limit.return_value = builder
    builder.execute.return_value = MagicMock(data=rows)
    return db


class TestPageLimitBoundaries:
    """The pages request limit=20; the contract must accept it and no more."""

    def test_notices_page_limit_is_within_the_contract(self, authorized_student):
        result = notices_service.get_own_notices(
            _student_user(),
            limit=notices_service.MAX_NOTICE_LIMIT,
            client=_chained_db([]),
        )
        assert result.items == []
        assert result.total == 0

    def test_notices_limit_past_the_maximum_is_422(self, authorized_student):
        with pytest.raises(AppError) as exc:
            notices_service.get_own_notices(
                _student_user(),
                limit=notices_service.MAX_NOTICE_LIMIT + 1,
                client=MagicMock(),
            )
        assert exc.value.status_code == 422
        assert exc.value.code == "INVALID_FILTER"

    def test_resources_page_limit_is_within_the_contract(self, authorized_student):
        assert resources_service.MAX_RESOURCE_LIMIT >= 20
        result = resources_service.get_own_resources(
            _student_user(), limit=20, client=_chained_db([])
        )
        assert result.items == []
        assert result.total == 0

    def test_resources_limit_past_the_maximum_is_422(self, authorized_student):
        with pytest.raises(AppError) as exc:
            resources_service.get_own_resources(
                _student_user(),
                limit=resources_service.MAX_RESOURCE_LIMIT + 1,
                client=MagicMock(),
            )
        assert exc.value.status_code == 422
        assert exc.value.code == "INVALID_FILTER"


class TestUnknownSourceTypeSafety:
    """An unknown source type must be projected, never crash, never leak."""

    def test_source_type_outside_the_known_vocabulary_is_projected_safely(self, authorized_student):
        row = {
            "knowledge_source_id": "60000000-0000-0000-0000-000000000009",
            "source_type": "mystery-bundle",
            "title": "Mystery material",
            "description": "Unknown vocabulary still renders.",
            "lifecycle_status": "published",
            "effective_from": "2026-09-01T00:00:00+00:00",
            "effective_until": None,
            "storage_bucket": "internal-bucket",
            "storage_object_key": "internal/object.pdf",
            "institution_id": TENANT_A,
            "created_by_user_id": "99999999-0000-0000-0000-000000000001",
        }
        result = resources_service.get_own_resources(
            _student_user(), limit=10, client=_chained_db([row])
        )
        assert len(result.items) == 1
        item = result.items[0]
        assert item.source_type == "mystery-bundle"
        dumped = item.model_dump(mode="json")
        assert set(dumped) == {
            "resource_id", "title", "description", "source_type",
            "effective_from", "effective_until",
        }
        assert "internal-bucket" not in str(dumped)
        assert "internal/object.pdf" not in str(dumped)


class TestProfileIsReadOnly:
    """No student-owned update contract exists → every /me route is GET-only."""

    def test_no_student_owned_mutation_route_exists(self):
        schema = app.openapi()
        paths = schema["paths"]
        # The three information surfaces this phase completes stay read-only.
        # (The separate Phase 6.11 notification read-receipt PATCH is an
        # existing, unrelated student-owned contract and is not touched here.)
        for suffix in ("academic-profile", "notices", "resources"):
            path = f"/api/v1/students/me/{suffix}"
            assert path in paths, path
            assert set(paths[path]) == {"get"}, path
