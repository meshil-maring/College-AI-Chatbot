"""Focused security + contract tests for Phase 7.13 institution management.

Covers the acceptance matrix directly:

* Super Admin can list / create / read / update / suspend / activate.
* Anonymous -> 401, and student / faculty / staff / admin -> 403 on EVERY
  platform institution endpoint (not just ``/platform/me``).
* Tenant isolation: an institution-scoped University Admin from Institution A is
  refused for Institution B on every verb, and can never grant a platform role.
* Input attacks: duplicate code, malformed code, empty name, unexpected fields,
  invalid institution id, and attempts to smuggle authorization-control fields.
* Suspension never deletes data and is idempotent.
* The migration reuses the canonical tenant and adds no duplicate entity.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

MIGRATION = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20261001010000_phase_7_13_super_admin_institution_management.sql"
)

INSTITUTION_ID = "40000000-0000-0000-0000-000000000001"
ACTOR_USER_ID = "10000000-0000-0000-0000-000000000001"
TARGET_USER_ID = "10000000-0000-0000-0000-000000000009"

INSTITUTION_ROW = {
    "institution_id": INSTITUTION_ID,
    "name": "Unico University",
    "code": "UNICO",
    "display_name": None,
    "logo_url": None,
    "primary_color": None,
    "secondary_color": None,
    "welcome_message": None,
    "status": "active",
    "is_active": True,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}

PLATFORM_ENDPOINTS = [
    ("GET", "/api/v1/platform/institutions"),
    ("POST", "/api/v1/platform/institutions"),
    ("GET", f"/api/v1/platform/institutions/{INSTITUTION_ID}"),
    ("PATCH", f"/api/v1/platform/institutions/{INSTITUTION_ID}"),
    ("POST", f"/api/v1/platform/institutions/{INSTITUTION_ID}/suspend"),
    ("POST", f"/api/v1/platform/institutions/{INSTITUTION_ID}/activate"),
    ("POST", f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins"),
]

_BODIES = {
    "POST": {"name": "X", "code": "XX"},
    "PATCH": {"name": "X"},
}

# The admin-assignment route takes an email, not the institution fields above.
_ASSIGN_BODY = {"email": "dean@unico.example"}


def _body_for(method: str, path: str) -> dict | None:
    if path.endswith("/admins"):
        return dict(_ASSIGN_BODY)
    return _BODIES.get(method)


def _principal(role: str, *, institution_id: str | None = None) -> dict:
    return {
        "user_id": ACTOR_USER_ID,
        "auth_user_id": "20000000-0000-0000-0000-000000000001",
        "email": "user@example.test",
        "roles": [role],
        "institution_id": institution_id,
    }


def _allow_super_admin():
    """Mock an active, platform-granted super_admin."""
    return patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "active", "has_platform_grant": True}),
    )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# 1. Authorization: anonymous denied, every tenant role forbidden
# ============================================================================


@pytest.mark.parametrize("method,path", PLATFORM_ENDPOINTS)
def test_anonymous_is_unauthorized_on_every_platform_endpoint(method, path) -> None:
    response = client.request(method, path, json=_body_for(method, path))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("role", ["student", "faculty", "staff", "admin"])
@pytest.mark.parametrize("method,path", PLATFORM_ENDPOINTS)
def test_every_tenant_role_is_forbidden_on_every_platform_endpoint(
    role, method, path
) -> None:
    """A University Admin of ANY institution is refused here, just like students.

    This is the tenant-isolation guarantee: the platform boundary is decided by
    the server-resolved super_admin role alone, never by the URL's institution id.
    """
    app.dependency_overrides[get_current_user] = lambda: _principal(
        role, institution_id=INSTITUTION_ID
    )
    response = client.request(method, path, json=_body_for(method, path))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_platform_create_is_forbidden_for_tenant_admin_of_another_institution() -> None:
    """Institution A's admin cannot create Institution B."""
    app.dependency_overrides[get_current_user] = lambda: _principal(
        "admin", institution_id=INSTITUTION_ID
    )
    response = client.post(
        "/api/v1/platform/institutions",
        json={"name": "Institution B", "code": "INSTB"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_super_admin_can_list_institutions() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.list_platform_institutions",
            return_value=[INSTITUTION_ROW],
        ),
        patch(
            "app.services.platform_institutions.platform_repo.list_institution_admin_counts",
            return_value={INSTITUTION_ID: 2},
        ),
    ):
        response = client.get("/api/v1/platform/institutions")

    assert response.status_code == 200
    assert response.json() == {
        "institutions": [
            {
                "id": INSTITUTION_ID,
                "code": "UNICO",
                "name": "Unico University",
                "status": "active",
                "is_active": True,
                "admin_count": 2,
            }
        ]
    }
    # No student or credential material may appear in the list projection.
    assert "students" not in response.text and "password" not in response.text


