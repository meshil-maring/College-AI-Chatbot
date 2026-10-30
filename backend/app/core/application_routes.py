"""Register feature routers without changing their public routes."""

from fastapi import FastAPI
from app.api.platform.platform import router as platform_router
from app.api.invitations.admin_invitations import router as admin_invitations_router
from app.api.invitations.super_admin_registration import (
    router as super_admin_registration_router,
)
from app.api.email.mailgun_webhooks import router as mailgun_webhooks_router
from app.api.knowledge.ingestion import router as ingestion_router
from app.api.knowledge.resources import router as knowledge_resources_router
from app.api.knowledge.resource_uploads import router as knowledge_uploads_router
from app.api.auth.auth import router as auth_router
from app.api.auth.registration import router as registration_router
from app.api.ai.conversations import router as conversations_router
from app.api.admin.admin import router as admin_router
from app.api.platform.organizations import router as organizations_router
from app.api.platform.institutions import router as institutions_router
from app.api.auth.users import router as users_router
from app.api.auth.student_auth import router as student_auth_router
from app.api.students.students import router as students_router
from app.api.students.student_notifications import (
    router as student_notifications_router,
)
from app.api.auth.dev_auth import router as dev_auth_router
from app.api.auth.identity import router as identity_router
from app.api.academics.academic_setup import router as academic_setup_router
from app.api.academics.academic_structure import router as academic_structure_router
from app.api.academics.semester_registration import router as semester_registration_router


def register_feature_routes(app: FastAPI) -> None:
    app.include_router(ingestion_router, prefix="/api/v1")
    # Literal upload/retry paths must precede the revision/{action} route.
    app.include_router(knowledge_uploads_router, prefix="/api/v1")
    app.include_router(knowledge_resources_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(student_auth_router, prefix="/api/v1")
    app.include_router(registration_router, prefix="/api/v1")
    app.include_router(organizations_router, prefix="/api/v1")
    app.include_router(institutions_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(academic_setup_router, prefix="/api/v1")
    app.include_router(academic_structure_router, prefix="/api/v1")
    app.include_router(semester_registration_router, prefix="/api/v1")
    app.include_router(students_router, prefix="/api/v1")
    app.include_router(student_notifications_router, prefix="/api/v1")
    app.include_router(dev_auth_router, prefix="/api/v1")  # DEVELOPMENT / TESTING ONLY
    app.include_router(platform_router, prefix="/api/v1")
    # Phase 7.14: the invitation boundary is token-authorized, not session-
    # authorized, so it is mounted as its own router rather than under /platform.
    app.include_router(admin_invitations_router, prefix="/api/v1")
    app.include_router(super_admin_registration_router, prefix="/api/v1")
    app.include_router(mailgun_webhooks_router, prefix="/api/v1")
    app.include_router(identity_router)
