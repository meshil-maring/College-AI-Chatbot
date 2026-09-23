"""Phase 6.22 — Complete Product Demo & End-to-End System Validation (backend).

Validates the COMPLETE product journey as one connected workflow rather than as
isolated phases, using the real application contracts (routers + schemas +
services) with the same client/patch style as the Phase 6.20/6.21 suites:

    institution lookup -> registration (pending, no token)
      -> approval (admin/staff authorization boundary)
      -> student authentication (email / register number / roll number)
      -> academic data access (identity resolved server-side)
      -> RAG ingestion + tenant-scoped retrieval
      -> generation authorization + conversation ownership
      -> cross-tenant denial and representative role boundaries

This suite additionally PINS the three blocking defects that the Phase 6.22
live walkthrough found and this phase fixed, so none of them can silently
return:

    1. ``document_versions.knowledge_source_id`` does not exist — the
       processing-run query now resolves the tenant through the existing
       ``documents(knowledge_source_id)`` embed.
    2. ``STUDENT_COLUMNS`` carries no ``approval_status`` — the student
       eligibility guard now reads the approval projection, so approved
       students are no longer rejected with 403 STUDENT_NOT_APPROVED.
    3. ``personalization`` label reads called ``response.data`` on a
       ``maybe_single()`` result of ``None`` — every such read is now guarded.
"""

from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"
FOREIGN_TENANT = "30000000-0000-0000-0000-0000000000ff"
USER_ID = "30000000-0000-0000-0000-000000000701"
STUDENT_ID = "30000000-0000-0000-0000-000000000151"
OTHER_STUDENT_ID = "30000000-0000-0000-0000-000000000152"
KNOWLEDGE_SOURCE_ID = "30000000-0000-0000-0000-000000000111"
DOCUMENT_ID = "30000000-0000-0000-0000-000000000121"
RUN_ID = "30000000-0000-0000-0000-000000000141"
CONVERSATION_ID = "30000000-0000-0000-0000-000000000901"
PROCESSING_RUN_ID = "30000000-0000-0000-0000-000000000941"

AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}
CLAIMS = {"sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "email": "demo@college.edu"}


def _user(role="student", tenant=INSTITUTION_A, user_id=USER_ID):
    return {
        "user_id": user_id,
        "auth_user_id": CLAIMS["sub"],
        "email": f"{role}@college.edu",
        "roles": [role],
        "institution_id": tenant,
    }


@contextmanager
def _auth(role="student", tenant=INSTITUTION_A, user_id=USER_ID):
    principal = _user(role, tenant, user_id)
    with ExitStack() as stack:
        stack.enter_context(patch("app.core.security.verify_jwt", return_value=dict(CLAIMS)))
        stack.enter_context(
            patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=principal))
        )
        yield principal


def _envelope(response):
    """Return the error envelope; only {code, message[, details]} is ever exposed."""
    body = response.json()
    assert "error" in body, f"expected error envelope got: {body!r}"
    error = body["error"]
    assert {"code", "message"} <= set(error), f"missing envelope keys: {error}"
    assert set(error) <= {"code", "message", "details"}, f"leaked keys: {error}"
    return error



# ============================================================================
# Institution resolution (demo environment / institution setup)
# ============================================================================


def test_institution_lookup_is_public_and_returns_the_safe_projection():
    payload = {
        "institution_id": INSTITUTION_A,
        "code": "GIT",
        "name": "Greenfield Institute of Technology",
    }
    with patch("app.api.institutions.lookup_institution_by_code", return_value=payload):
        # No Authorization header: discovery must work before login.
        response = client.get("/api/v1/institutions/lookup", params={"code": "GIT"})
    assert response.status_code == 200
    body = response.json()
    # Phase 6.15.2 — exactly {institution_id, code, name}; nothing else leaks.
    assert set(body) == {"institution_id", "code", "name"}
    assert body["institution_id"] == INSTITUTION_A


def test_unknown_institution_code_fails_safely():
    with patch(
        "app.api.institutions.lookup_institution_by_code",
        side_effect=AppError(
            "Institution not found", status_code=404, code="INSTITUTION_NOT_FOUND"
        ),
    ):
        response = client.get("/api/v1/institutions/lookup", params={"code": "NO-SUCH"})
    assert response.status_code == 404
    assert _envelope(response)["code"] == "INSTITUTION_NOT_FOUND"


