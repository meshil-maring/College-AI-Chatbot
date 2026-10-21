"""Admin router composition. Feature routers share one permission boundary."""

from fastapi import APIRouter, Depends

from app.api.admin import (
    overview,
    memberships,
    knowledge_sources,
    documents,
    faqs,
    notices,
    students,
    results,
    attendance,
    audit,
    permissions,
    faculty,
    student_workspace,
)
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
router.include_router(students.router)
router.include_router(results.router)
router.include_router(attendance.router)
router.include_router(audit.router)
router.include_router(permissions.router)
router.include_router(faculty.router)
router.include_router(student_workspace.router)
