"""Admin router composition. Feature routers share one permission boundary."""

from fastapi import APIRouter, Depends

from app.api.admin import (
    overview,
    memberships,
    knowledge_sources,
    documents,
    faqs,
    notices,
    audit,
    permissions,
)
from app.api.admin import student_approvals
from app.api.admin.dependencies import _authorize_admin_endpoint


router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(_authorize_admin_endpoint)],
)

router.include_router(overview.router)
router.include_router(memberships.router)
router.include_router(knowledge_sources.router)
router.include_router(documents.router)
router.include_router(faqs.router)
router.include_router(notices.router)
router.include_router(audit.router)
router.include_router(permissions.router)
router.include_router(student_approvals.router)
