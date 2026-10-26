"""Offline service validation, safe database errors and authority boundaries."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.academics.academic_setup import AcademicEntity as Entity
from app.services.academics import academic_setup as service
from .support import DEPARTMENT, FOREIGN_TENANT, ORGANIZATION, TENANT, YEAR, academic_year, principal


@pytest.fixture
def database():
    with (
        patch.object(service, "get_admin_client", return_value=MagicMock()) as factory,
        patch.object(service.repository, "get_institution_lifecycle", return_value={
            "institution_id": TENANT, "organization_id": ORGANIZATION,
            "status": "active", "is_active": True,
        }),
        patch.object(service.repository, "get_organization_lifecycle", return_value={
            "organization_id": ORGANIZATION, "status": "active",
        }),
    ):
        yield factory


def test_catalogue_omits_unreadable_entities_and_does_not_infer_permissions(database):
    with patch.object(service.repository, "list_records", return_value=[]) as listing:
        result = service.get_setup(principal(["departments.read"]))
    assert list(result.records) == [Entity.departments, Entity.programs]
    assert result.manageable == []
    assert listing.call_count == 2


@pytest.mark.parametrize("permissions", [[], ["departments.read"]])
def test_revoked_manage_permissions_deny_before_database_access(permissions):
    with patch.object(service, "get_admin_client") as database, pytest.raises(AppError) as error:
        service.manage_record(principal(permissions), Entity.departments, {"name": "CSE"})
    assert error.value.code == "FORBIDDEN"
    database.assert_not_called()


def test_foreign_scope_permissions_cannot_authorize_own_tenant():
    user = principal([])
    user["role_assignments"].append({
        "role": "admin", "scope_type": "organization", "scope_id": FOREIGN_TENANT,
        "permissions": ["departments.manage"], "is_active": True,
    })
    with pytest.raises(AppError) as error:
        service.manage_record(user, Entity.departments, {"name": "CSE", "code": "CSE"})
    assert error.value.code == "FORBIDDEN"


def test_foreign_record_returns_not_found_and_never_calls_writer(database):
    with (
        patch.object(service.repository, "get_record", return_value=None) as lookup,
        patch.object(service.repository, "manage_record") as writer,
        pytest.raises(AppError) as error,
    ):
        service.manage_record(principal(), Entity.departments, {"name": "Changed"}, DEPARTMENT)
    assert error.value.code == "ACADEMIC_NOT_FOUND"
    assert lookup.call_args.args[1:3] == (TENANT, Entity.departments)
    writer.assert_not_called()


@pytest.mark.parametrize("parent", [None, {"is_active": False}])
def test_program_requires_active_same_tenant_parent(database, parent):
    with (
        patch.object(service.repository, "get_record", return_value=parent),
        patch.object(service.repository, "manage_record") as writer,
        pytest.raises(AppError) as error,
    ):
        service.manage_record(principal(), Entity.programs, {
            "name": "B.Tech CSE", "code": "BTCSE", "department_id": DEPARTMENT,
            "degree_type": "B.Tech", "duration_years": 4,
        })
    assert error.value.code == "ACADEMIC_REFERENCE_INVALID"
    writer.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"end_date": "2026-06-01"}, {"start_date": "2027-07-01"},
    {"is_active": False},
])
def test_partial_year_patch_validates_against_persisted_dates_and_current_status(database, changes):
    with (
        patch.object(service.repository, "get_record", return_value=academic_year(is_current=True)),
        patch.object(service.repository, "manage_record") as writer,
        pytest.raises(ValidationError),
    ):
        service.manage_record(principal(), Entity.academic_years, changes, YEAR)
    writer.assert_not_called()


def test_valid_partial_year_patch_preserves_omitted_fields(database):
    with (
        patch.object(service.repository, "get_record", return_value=academic_year()),
        patch.object(service.repository, "manage_record", return_value=academic_year()) as writer,
    ):
        service.manage_record(principal(), Entity.academic_years, {"name": "Academic 2026–2027"}, YEAR)
    assert writer.call_args.args[-1] == {"name": "Academic 2026–2027"}


@pytest.mark.parametrize("db_code,status,public_code", [
    ("23505", 409, "ACADEMIC_DUPLICATE"),
    ("23P01", 409, "ACADEMIC_DATE_CONFLICT"),
    ("23514", 422, "ACADEMIC_HIERARCHY_INVALID"),
    ("23503", 422, "ACADEMIC_REFERENCE_INVALID"),
    ("22003", 422, "ACADEMIC_INPUT_INVALID"),
    ("22023", 422, "ACADEMIC_INPUT_INVALID"),
    ("P0002", 404, "ACADEMIC_NOT_FOUND"),
    ("42501", 403, "FORBIDDEN"),
    ("42P01", 503, "ACADEMIC_SCHEMA_UNAVAILABLE"),
    ("PGRST202", 503, "ACADEMIC_SCHEMA_UNAVAILABLE"),
    ("unknown", 500, "ACADEMIC_OPERATION_FAILED"),
])
def test_atomic_writer_errors_are_safe_and_typed(database, db_code, status, public_code):
    failure = Exception("secret database detail")
    failure.code = db_code
    with (
        patch.object(service.repository, "manage_record", side_effect=failure),
        pytest.raises(AppError) as error,
    ):
        service.manage_record(principal(), Entity.departments, {"name": "CSE", "code": "CSE"})
    assert (error.value.status_code, error.value.code) == (status, public_code)
    assert "secret" not in error.value.message


def test_department_deactivation_retains_id_and_uses_atomic_writer(database):
    row = {"department_id": DEPARTMENT, "institution_id": TENANT, "is_active": False}
    with (
        patch.object(service.repository, "get_record", return_value={**row, "is_active": True}),
        patch.object(service.repository, "manage_record", return_value=row) as writer,
    ):
        assert service.manage_record(
            principal(), Entity.departments, {"is_active": False}, DEPARTMENT
        ) == row
    assert writer.call_args.args[-2:] == (DEPARTMENT, {"is_active": False})


@pytest.mark.parametrize("row", [
    None,
    {},
    {"department_id": DEPARTMENT, "institution_id": FOREIGN_TENANT},
])
def test_invalid_or_foreign_write_responses_are_rejected(database, row):
    with (
        patch.object(service.repository, "manage_record", return_value=row),
        pytest.raises(AppError) as error,
    ):
        service.manage_record(principal(), Entity.departments, {"name": "CSE", "code": "CSE"})
    assert (error.value.status_code, error.value.code) == (500, "ACADEMIC_OPERATION_FAILED")
