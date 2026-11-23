"""Real hierarchy validation rejects foreign, inactive and inconsistent parents."""
from unittest.mock import patch

import pytest

from app.core.errors import AppError
from app.schemas.academics.academic_setup import AcademicEntity as Entity
from app.services.academics import parent_validation as hierarchy
from .support import FOREIGN_TENANT, TENANT, setup_rows


@pytest.fixture
def rows():
    records = setup_rows()
    def lookup(client, tenant, entity, identifier):
        assert tenant == TENANT
        row = records[entity]
        return row if str(identifier) in row.values() else None
    with patch.object(hierarchy.repository, "get_record", side_effect=lookup), patch.object(
        hierarchy.repository, "list_records", side_effect=lambda client, tenant, entity: [records[entity]]
    ):
        yield records


@pytest.mark.parametrize("entity", list(Entity))
def test_valid_export_hierarchy_is_accepted(rows, entity):
    hierarchy.validate_structure_parents(None, TENANT, entity, rows[entity], None)


@pytest.mark.parametrize("entity,field", [(Entity.programs,"department_id"), (Entity.courses,"department_id"), (Entity.semesters,"academic_year_id")])
def test_unknown_or_foreign_parent_is_rejected(rows, entity, field):
    with pytest.raises(AppError):
        hierarchy.validate_structure_parents(None, TENANT, entity, {**rows[entity], field: FOREIGN_TENANT}, None)


def test_semester_dates_must_fit_the_year_even_on_update(rows):
    with pytest.raises(AppError):
        hierarchy.validate_structure_parents(None, TENANT, Entity.semesters, {"start_date":"2025-01-01"}, rows["semesters"])


def test_inactive_ancestry_does_not_prevent_child_deactivation(rows):
    rows["academic_years"]["is_active"] = False
    hierarchy.validate_structure_parents(None, TENANT, Entity.semesters, {"is_active":False}, rows["semesters"])


def test_inactive_parent_blocks_child_reactivation(rows):
    rows["departments"]["is_active"] = False
    with pytest.raises(AppError):
        hierarchy.validate_structure_parents(None, TENANT, Entity.courses, {"is_active":True}, rows["courses"])
