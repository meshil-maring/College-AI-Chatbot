"""Authentication rejects incomplete server-owned permission projections."""

from copy import deepcopy

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.errors import AppError, app_error_handler
from app.core.security.identity import get_current_user

from .support import ACTOR, TENANT_A, AsyncMock, patch, pytest


def _projection():
    return {
        "user_id": ACTOR,
        "status": "active",
        "roles": ["admin"],
        "role_assignments": [
            {
                "role": "admin",
                "scope_type": "institution",
                "scope_id": TENANT_A,
                "is_active": True,
                "permissions": ["users.read"],
            }
        ],
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
        "effective_permissions": ["*"],
        "direct_permission_grants": [
            {"institution_id": TENANT_A, "permission": "documents.create"}
        ],
    }


@pytest.fixture
def authenticate():
    application = FastAPI()
    application.add_exception_handler(AppError, app_error_handler)

    @application.get("/protected")
    def protected(user=Depends(get_current_user)):
        return user

    client = TestClient(application)

    def request(record):
        with (
            patch("app.core.security.tokens.verify_jwt", return_value={"sub": "auth"}),
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=record),
            ) as lookup,
        ):
            response = client.get(
                "/protected", headers={"Authorization": "Bearer token"}
            )
        lookup.assert_awaited_once_with("auth", include_permissions=True)
        return response

    return request


@pytest.mark.parametrize("field", ["permissions_resolved", "scoped_permissions_resolved"])
@pytest.mark.parametrize("value", [None, False, 0, 1, "true", [], {}])
def test_invalid_provenance_is_forbidden(authenticate, field, value):
    record = _projection()
    record[field] = value
    response = authenticate(record)
    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "FORBIDDEN",
            "message": "You do not have permission to perform this action",
        }
    }


@pytest.mark.parametrize(
    "missing",
    [
        ("permissions_resolved",),
        ("scoped_permissions_resolved",),
        ("permissions_resolved", "scoped_permissions_resolved"),
    ],
)
def test_incomplete_authentication_projection_is_forbidden(authenticate, missing):
    record = _projection()
    for field in missing:
        record.pop(field)
    response = authenticate(record)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("status", [None, "inactive", "deactivated"])
def test_account_status_is_checked_before_permission_provenance(authenticate, status):
    record = _projection()
    record["status"] = status
    record.pop("scoped_permissions_resolved")
    response = authenticate(record)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_complete_projection_uses_exact_scope_and_preserves_provenance(authenticate):
    record = _projection()
    before = deepcopy(record)
    response = authenticate(record)
    assert response.status_code == 200
    user = response.json()
    assert user["institution_id"] == TENANT_A
    assert user["effective_permissions"] == ["users.read"]
    assert user["permissions_resolved"] is True
    assert user["scoped_permissions_resolved"] is True
    assert user["role_assignments"] == record["role_assignments"]
    assert user["direct_permission_grants"] == record["direct_permission_grants"]
    assert record == before
