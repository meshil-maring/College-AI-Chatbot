"""Admin permissions endpoints."""

from uuid import UUID

from fastapi import Depends

from app.core.security import user_tenant_id
from app.schemas.auth.phase81 import StaffPermissionGrantChange
from app.services.auth import phase81_rbac
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/permissions/delegable-staff")
def get_delegable_staff_permissions(
    _current_user: dict = Depends(_ADMIN),
) -> dict:
    return {"permissions": phase81_rbac.list_delegable_permissions()}


@router.get("/staff/{user_id}/permissions")
def get_staff_permissions(
    user_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    return phase81_rbac.list_staff_permissions(
        user_id, UUID(str(user_tenant_id(current_user)))
    )


@router.post("/staff/{user_id}/permissions")
def grant_staff_permissions(
    user_id: UUID,
    body: StaffPermissionGrantChange,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    return phase81_rbac.change_staff_permissions(
        current_user,
        UUID(str(user_tenant_id(current_user))),
        user_id,
        body.permission_codes,
        grant=True,
    )


@router.delete("/staff/{user_id}/permissions")
def revoke_staff_permissions(
    user_id: UUID,
    body: StaffPermissionGrantChange,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    return phase81_rbac.change_staff_permissions(
        current_user,
        UUID(str(user_tenant_id(current_user))),
        user_id,
        body.permission_codes,
        grant=False,
    )
