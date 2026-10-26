"""Tenant joins must work with the export's indirectly scoped descendants."""
from unittest.mock import MagicMock

import pytest

from app.repositories.academics import academic_setup as repository
from app.schemas.academics.academic_setup import AcademicEntity as Entity
from .support import DEPARTMENT, TENANT


def query_client(data):
    client = MagicMock()
    query = client.table.return_value
    for method in ("select", "eq", "order", "range", "maybe_single"):
        getattr(query, method).return_value = query
    query.execute.return_value.data = data
    return client, query


@pytest.mark.parametrize("entity", list(Entity))
def test_lists_apply_every_tenant_join_and_pagination(entity):
    client, query = query_client([])
    assert repository.list_records(client, TENANT, entity) == []
    client.table.assert_called_once_with(entity.value)
    assert [call.args for call in query.eq.call_args_list] == [(path, TENANT) for path in repository.JOINS[entity][1]]
    query.range.assert_called_once_with(0, 499)
    if entity not in {Entity.departments, Entity.academic_years}:
        assert "!inner(" in repository.PROJECTIONS[entity]
        assert "institution_id" not in repository.FIELDS[entity]


@pytest.mark.parametrize("entity", list(Entity))
def test_lookup_scopes_before_primary_key(entity):
    client, query = query_client(None)
    assert repository.get_record(client, TENANT, entity, DEPARTMENT) is None
    assert query.eq.call_args_list[-1].args == (repository.PRIMARY_KEYS[entity], DEPARTMENT)
    assert query.eq.call_args_list[0].args == (repository.JOINS[entity][1][0], TENANT)


def test_join_data_is_removed_and_tenant_context_is_server_derived():
    client, _ = query_client([{"program_id": "program", "department": {"institution_id": TENANT}}])
    assert repository.list_records(client, TENANT, Entity.programs) == [{"program_id": "program", "institution_id": TENANT}]


@pytest.mark.parametrize("entity", list(Entity))
def test_all_writes_use_exported_rpc_with_server_actor_and_tenant(entity):
    client = MagicMock()
    payload = {"is_active": False}
    repository.manage_record(client, "actor", TENANT, entity, DEPARTMENT, payload)
    client.rpc.assert_called_once_with("manage_academic_master_record", {
        "p_actor_user_id": "actor", "p_institution_id": TENANT, "p_entity": entity.value,
        "p_record_id": DEPARTMENT, "p_payload": payload,
    })
