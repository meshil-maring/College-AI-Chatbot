from .support import (
    TENANT_A,
    _active_institution_authorization,
    _user,
    assert_tenant_object,
    scope_tenant,
)


def test_scope_tenant_defaults_to_own_tenant():
    from uuid import UUID

    assert scope_tenant(_user("student", TENANT_A), None) == UUID(TENANT_A)


def test_assert_tenant_object_allows_global_rows():
    assert_tenant_object(_user("student", TENANT_A), None)
