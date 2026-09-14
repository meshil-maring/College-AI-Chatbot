"""Phase 6.9 - Student-specific data access security tests.

Verifies the secure student identity chain and data access boundary.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.services import student_context
client = TestClient(app, raise_server_exceptions=False)
TENANT_A = "a1111111-0000-0000-0000-000000000001"
TENANT_B = "b2222222-0000-0000-0000-000000000002"
STUDENT_USER_ID = "71000000-0000-0000-0000-000000000001"
STUDENT_ID = "30000000-0000-0000-0000-0000000000151"
OTHER_STUDENT_ID = "30000000-0000-0000-0000-0000000000152"
STUDENT_AUTH_USER_ID = "61000000-0000-0000-0000-000000000001"
EMAIL = "student@college.edu"
OTHER_EMAIL = "other@college.edu"


def _student_user(user_id=STUDENT_USER_ID, tenant=TENANT_A, auth_user_id=STUDENT_AUTH_USER_ID, email=EMAIL):
    return {"user_id": user_id, "auth_user_id": auth_user_id, "email": email, "roles": ["student"], "institution_id": tenant}


def _student_profile(student_id=STUDENT_ID, user_id=STUDENT_USER_ID,
                     institution_id=TENANT_A, approval_status="approved", is_active=True):
    return {"student_id": student_id, "user_id": user_id, "institution_id": institution_id,
            "student_number": "STU100", "approval_status": approval_status, "is_active": is_active, "email": EMAIL}


def _db_with_student_profile(profile=None):
    db = MagicMock()
    if profile is None:
        profile = _student_profile()
    (db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute).return_value = MagicMock(data=profile)
    return db


def _db_without_profile():
    db = MagicMock()
    (db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute).return_value = MagicMock(data=None)
    return db


@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.pop(get_current_user, None)

class TestStudentContextResolution:
    """TEST GROUP 1: Student context resolution (6 tests)."""

    def test_resolves_student_context_from_jwt_user_id(self):
        """1. Authenticated student context resolves correctly."""
        db = _db_with_student_profile()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            context = student_context.get_student_context(_student_user())
        assert context["student_id"] == STUDENT_ID
        assert context["user_id"] == STUDENT_USER_ID
        assert context["auth_user_id"] == STUDENT_AUTH_USER_ID
        assert context["institution_id"] == TENANT_A
        assert context["approval_status"] == "approved"
        assert context["is_active"] is True

    def test_context_contains_only_safe_fields(self):
        """Context only exposes whitelisted fields, no sensitive data."""
        db = _db_with_student_profile()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            context = student_context.get_student_context(_student_user())
        allowed_fields = set(student_context.CONTEXT_FIELDS)
        assert set(context.keys()) == allowed_fields
        assert "password" not in context
        assert "token" not in context

    def test_returns_404_when_no_profile(self):
        """3. Missing student profile fails safely."""
        db = _db_without_profile()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with pytest.raises(AppError) as exc:
                student_context.get_student_context(_student_user())
        assert exc.value.status_code == 404
        assert exc.value.code == "STUDENT_PROFILE_NOT_FOUND"

    def test_pending_student_not_eligible(self):
        """19. Inactive/unapproved students follow intended access rule."""
        db = _db_with_student_profile(_student_profile(approval_status="pending"))
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with pytest.raises(AppError) as exc:
                student_context.get_student_context(_student_user())
        assert exc.value.status_code == 403
        assert exc.value.code == "STUDENT_NOT_APPROVED"

    def test_inactive_student_not_eligible(self):
        """19. Inactive students cannot access data."""
        db = _db_with_student_profile(_student_profile(is_active=False))
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with pytest.raises(AppError) as exc:
                student_context.get_student_context(_student_user())
        assert exc.value.status_code == 403
        assert exc.value.code == "STUDENT_INACTIVE"

    def test_non_student_has_no_context(self):
        """2. Authenticated non-student has no student context."""
        admin_user = _student_user(
            user_id="71000000-0000-0000-0000-000000000099",
            auth_user_id="61000000-0000-0000-0000-000000000099",
            email="admin@college.edu",
        )
        admin_user["roles"] = ["admin"]
        db = _db_without_profile()
        with patch("app.services.student_context.get_admin_client", return_value=db):
            with pytest.raises(AppError) as exc:
                student_context.get_student_context(admin_user)
        assert exc.value.code == "STUDENT_PROFILE_NOT_FOUND"

class TestProfileAccess:
    """TEST GROUP 2: Student profile access (3 tests)."""

    def test_student_can_access_own_profile(self):
        """4. Student can access own profile."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        with patch("app.services.student_data.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/profile")
        assert response.status_code == 200
        assert response.json()["student_id"] == STUDENT_ID

    def test_profile_ignores_client_supplied_student_id(self):
        """11. Student cannot override identity using student_id."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        with patch("app.services.student_data.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/profile", params={"student_id": OTHER_STUDENT_ID})
        assert response.status_code == 200
        assert response.json()["student_id"] == STUDENT_ID

    def test_profile_404_without_profile(self):
        """3. Missing student profile returns 404."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_without_profile()
        with patch("app.services.student_data.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/profile")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