def test_super_admin_can_read_institution_detail() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=INSTITUTION_ROW,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.count_institution_admins",
            return_value=1,
        ),
    ):
        response = client.get(f"/api/v1/platform/institutions/{INSTITUTION_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "UNICO"
    assert body["status"] == "active"
    assert body["admin_count"] == 1
    # Organization linkage / internal columns are not part of the projection.
    assert "organization_id" not in body
    assert "join_code" not in body


def test_super_admin_can_create_institution() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.institution_code_taken",
            return_value=False,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_organization_id",
            return_value="50000000-0000-0000-0000-000000000001",
        ),
        patch(
            "app.services.platform_institutions.platform_repo.insert_platform_institution",
            return_value=INSTITUTION_ROW,
        ) as insert,
        patch(
            "app.services.platform_institutions.platform_repo.record_institution_audit"
        ) as audit,
        patch(
            "app.services.platform_institutions.platform_repo.count_institution_admins",
            return_value=0,
        ),
    ):
        response = client.post(
            "/api/v1/platform/institutions",
            json={"name": "Unico University", "code": "unico"},
        )

    assert response.status_code == 201
    assert response.json()["status"] == "active"
    # The code is normalized server-side, never trusted from the client.
    assert insert.call_args.kwargs["code"] == "UNICO"
    audit.assert_called_once()
    assert audit.call_args.kwargs["action"] == "institution_created"
    assert audit.call_args.kwargs["actor_user_id"] == ACTOR_USER_ID


def test_super_admin_can_update_institution_configuration() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    updated = {**INSTITUTION_ROW, "name": "Unico University (Renamed)"}
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=INSTITUTION_ROW,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.update_platform_institution",
            return_value=updated,
        ) as update,
        patch(
            "app.services.platform_institutions.platform_repo.record_institution_audit"
        ) as audit,
        patch(
            "app.services.platform_institutions.platform_repo.count_institution_admins",
            return_value=0,
        ),
    ):
        response = client.patch(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}",
            json={"name": "Unico University (Renamed)"},
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Unico University (Renamed)"
    written = update.call_args.args[2]
    assert written == {"name": "Unico University (Renamed)"}
    audit.assert_called_once()
    assert audit.call_args.kwargs["action"] == "institution_updated"

# ============================================================================
# 2. Lifecycle: suspend / activate
# ============================================================================


def test_super_admin_can_suspend_and_activate_institution() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    suspended = {**INSTITUTION_ROW, "status": "suspended", "is_active": False}
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=INSTITUTION_ROW,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.set_institution_status",
            return_value=suspended,
        ) as set_status,
        patch(
            "app.services.platform_institutions.platform_repo.record_institution_audit"
        ) as audit,
    ):
        response = client.post(f"/api/v1/platform/institutions/{INSTITUTION_ID}/suspend")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "suspended"
    assert body["is_active"] is False
    assert body["already_applied"] is False
    # Only the status column is written: no data is deleted on suspension.
    set_status.assert_called_once()
    assert set_status.call_args.args[2] == "suspended"
    assert "retained" in body["message"] and "revoked" in body["message"]
    assert audit.call_args.kwargs["action"] == "institution_suspended"

    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=suspended,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.set_institution_status",
            return_value=INSTITUTION_ROW,
        ) as set_status,
        patch(
            "app.services.platform_institutions.platform_repo.record_institution_audit"
        ) as audit,
    ):
        response = client.post(f"/api/v1/platform/institutions/{INSTITUTION_ID}/activate")

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert set_status.call_args.args[2] == "active"
    assert audit.call_args.kwargs["action"] == "institution_activated"


