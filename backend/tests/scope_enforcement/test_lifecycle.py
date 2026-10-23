"""Test lifecycle."""

from __future__ import annotations

from app.core.errors import AppError

from app.services.auth import authorization as authz

from app.services.platform import tenancy as tenancy_svc

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .database import (
    _db,
)

from .fixtures import (
    _active_institution_authorization,
)

from .state import (
    _base_state,
)

from .support import (
    INST_ADMIN,
    ORG_ADMIN,
    _inst_ctx,
    _org_ctx,
)


def test_17_inactive_institution_denied():
    """Suspended (is_active=False) institution -> TENANT_INACTIVE."""
    ctx = _inst_ctx()
    current_user = {"user_id": INST_ADMIN, "institution_id": None}
    state = _base_state(inst_status="suspended")
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(), current_user, ctx
            )
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_INACTIVE"


def test_18_pending_institution_denied():
    """Pending institution (is_active=False) -> TENANT_INACTIVE."""
    ctx = _inst_ctx()
    current_user = {"user_id": INST_ADMIN, "institution_id": None}
    state = _base_state(inst_status="pending")
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(), current_user, ctx
            )
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_INACTIVE"


def test_19_rejected_institution_denied():
    """Rejected institution -> TENANT_INACTIVE."""
    ctx = _inst_ctx()
    current_user = {"user_id": INST_ADMIN, "institution_id": None}
    state = _base_state(inst_status="rejected")
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(), current_user, ctx
            )
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_INACTIVE"


def test_19b_missing_institution_row_denied():
    """An institution-scoped user whose institution row vanished fails closed."""
    ctx = _inst_ctx()
    state = _base_state()
    state["institutions"] = {}  # orphaned scope: institution row gone
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(),
                {"user_id": INST_ADMIN, "institution_id": None},
                ctx,
            )
    assert excinfo.value.code == "TENANT_INACTIVE"


def test_20_rejected_organization_denied():
    """A rejected/suspended organization's admin can no longer act."""
    ctx = _org_ctx()
    current_user = {"user_id": ORG_ADMIN, "institution_id": None}
    for status in ("rejected", "suspended"):
        state = _base_state(org_status=status)
        with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
            with pytest.raises(AppError) as excinfo:
                authz.assert_active_tenant_context(
                    tenancy_svc.get_admin_client(), current_user, ctx
                )
        assert excinfo.value.status_code == 403
        assert excinfo.value.code == "ORGANIZATION_INACTIVE"


def test_20b_missing_organization_row_denied():
    """An org-scoped user whose organization row vanished fails closed."""
    ctx = _org_ctx()
    state = _base_state()
    state["organizations"] = {}
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)):
        with pytest.raises(AppError) as excinfo:
            authz.assert_active_tenant_context(
                tenancy_svc.get_admin_client(),
                {"user_id": ORG_ADMIN, "institution_id": None},
                ctx,
            )
    assert excinfo.value.code == "ORGANIZATION_INACTIVE"


def test_20c_pending_organization_still_manageable():
    """A pending organization's admin may still act while awaiting platform review."""
    ctx = _org_ctx()
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(_base_state())):
        authz.assert_active_tenant_context(
            tenancy_svc.get_admin_client(),
            {"user_id": ORG_ADMIN, "institution_id": None},
            ctx,
        )
