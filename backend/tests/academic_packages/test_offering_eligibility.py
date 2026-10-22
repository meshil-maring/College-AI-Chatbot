"""Named eligibility is bounded tenant metadata, never a synthetic legacy link."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from app.services.academics import academic_setup as service
from tests.test_academic_setup import ACTOR, BASE, FOREIGN, TENANT, api

ELIGIBLE = {"program_id": "p", "course_id": "c", "semester_id": "s", "source": "named_curriculum"}


def seed(db, *, eligibility=None, error=None):
    source = {
        "departments": [{"department_id": "d"}], "academic_batches": [],
        "programs": [{"program_id": "p", "department_id": "d"}],
        "courses": [{"course_id": "c", "department_id": "d"}],
        "academic_years": [{"academic_year_id": "y"}],
        "semesters": [{"semester_id": "s", "academic_year_id": "y"}],
        "program_courses": [], "course_offerings": [], "sections": [],
    }
    def table(entity):
        query = MagicMock()
        for method in ("select", "order", "eq", "in_", "range"):
            getattr(query, method).return_value = query
        query.execute.return_value = SimpleNamespace(data=source[entity])
        return query
    db.table.side_effect = table
    db.rpc.side_effect = None
    db.rpc.return_value.execute.side_effect = error
    db.rpc.return_value.execute.return_value.data = [] if eligibility is None else eligibility


def test_named_subjects_supply_offering_eligibility_without_fabricating_legacy_links(api):
    client, db, *_ = api
    seed(db, eligibility=[ELIGIBLE, ELIGIBLE, {**ELIGIBLE, "program_id": "foreign"}])
    response = client.get(f"{BASE}?institution_id={FOREIGN}&actor_user_id={FOREIGN}")
    assert response.status_code == 200
    assert response.json()["offering_eligibility"] == [ELIGIBLE]
    assert response.json()["records"]["program_courses"] == []
    db.rpc.assert_called_once_with("academic_package_offering_eligibility", {
        "p_actor_user_id": ACTOR, "p_institution_id": TENANT,
    })


def test_nonreaders_receive_no_named_metadata_or_rpc_access(api):
    client, db, user, _ = api
    seed(db, eligibility=[ELIGIBLE])
    user["effective_permissions"] = ["departments.read"]
    response = client.get(BASE)
    assert response.status_code == 200 and response.json()["offering_eligibility"] == []
    db.rpc.assert_not_called()


@pytest.mark.parametrize("code", ["PGRST202", "42883"])
def test_only_the_explicit_absent_optional_rpc_preserves_legacy_setup(api, code):
    client, db, *_ = api
    seed(db, error=APIError({"code": code, "message": "function academic_package_offering_eligibility is absent", "details": "", "hint": ""}))
    response = client.get(BASE)
    assert response.status_code == 200 and response.json()["offering_eligibility"] == []


@pytest.mark.parametrize("code,status", [("42501", 403), ("42P01", 503), ("PGRST202", 503), ("XX000", 500)])
def test_other_authorization_or_internal_schema_failures_do_not_fall_back(api, code, status):
    client, db, *_ = api
    seed(db, error=APIError({"code": code, "message": "private internal helper error", "details": "", "hint": ""}))
    response = client.get(BASE)
    assert response.status_code == status and "private internal" not in response.text


@pytest.mark.parametrize("projection", [{"saved": True}, [{**ELIGIBLE, "source": "legacy"}], [ELIGIBLE] * 5001])
def test_invalid_or_unbounded_metadata_is_rejected(api, projection):
    client, db, *_ = api
    seed(db, eligibility=projection)
    response = client.get(BASE)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "DATABASE_PROJECTION_INVALID"