def test_suspension_is_idempotent_and_audited_as_already_applied() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    suspended = {**INSTITUTION_ROW, "status": "suspended", "is_active": False}
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=suspended,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.set_institution_status"
        ) as set_status,
        patch(
            "app.services.platform_institutions.platform_repo.record_institution_audit"
        ) as audit,
    ):
        response = client.post(f"/api/v1/platform/institutions/{INSTITUTION_ID}/suspend")

    assert response.status_code == 200
    assert response.json()["already_applied"] is True
    set_status.assert_not_called()
    assert audit.call_args.kwargs["result"] == "already_applied"


def test_unknown_institution_is_a_clean_404_for_every_platform_route() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    missing = uuid.uuid4()
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=None,
        ),
    ):
        for method, path in [
            ("GET", f"/api/v1/platform/institutions/{missing}"),
            ("PATCH", f"/api/v1/platform/institutions/{missing}"),
            ("POST", f"/api/v1/platform/institutions/{missing}/suspend"),
            ("POST", f"/api/v1/platform/institutions/{missing}/activate"),
            ("POST", f"/api/v1/platform/institutions/{missing}/admins"),
        ]:
            response = client.request(method, path, json=_body_for(method, path))
            assert response.status_code == 404, (method, path)
            assert response.json()["error"]["code"] == "INSTITUTION_NOT_FOUND"


# ============================================================================
# 3. Input attacks
# ============================================================================


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Duplicate", "code": "UNICO"},
        {"name": "Lowercase duplicate", "code": "unico"},
        {"name": "Padded duplicate", "code": "  UNICO  "},
    ],
)
def test_duplicate_institution_code_is_rejected_case_insensitively(payload) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.institution_code_taken",
            return_value=True,
        ),
    ):
        response = client.post("/api/v1/platform/institutions", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSTITUTION_CODE_TAKEN"


@pytest.mark.parametrize(
    "code",
    [
        "A",  # too short: the public route requires at least 2 characters
        "A" * 40,  # too long for the public route
        "UNICO UNIVERSITY",  # whitespace
        "UNICO/../ADMIN",  # path traversal
        "UNICO%",  # url-unsafe
        "UNICO;DROP",  # special character
        "ÜNICO",  # non-ascii
        "-UNICO",  # must start alphanumeric
        "",
    ],
)
def test_malformed_institution_code_is_rejected(code) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin():
        response = client.post(
            "/api/v1/platform/institutions", json={"name": "Test", "code": code}
        )
    assert response.status_code == 422


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_institution_name_is_rejected(name) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin():
        response = client.post(
            "/api/v1/platform/institutions", json={"name": name, "code": "TESTCO"}
        )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "X", "code": "XC1", "institution_id": INSTITUTION_ID},
        {"name": "X", "code": "XC2", "organization_id": str(uuid.uuid4())},
        {"name": "X", "code": "XC3", "role": "super_admin"},
        {"name": "X", "code": "XC4", "scope_type": "platform"},
        {"name": "X", "code": "XC5", "is_active": True},
        {"name": "X", "code": "XC6", "unexpected_field": "boom"},
    ],
)
def test_unexpected_and_authorization_control_fields_are_forbidden(payload) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin():
        response = client.post("/api/v1/platform/institutions", json=payload)
    assert response.status_code == 422


