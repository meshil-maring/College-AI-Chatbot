"""Staff/Faculty account status changes (moved from the Phase 7.23 roster tests).

``set_active`` became ``member_status.set_status`` when suspension was added;
these keep the original tenant, protected-role and status guarantees.
"""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.services.admin import member_status as status_service

INST_A = UUID("40000000-0000-0000-0000-000000000001")
INST_B = UUID("40000000-0000-0000-0000-000000000002")
ADMIN_A = "10000000-0000-0000-0000-000000000001"
USER_A = UUID("20000000-0000-0000-0000-000000000001")


def _actor() -> dict:
    return {"user_id": ADMIN_A, "institution_id": str(INST_A), "roles": ["admin"]}


def test_cross_tenant_deactivation_fails_safely() -> None:
    grants = [{"scope_type": "institution", "scope_id": str(INST_B), "roles": {"name": "staff"}}]
    with patch.object(status_service, "get_admin_client", return_value=object()), patch.object(
        status_service.repo, "get_user", return_value={"id": str(USER_A), "status": "active"}
    ), patch.object(status_service.repo, "list_user_grants", return_value=grants), patch.object(
        status_service.repo, "set_user_status"
    ) as update:
        with pytest.raises(AppError) as caught:
            status_service.set_status(_actor(), INST_A, USER_A, "deactivated")
    assert caught.value.code == "MEMBERSHIP_NOT_FOUND"
    update.assert_not_called()


def test_admin_or_platform_role_cannot_be_modified_through_roster() -> None:
    grants = [
        {"scope_type": "institution", "scope_id": str(INST_A), "roles": {"name": "staff"}},
        {"scope_type": "platform", "scope_id": None, "roles": {"name": "super_admin"}},
    ]
    with patch.object(status_service, "get_admin_client", return_value=object()), patch.object(
        status_service.repo, "get_user", return_value={"id": str(USER_A), "status": "active"}
    ), patch.object(status_service.repo, "list_user_grants", return_value=grants):
        with pytest.raises(AppError) as caught:
            status_service.set_status(_actor(), INST_A, USER_A, "deactivated")
    assert caught.value.code == "PROTECTED_ROLE"


@pytest.mark.parametrize(
    ("active", "current", "desired"),
    [(False, "active", "deactivated"), (True, "deactivated", "active")],
)
def test_lifecycle_uses_existing_user_status(active: bool, current: str, desired: str) -> None:
    grants = [{"scope_type": "institution", "scope_id": str(INST_A), "roles": {"name": "staff"}}]
    update = MagicMock(return_value=True)
    with patch.object(status_service, "get_admin_client", return_value=object()), patch.object(
        status_service.repo, "get_user", return_value={"id": str(USER_A), "status": current}
    ), patch.object(status_service.repo, "list_user_grants", return_value=grants), patch.object(
        status_service.repo, "set_user_status", update
    ), patch.object(status_service, "record_admin_action"):
        result = status_service.set_status(_actor(), INST_A, USER_A, desired)
    assert result.status == desired
    assert update.call_args.kwargs["status"] == desired
