from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.academics.academic_structure import router
from app.core.errors import AppError, app_error_handler
from app.core.security import get_current_user
from app.repositories.academics import academic_setup as base_repository
from app.repositories.platform import tenancy
from app.services.academics import academic_structure as service
from app.services.auth import authorization
from ..support import TENANT, ORGANIZATION, SETUP_PERMISSIONS, principal


@pytest.fixture
def api():
    application = FastAPI()
    application.add_exception_handler(AppError, app_error_handler)
    application.include_router(router, prefix="/api/v1")
    user = principal(SETUP_PERMISSIONS)
    application.dependency_overrides[get_current_user] = lambda: user
    with (
        patch.object(authorization, "get_admin_client", return_value=MagicMock()),
        patch.object(tenancy, "get_institution_by_id", return_value={
            "institution_id": TENANT, "status": "active", "is_active": True,
        }),
        patch.object(base_repository, "get_institution_lifecycle", return_value={
            "institution_id": TENANT, "organization_id": ORGANIZATION, "status": "active", "is_active": True,
        }),
        patch.object(base_repository, "get_organization_lifecycle", return_value={
            "organization_id": ORGANIZATION, "status": "active",
        }),
        patch.object(service, "get_admin_client", return_value=MagicMock()) as database,
        TestClient(application) as client,
    ):
        yield client, user, database
