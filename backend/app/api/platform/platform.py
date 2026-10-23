"""Platform router composition for nonacademic institution administration."""

from fastapi import APIRouter, Depends

from app.api.platform import (
    institution_routes,
    institution_invitations,
    platform_audit,
    super_admin_invitations,
)
from app.api.platform.dependencies import _authorize_platform_endpoint

router = APIRouter(
    tags=["platform"],
    dependencies=[Depends(_authorize_platform_endpoint)],
)
router.include_router(institution_routes.router)
router.include_router(institution_invitations.router)
router.include_router(platform_audit.router)
router.include_router(super_admin_invitations.router)