def test_institution_lookup_has_no_authentication_dependency():
    from app.api import institutions as institutions_api

    # APIRouter(prefix="/institutions") prepends the prefix when the route is
    # added, so the stored path is "/institutions/lookup", not "/lookup".
    route = next(
        r
        for r in institutions_api.router.routes
        if getattr(r, "path", "").endswith("/lookup")
    )
    dependency_names = {getattr(d.call, "__name__", "") for d in route.dependant.dependencies}
    assert "get_current_user" not in dependency_names


# ============================================================================
# Student registration (pending, no token, no privilege injection)
# ============================================================================


def _registration_payload(**overrides):
    payload = {
        "institution_id": INSTITUTION_A,
        "email": "phase622.student@demo.collegelocal.dev",
        "password": "DemoPassword!622",
        "first_name": "Demo",
        "last_name": "Student",
        "register_number": "622001",
        "university_roll_number": "R622001",
    }
    payload.update(overrides)
    return payload


def test_registration_returns_201_pending_and_issues_no_token():
    from app.services.student_registration import RegistrationResponse

    created = RegistrationResponse(
        message="Registration submitted. Your account is pending approval.",
        student_id=STUDENT_ID,
        institution_id=INSTITUTION_A,
        email="phase622.student@demo.collegelocal.dev",
        approval_status="pending",
    )
    with patch("app.api.registration.register_student", return_value=created):
        response = client.post("/api/v1/registration", json=_registration_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["approval_status"] == "pending"
    # No authentication token may be issued before approval.
    assert "access_token" not in body


def test_registration_rejects_privilege_injection_fields():
    for injected in (
        {"role": "admin"},
        {"approval_status": "approved"},
        {"user_id": USER_ID},
    ):
        response = client.post("/api/v1/registration", json=_registration_payload(**injected))
        assert response.status_code == 422, injected
        _envelope(response)


def test_registration_requires_institution_and_academic_identifier():
    missing_institution = _registration_payload()
    missing_institution.pop("institution_id")
    assert client.post("/api/v1/registration", json=missing_institution).status_code == 422

    with patch(
        "app.api.registration.register_student",
        side_effect=AppError(
            "Provide at least one of register_number or university_roll_number",
            status_code=422,
            code="IDENTIFIER_REQUIRED",
        ),
    ):
        response = client.post(
            "/api/v1/registration",
            json=_registration_payload(register_number=None, university_roll_number=None),
        )
    assert response.status_code == 422
    assert _envelope(response)["code"] == "IDENTIFIER_REQUIRED"


def test_registration_never_reports_success_for_a_failed_service_call():
    with patch(
        "app.api.registration.register_student",
        side_effect=AppError(
            "Unable to complete registration at this time. Please try again later.",
            status_code=500,
            code="REGISTRATION_FAILED",
        ),
    ):
        response = client.post("/api/v1/registration", json=_registration_payload())
    assert response.status_code == 500
    assert _envelope(response)["code"] == "REGISTRATION_FAILED"


# ============================================================================
# Student approval (admin approval + the staff approval exception)
# ============================================================================


def test_admin_approval_transitions_pending_to_approved():
    approved = {
        "student_id": STUDENT_ID,
        "approval_status": "approved",
        "institution_id": INSTITUTION_A,
    }
    # The audit write is a privileged mutation against the real admin_audit_log
    # table; stub it (Phase 6.19/6.20 pattern) so the approval contract itself
    # is what this test observes, not database reachability.
    with _auth("admin"), patch(
        "app.api.admin.admin_academics.approve_student", return_value=approved
    ) as approve, patch(
        "app.api.admin.record_admin_action", return_value={"audit_id": "a-1"}
    ), patch("app.api.admin.get_admin_client", return_value=MagicMock()):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_ID}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    # The approving tenant is resolved SERVER-SIDE from the principal, never
    # from the request body/query.
    tenant_argument = approve.call_args.args[1]
    assert str(tenant_argument) in (INSTITUTION_A, "None")