class TestAttendanceAccess:
    """TEST GROUP 3: Attendance access (3 tests)."""

    def test_student_can_access_own_attendance(self):
        """5. Student can access own attendance."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        rows = [{"student_attendance_id": str(uuid4()), "student_id": STUDENT_ID,
                "institution_id": TENANT_A, "date": "2026-09-01", "status": "present"}]
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.admin_academics.list_student_attendance", return_value=rows) as ml:
                response = client.get("/api/v1/students/me/attendance")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["student_id"] == STUDENT_ID
        ml.assert_called_once()
        assert ml.call_args.args[1] == STUDENT_ID

    def test_attendance_ignores_client_supplied_student_id(self):
        """11-16. Client-supplied identity params are ignored."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.admin_academics.list_student_attendance", return_value=[]) as ml:
                response = client.get("/api/v1/students/me/attendance", params={"student_id": OTHER_STUDENT_ID})
        assert response.status_code == 200
        assert ml.call_args.args[1] == STUDENT_ID

    def test_attendance_404_without_profile(self):
        """Missing student profile returns 404 for attendance."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_without_profile()
        with patch("app.services.student_data.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/attendance")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"

class TestResultsAccess:
    """TEST GROUP 4: Results access (5 tests)."""

    def test_student_can_access_own_results(self):
        """7. Student can access own results."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        rows = [{"student_result_id": str(uuid4()), "student_id": STUDENT_ID,
                "institution_id": TENANT_A, "status": "published", "sgpa": 3.5}]
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.admin_academics.list_student_results", return_value=rows) as ml:
                response = client.get("/api/v1/students/me/results")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["student_id"] == STUDENT_ID
        ml.assert_called_once()
        assert ml.call_args.args[1] == STUDENT_ID

    def test_student_cannot_access_other_students_result(self):
        """8. Student cannot access another student result detail."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        result_id = str(uuid4())
        db = _db_with_student_profile(profile)
        other = {"student_result_id": result_id, "student_id": OTHER_STUDENT_ID,
                 "institution_id": TENANT_A, "status": "published"}
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.results.get_student_result_with_items", return_value=other):
                response = client.get(f"/api/v1/students/me/results/{result_id}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"

    def test_student_cannot_access_other_students_test_results(self):
        """9. Student cannot access another student test results."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        other = [{"test_result_id": str(uuid4()), "student_id": OTHER_STUDENT_ID, "status": "published"}]
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.admin_academics.list_test_results", return_value=other) as ml:
                response = client.get("/api/v1/students/me/test-results")
        assert response.status_code == 200
        assert ml.call_args.args[1] == STUDENT_ID

    def test_results_404_without_profile(self):
        """Missing student profile returns 404 for results."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        db = _db_without_profile()
        with patch("app.services.student_data.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/results")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"

    def test_published_result_behavior_intact(self):
        """20. Published/unpublished result behavior remains intact."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        all_r = [{"student_result_id": "1", "student_id": STUDENT_ID, "status": "published"},
                {"student_result_id": "2", "student_id": STUDENT_ID, "status": "draft"},
                {"student_result_id": "3", "student_id": STUDENT_ID, "status": "withheld"}]
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.admin_academics.list_student_results", return_value=all_r):
                response = client.get("/api/v1/students/me/results")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["student_result_id"] == "1"
        assert data[0]["status"] == "published"