def test_update_cannot_change_status_or_identity_columns() -> None:
    """Lifecycle and identity are not settable through the generic PATCH."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin():
        response = client.patch(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}",
            json={"status": "suspended"},
        )
    assert response.status_code == 422
    with _allow_super_admin():
        response = client.patch(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}",
            json={"institution_id": str(uuid.uuid4())},
        )
    assert response.status_code == 422
    with _allow_super_admin():
        response = client.patch(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}",
            json={"organization_id": str(uuid.uuid4())},
        )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"logo_url": "javascript:alert(1)"},
        {"logo_url": "data:image/svg+xml;base64,AAAA"},
        {"primary_color": "red; background:url(http://x)"},
        {"primary_color": "#GGGGGG"},
    ],
)
def test_unsafe_branding_values_are_rejected(payload) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin():
        response = client.post(
            "/api/v1/platform/institutions",
            json={"name": "Branded", "code": "BRANDED", **payload},
        )
    assert response.status_code == 422


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "123", "12345678-1234-1234-1234-12345678901z"])
def test_malformed_institution_id_is_rejected(bad_id) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin():
        response = client.get(f"/api/v1/platform/institutions/{bad_id}")
    assert response.status_code == 422


def test_assignment_payload_cannot_request_a_privileged_role() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    for payload in (
        {"email": "a@b.test", "role": "super_admin"},
        {"email": "a@b.test", "scope_type": "platform"},
        {"email": "a@b.test", "institution_id": INSTITUTION_ID},
        {"email": "a@b.test", "password": "hunter2"},
    ):
        with _allow_super_admin():
            response = client.post(
                f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins", json=payload
            )
        assert response.status_code == 422, payload

# ============================================================================
# 4. University Admin assignment (controlled, non-provisioning)
# ============================================================================


def test_super_admin_can_assign_existing_account_as_university_admin() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    user_row = {"id": TARGET_USER_ID, "email": "dean@unico.example", "status": "active"}
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=INSTITUTION_ROW,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.get_user_by_email",
            return_value=user_row,
        ) as lookup,
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_organization_id",
            return_value="50000000-0000-0000-0000-000000000001",
        ),
        patch(
            "app.services.platform_institutions.platform_repo.has_institution_admin_grant",
            return_value=False,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.assign_institution_admin"
        ) as assign,
        patch(
            "app.services.platform_institutions.platform_repo.record_institution_audit"
        ) as audit,
    ):
        response = client.post(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins",
            json={"email": "DEAN@unico.example"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["assigned"] is True and body["already_assigned"] is False
    assert body["admin"]["institution_id"] == INSTITUTION_ID
    assert body["admin"]["scope"] == "institution"
    # The email is normalized server-side before the account lookup.
    lookup.assert_called_once()
    assert lookup.call_args.args[1] == "dean@unico.example"
    # The grant is structurally institution-scoped.
    assign.assert_called_once()
    assert str(assign.call_args.kwargs["institution_id"]) == INSTITUTION_ID
    assert audit.call_args.kwargs["action"] == "admin_assigned"
    assert audit.call_args.kwargs["target_user_id"] == TARGET_USER_ID


def test_assignment_is_idempotent_for_an_already_assigned_admin() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    user_row = {"id": TARGET_USER_ID, "email": "dean@unico.example", "status": "active"}
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=INSTITUTION_ROW,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.get_user_by_email",
            return_value=user_row,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_organization_id",
            return_value="50000000-0000-0000-0000-000000000001",
        ),
        patch(
            "app.services.platform_institutions.platform_repo.has_institution_admin_grant",
            return_value=True,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.assign_institution_admin"
        ) as assign,
        patch(
            "app.services.platform_institutions.platform_repo.record_institution_audit"
        ) as audit,
    ):
        response = client.post(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins",
            json={"email": "dean@unico.example"},
        )

    assert response.status_code == 201
    assert response.json()["already_assigned"] is True
    assign.assert_not_called()
    assert audit.call_args.kwargs["result"] == "already_applied"


def test_assignment_never_creates_an_auth_account() -> None:
    """A missing account is a clean 404; nothing is provisioned silently."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=INSTITUTION_ROW,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.get_user_by_email",
            return_value=None,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.assign_institution_admin"
        ) as assign,
    ):
        response = client.post(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins",
            json={"email": "nobody@unico.example"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"
    assign.assert_not_called()


def test_assignment_rejects_an_inactive_account() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        patch(
            "app.services.platform_institutions.platform_repo.get_platform_institution",
            return_value=INSTITUTION_ROW,
        ),
        patch(
            "app.services.platform_institutions.platform_repo.get_user_by_email",
            return_value={"id": TARGET_USER_ID, "email": "x@y.example", "status": "inactive"},
        ),
    ):
        response = client.post(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins",
            json={"email": "x@y.example"},
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


# ============================================================================
# 5. Repository invariants
# ============================================================================


def test_identity_and_scope_columns_are_not_mutable() -> None:
    from app.repositories.platform_institutions import MUTABLE_INSTITUTION_FIELDS

    assert "institution_id" not in MUTABLE_INSTITUTION_FIELDS
    assert "organization_id" not in MUTABLE_INSTITUTION_FIELDS
    assert "status" not in MUTABLE_INSTITUTION_FIELDS
    assert "is_active" not in MUTABLE_INSTITUTION_FIELDS
    assert {"name", "code"} <= MUTABLE_INSTITUTION_FIELDS


def test_platform_projection_excludes_organization_and_contact_columns() -> None:
    from app.repositories.platform_institutions import PLATFORM_INSTITUTION_COLUMNS

    for sensitive in (
        "organization_id",
        "join_code",
        "email",
        "address",
        "phone",
    ):
        assert sensitive not in PLATFORM_INSTITUTION_COLUMNS


def test_audit_record_never_accepts_credential_fields() -> None:
    """The audit signature only accepts non-sensitive summary data."""
    import inspect

    from app.repositories.platform_institutions import record_institution_audit

    params = set(inspect.signature(record_institution_audit).parameters)
    assert params == {
        "client",
        "actor_user_id",
        "action",
        "institution_id",
        "result",
        "target_user_id",
        "details",
    }
    assert not params & {"password", "token", "secret", "service_role_key"}


def test_admin_role_projection_uses_the_real_roles_primary_key() -> None:
    """Regression guard: the roles primary key column is ``id``, not ``role_id``.

    ``user_roles.role_id`` is the foreign key that REFERENCES ``roles(id)``.
    Selecting a non-existent ``role_id`` column from ``roles`` raises a PostgREST
    error at runtime, which would silently break every admin count and the
    admin-assignment grant. Confirmed against a live local database.
    """
    from unittest.mock import MagicMock

    from app.repositories.platform_institutions import _admin_role

    db = MagicMock()
    roles = db.table.return_value
    roles.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "id": "71200000-0000-0000-0000-000000000002",
        "name": "admin",
        "is_active": True,
    }
    with patch("app.repositories.platform_institutions.Client", return_value=db):
        role = _admin_role(db)

    assert role is not None
    assert role["id"] == "71200000-0000-0000-0000-000000000002"
    roles.select.assert_called_with("id, name, is_active")
    roles.select.return_value.eq.assert_called_with("name", "admin")


# ============================================================================
# 6. Migration contract
# ============================================================================


def test_migration_extends_the_canonical_tenant_without_duplicate_entities() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    # Extends the EXISTING institutions table additively.
    assert 'ALTER TABLE "public"."institutions"' in sql
    for column in (
        "display_name",
        "logo_url",
        "primary_color",
        "secondary_color",
        "welcome_message",
    ):
        assert f'"{column}"' in sql
    # No duplicate tenant/college/university/organization entity is created.
    assert "CREATE TABLE" not in sql.split("platform_institution_audit_log")[0]
    assert 'CREATE TABLE IF NOT EXISTS "public"."institutions"' not in sql
    assert 'CREATE TABLE IF NOT EXISTS "public"."universities"' not in sql
    assert 'CREATE TABLE IF NOT EXISTS "public"."colleges"' not in sql
    assert 'CREATE TABLE IF NOT EXISTS "public"."tenants"' not in sql
    # No separate slug column: `code` remains the single routing identifier.
    assert '"slug"' not in sql
    # Deterministic case-insensitive uniqueness for the routing code.
    assert "institutions_code_upper_key" in sql
    assert 'ON "public"."institutions" (upper("code"))' in sql


def test_migration_audit_ledger_is_service_role_only_and_secret_free() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert 'REVOKE ALL ON TABLE "public"."platform_institution_audit_log"' in sql
    assert 'FROM PUBLIC, "anon", "authenticated"' in sql
    assert 'GRANT SELECT, INSERT ON TABLE "public"."platform_institution_audit_log" TO "service_role"' in sql
    for action in (
        "institution_created",
        "institution_updated",
        "institution_suspended",
        "institution_activated",
        "admin_assigned",
    ):
        assert f"'{action}'" in sql
    # No destructive operation against tenant-owned data.
    for destructive in ("DROP TABLE", "DELETE FROM", "TRUNCATE"):
        assert destructive not in sql
    # Never touches Auth or stores credentials.
    assert "auth.users" not in sql.lower()


def test_platform_organization_insert_is_idempotent() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert 'INSERT INTO "public"."organizations"' in sql
    assert "COLLEGE-AI-PLATFORM" in sql
    assert 'ON CONFLICT ("organization_code") DO NOTHING' in sql


def test_public_routes_are_untouched_by_this_phase() -> None:
    """Phase 7.13 must not add a second public-chat backend."""
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "CREATE FUNCTION" not in sql
    assert "CREATE OR REPLACE FUNCTION" not in sql
    assert "public_chat" not in sql.lower()