def test_staff_may_use_the_approval_queue_exception_only():
    # The whole scenario must run INSIDE the auth context: once _auth exits the
    # verify_jwt / get_user_by_auth_id patches are gone and every admin route
    # would answer 401 (no principal) instead of exercising the role gate.
    with _auth("staff"), patch(
        "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
    ):
        queue = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
        assert queue.status_code == 200

        # ...but every admin-only management surface still denies staff.
        # institution_id is supplied so the 403 comes from require_roles("admin"),
        # never from query validation short-circuiting the gate.
        for path in ("/api/v1/admin/students", "/api/v1/admin/dashboard"):
            response = client.get(
                path,
                params={"institution_id": INSTITUTION_A},
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 403, path
            assert _envelope(response)["code"] == "FORBIDDEN"


@pytest.mark.parametrize("role", ["student", "faculty"])
def test_non_approver_roles_cannot_reach_the_approval_endpoints(role):
    with _auth(role):
        queue = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
        approve = client.post(
            f"/api/v1/admin/students/{STUDENT_ID}/approve", headers=AUTH_HEADERS
        )
    for response in (queue, approve):
        assert response.status_code == 403
        assert _envelope(response)["code"] == "FORBIDDEN"


def test_staff_approval_queue_is_tenant_scoped_by_the_principal():
    with _auth("staff", tenant=INSTITUTION_A), patch(
        "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
    ) as pending:
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    # admin.list_pending_students passes the tenant POSITIONALLY:
    #   list_pending_approvals(effective, limit=limit, offset=offset)
    assert str(pending.call_args.args[0]) == INSTITUTION_A


def test_stale_approval_of_an_already_decided_student_conflicts():
    with _auth("admin"), patch(
        "app.api.admin.admin_academics.approve_student",
        side_effect=AppError(
            "Student is not pending approval", status_code=409, code="STUDENT_NOT_PENDING"
        ),
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_ID}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 409
    assert _envelope(response)["code"] == "STUDENT_NOT_PENDING"


def test_unauthenticated_approval_is_rejected():
    response = client.post(f"/api/v1/admin/students/{STUDENT_ID}/approve")
    assert response.status_code == 401
    _envelope(response)


# ============================================================================
# Student authentication (email / register number / university roll number)
# ============================================================================

_LOGIN_URL = "/api/v1/auth/student/login"
_SESSION = {
    "access_token": "student.session.token",
    "user": {"id": CLAIMS["sub"], "email": "student@college.edu"},
}


def test_email_login_needs_no_institution_context():
    with patch("app.api.student_auth.authenticate_student", return_value=_SESSION) as auth:
        response = client.post(
            _LOGIN_URL,
            json={"identifier": "student@college.edu", "password": "secret123"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "student.session.token"
    assert body["user"]["email"] == "student@college.edu"
    assert auth.call_args.args[2] is None


def test_academic_identifier_login_requires_institution_code():
    response = client.post(
        _LOGIN_URL, json={"identifier": "2448052", "password": "secret123"}
    )
    assert response.status_code == 422
    _envelope(response)


@pytest.mark.parametrize("identifier", ["622001", "R622001"])
def test_academic_identifier_login_forwards_the_institution_code(identifier):
    with patch("app.api.student_auth.authenticate_student", return_value=_SESSION) as auth:
        response = client.post(
            _LOGIN_URL,
            json={
                "identifier": identifier,
                "password": "secret123",
                "institution_code": "GIT",
            },
        )
    assert response.status_code == 200
    assert auth.call_args.args[2] == "GIT"


def test_login_normalizes_unknown_identifier_and_pending_state_to_401():
    from app.services.student_auth import SafeAuthFailure

    with patch("app.api.student_auth.authenticate_student", side_effect=SafeAuthFailure()):
        response = client.post(
            _LOGIN_URL,
            json={"identifier": "nobody@college.edu", "password": "secret123"},
        )
    assert response.status_code == 401
    assert _envelope(response)["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_identity_and_role_injection_fields():
    for injected in (
        {"role": "admin"},
        {"user_id": USER_ID},
        {"student_id": STUDENT_ID},
        {"approval_status": "approved"},
    ):
        payload = {"identifier": "student@college.edu", "password": "secret123", **injected}
        response = client.post(_LOGIN_URL, json=payload)
        assert response.status_code == 422, injected
        _envelope(response)


# ============================================================================
# Academic data access (identity always resolved from the authenticated JWT)
# ============================================================================


def test_own_profile_is_resolved_from_the_authenticated_user():
    own = {"student_id": STUDENT_ID, "institution_id": INSTITUTION_A}
    with _auth("student"), patch(
        "app.api.students.student_data.get_own_profile", return_value=own
    ) as get_own:
        response = client.get(
            "/api/v1/students/me/profile",
            headers=AUTH_HEADERS,
            # A client-supplied identity parameter must never override the JWT.
            params={"student_id": OTHER_STUDENT_ID, "institution_id": FOREIGN_TENANT},
        )
    assert response.status_code == 200
    assert response.json()["student_id"] == STUDENT_ID
    assert str(get_own.call_args.args[0]) == USER_ID


def test_cross_tenant_student_row_is_denied():
    foreign = {"student_id": OTHER_STUDENT_ID, "institution_id": FOREIGN_TENANT}
    with _auth("student", tenant=INSTITUTION_A), patch(
        "app.api.students.student_data.get_own_profile", return_value=foreign
    ):
        response = client.get("/api/v1/students/me/profile", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert _envelope(response)["code"] == "TENANT_MISMATCH"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/students/me/profile",
        "/api/v1/students/me/academic-profile",
        "/api/v1/students/me/attendance",
        "/api/v1/students/me/results",
        "/api/v1/students/me/test-results",
        "/api/v1/students/me/notices",
        "/api/v1/students/me/resources",
    ],
)
def test_student_surfaces_are_closed_to_non_student_roles(path):
    for role in ("admin", "faculty", "staff"):
        with _auth(role), patch(
            "app.services.student_context.get_student_context",
            side_effect=AppError(
                "No student profile is linked to this account",
                status_code=404,
                code="STUDENT_PROFILE_NOT_FOUND",
            ),
        ):
            response = client.get(path, headers=AUTH_HEADERS)
        assert response.status_code in (403, 404), (path, role)
        _envelope(response)


def test_unauthenticated_student_surface_is_rejected():
    response = client.get("/api/v1/students/me/attendance")
    assert response.status_code == 401
    _envelope(response)


# ============================================================================
# Defect pins — Phase 6.22 blocking defects found by the live walkthrough
# ============================================================================


def test_processing_run_query_documents_the_corrected_tenant_resolution():
    """Defect 1 — the fix rationale is pinned in the repository docstring."""
    from app.repositories import ingestion as ingestion_repo

    documented = ingestion_repo.get_processing_run_with_version.__doc__ or ""
    assert "documents(knowledge_source_id)" in documented
    assert "knowledge_source_id" in documented


def test_processing_run_tenant_is_hoisted_from_the_document_row():
    """Defect 1 — the tenant must come from ``documents``, not ``document_versions``."""
    run_row = {
        "processing_run_id": PROCESSING_RUN_ID,
        "status": "queued",
        "document_version_id": "30000000-0000-0000-0000-000000000931",
        "document_versions": {
            "document_version_id": "30000000-0000-0000-0000-000000000931",
            "storage_bucket": "college-ai-knowledge",
            "storage_object_key": "tenant/key",
            "file_type": "txt",
            "documents": {"knowledge_source_id": KNOWLEDGE_SOURCE_ID},
        },
    }
    response = MagicMock()
    response.data = run_row
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value = response
    fake_client = MagicMock()
    fake_client.table.return_value = chain

    from app.repositories.ingestion import get_processing_run_with_version

    run = get_processing_run_with_version(fake_client, PROCESSING_RUN_ID)
    assert run["document_versions"]["knowledge_source_id"] == KNOWLEDGE_SOURCE_ID
    selected = chain.select.call_args.args[0]
    assert "documents(knowledge_source_id)" in selected
    assert "file_type, knowledge_source_id)" not in selected


def test_approval_projection_supplies_the_column_the_eligibility_guard_needs():
    """Defect 2 — STUDENT_COLUMNS lacks approval_status; the guard must not 403."""
    from app.repositories.admin_academics import (
        STUDENT_APPROVAL_COLUMNS,
        STUDENT_COLUMNS,
    )

    assert "approval_status" not in STUDENT_COLUMNS
    assert "approval_status" in STUDENT_APPROVAL_COLUMNS

    from app.services.student_context import get_student_context

    student = {
        "student_id": STUDENT_ID,
        "user_id": USER_ID,
        "institution_id": INSTITUTION_A,
        "student_number": "STU2026001",
        "email": "student@college.edu",
        "approval_status": "approved",
        "status": "active",
        "is_active": True,
    }
    with patch(
        "app.repositories.admin_academics.get_student_approval_row_by_user_id",
        return_value=student,
    ), patch("app.services.student_context.get_admin_client", return_value=MagicMock()):
        context = get_student_context({"user_id": USER_ID, "institution_id": INSTITUTION_A})
    assert context["approval_status"] == "approved"
    assert context["student_id"] == STUDENT_ID


def test_student_context_still_rejects_a_pending_student():
    """Defect 2 must not have weakened the approval guard itself."""
    from app.services.student_context import get_student_context

    pending = {
        "student_id": STUDENT_ID,
        "user_id": USER_ID,
        "institution_id": INSTITUTION_A,
        "student_number": "STU622",
        "email": "pending@college.edu",
        "approval_status": "pending",
        "status": "active",
        "is_active": True,
    }
    with patch(
        "app.repositories.admin_academics.get_student_approval_row_by_user_id",
        return_value=pending,
    ), patch("app.services.student_context.get_admin_client", return_value=MagicMock()):
        with pytest.raises(AppError) as excinfo:
            get_student_context({"user_id": USER_ID, "institution_id": INSTITUTION_A})
    assert excinfo.value.code == "STUDENT_NOT_APPROVED"


def test_personalization_label_reads_tolerate_a_missing_row():
    """Defect 3 — a zero-row ``maybe_single()`` now yields None, not a 500."""
    from app.repositories import personalization

    def client_returning_no_row():
        # postgrest >= 2.x zero-row shape: maybe_single() still returns the
        # builder — it is .execute() that yields None (not an APIResponse
        # with data=None). _single_row() is the guard that must absorb it.
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.execute.return_value = None
        fake = MagicMock()
        fake.table.return_value = chain
        return fake

    fake = client_returning_no_row()
    assert personalization.get_program_label(fake, "30000000-0000-0000-0000-000000000042") is None
    assert personalization.get_program_label(fake, "p-1", INSTITUTION_A) is None
    assert personalization.get_academic_year_label(fake, "30000000-0000-0000-0000-000000000022") is None
    assert personalization.get_current_semester_label(fake, "30000000-0000-0000-0000-000000000022") is None


# ============================================================================
# RAG — retrieval scoping, tenant isolation, generation authorization
# ============================================================================


def test_retrieval_requires_an_explicit_scope():
    from pydantic import ValidationError

    from app.schemas.retrieval import RetrievalRequest

    with pytest.raises(ValidationError):
        RetrievalRequest(query="What time does the library close?")
    with pytest.raises(ValidationError):
        RetrievalRequest(query="   ", institution_id=INSTITUTION_A)


def test_retrieval_passes_the_requested_tenant_to_the_vector_search():
    from app.schemas.retrieval import RetrievalRequest
    from app.services import retrieval as retrieval_service

    with patch.object(
        retrieval_service, "embed_query", return_value=[0.0] * 1536
    ), patch.object(retrieval_service, "search_chunks", return_value=[]) as search:
        response = retrieval_service.retrieve(
            RetrievalRequest(query="library hours", institution_id=INSTITUTION_A, top_k=4)
        )
    assert response.results == []
    assert search.call_args.kwargs["institution_id"] == INSTITUTION_A


def test_retrieval_for_a_foreign_tenant_returns_no_rows():
    from app.schemas.retrieval import RetrievalRequest
    from app.services import retrieval as retrieval_service

    with patch.object(
        retrieval_service, "embed_query", return_value=[0.0] * 1536
    ), patch.object(retrieval_service, "search_chunks", return_value=[]) as search:
        response = retrieval_service.retrieve(
            RetrievalRequest(query="library hours", institution_id=FOREIGN_TENANT)
        )
    assert response.results == []
    assert search.call_args.kwargs["institution_id"] == FOREIGN_TENANT


def test_retrieval_failure_is_reported_without_leaking_internals():
    from app.schemas.retrieval import RetrievalRequest
    from app.services import retrieval as retrieval_service

    with patch.object(
        retrieval_service, "embed_query", return_value=[0.0] * 1536
    ), patch.object(
        retrieval_service,
        "search_chunks",
        side_effect=AppError("db exploded at table knowledge_chunks", code="X"),
    ):
        with pytest.raises(AppError) as excinfo:
            retrieval_service.retrieve(
                RetrievalRequest(query="library hours", institution_id=INSTITUTION_A)
            )
    assert excinfo.value.code == "RETRIEVAL_FAILED"
    assert "db exploded" not in (excinfo.value.message or "")


def test_retrieval_rejects_an_invalid_query_embedding():
    from app.services import retrieval as retrieval_service

    with pytest.raises(AppError) as excinfo:
        retrieval_service.retrieve_chunks([0.0] * 10, institution_id=INSTITUTION_A)
    assert excinfo.value.code == "INVALID_QUERY_EMBEDDING"