class TestCrossStudentSecurity:
    """TEST GROUP 5: Cross-student security (1 test)."""

    def test_cannot_override_via_request_params(self):
        """11-16. Student cannot override identity using various identifiers."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.admin_academics.list_student_results", return_value=[]) as ml:
                response = client.get("/api/v1/students/me/results", params={
                    "student_id": OTHER_STUDENT_ID,
                    "user_id": "71000000-0000-0000-0000-000000000099",
                    "institution_id": TENANT_B,
                    "email": OTHER_EMAIL,
                    "register_number": "OTHERREG",
                    "university_roll_number": "OTHERROLL",
                })
        assert response.status_code == 200
        assert ml.call_args.args[1] == STUDENT_ID


class TestCrossTenantSecurity:
    """TEST GROUP 6: Cross-tenant security (2 tests)."""

    def test_cross_tenant_access_fails(self):
        """17. Cross-tenant access fails."""
        app.dependency_overrides[get_current_user] = lambda: _student_user(tenant=TENANT_A)
        profile = _student_profile(institution_id=TENANT_A)
        result_id = str(uuid4())
        db = _db_with_student_profile(profile)
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.results.get_student_result_with_items", return_value={
                "student_result_id": result_id, "student_id": STUDENT_ID,
                "institution_id": TENANT_B, "status": "published"}):
                response = client.get(f"/api/v1/students/me/results/{result_id}")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"

    def test_tenant_assertion_on_profile(self):
        """Tenant assertion prevents cross-tenant profile access."""
        app.dependency_overrides[get_current_user] = lambda: _student_user(tenant=TENANT_A)
        profile = _student_profile(institution_id=TENANT_B)
        db = _db_with_student_profile(profile)
        with patch("app.services.student_data.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/profile")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"


class TestMalformedIds:
    """TEST GROUP 7: Malformed IDs (1 test)."""

    def test_malformed_result_id_rejected(self):
        """21. Malformed IDs fail safely."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.get("/api/v1/students/me/results/not-a-uuid")
        assert response.status_code == 422

class TestRoleBoundaries:
    """TEST GROUP 8: Role boundaries (2 tests)."""

    def test_student_can_access_me_endpoints(self):
        """Students can access /students/me/* endpoints."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        with patch("app.services.student_data.get_admin_client", return_value=db):
            for path in ["/api/v1/students/me/profile", "/api/v1/students/me/results",
                         "/api/v1/students/me/test-results", "/api/v1/students/me/attendance"]:
                response = client.get(path)
                assert response.status_code in (200, 404), f"Failed at {path}"

    def test_admin_cannot_access_student_me_endpoints(self):
        """18. Unauthorized roles are rejected appropriately."""
        admin_user = _student_user(
            user_id="71000000-0000-0000-0000-000000000099",
            auth_user_id="61000000-0000-0000-0000-000000000099",
            email="admin@college.edu",
        )
        admin_user["roles"] = ["admin"]
        app.dependency_overrides[get_current_user] = lambda: admin_user
        db = _db_without_profile()
        with patch("app.services.student_data.get_admin_client", return_value=db):
            response = client.get("/api/v1/students/me/profile")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


class TestExistingSecurityContracts:
    """TEST GROUP 9: Existing Phase 6.7/6.8 security contracts (3 tests)."""

    def test_publication_filter_intact(self):
        """20. Published/unpublished result behavior remains intact."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        profile = _student_profile()
        db = _db_with_student_profile(profile)
        rows = [{"student_result_id": "1", "student_id": STUDENT_ID, "status": "published"},
                {"student_result_id": "2", "student_id": STUDENT_ID, "status": "draft"},
                {"student_result_id": "3", "student_id": STUDENT_ID, "status": "withheld"}]
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.admin_academics.list_student_results", return_value=rows):
                response = client.get("/api/v1/students/me/results")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "published"

    def test_tenant_guard_intact(self):
        """24. Existing Phase 6.7/6.8 security contracts remain intact."""
        app.dependency_overrides[get_current_user] = lambda: _student_user(tenant=TENANT_A)
        profile = _student_profile(institution_id=TENANT_A)
        result_id = str(uuid4())
        db = _db_with_student_profile(profile)
        with patch("app.services.student_data.get_admin_client", return_value=db):
            with patch("app.repositories.results.get_student_result_with_items", return_value={
                "student_result_id": result_id, "student_id": STUDENT_ID,
                "institution_id": TENANT_B, "status": "published"}):
                response = client.get(f"/api/v1/students/me/results/{result_id}")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"

    def test_identity_params_never_trusted(self):
        """24. /me endpoints have no student_id parameter in OpenAPI."""
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        openapi = client.get("/openapi.json").json()
        me_paths = [p for p in openapi["paths"] if p.startswith("/api/v1/students/me/")]
        for path in me_paths:
            for method in ("get", "post", "patch", "put", "delete"):
                if method in openapi["paths"][path]:
                    params = openapi["paths"][path][method].get("parameters", [])
                    for param in params:
                        pname = param.get("name", "")
                        assert pname not in ("student_id", "user_id", "auth_user_id"), \
                            f"Found untrusted identity param {pname} in {method.upper()} {path}"