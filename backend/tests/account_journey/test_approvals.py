from .support import (
    AUTH_HEADERS,
    AppError,
    INSTITUTION_A,
    MagicMock,
    STUDENT_ID,
    USER_ID,
    _LOGIN_URL,
    _active_institution_authorization,
    _auth,
    _envelope,
    _registration_payload,
    client,
    patch,
    pytest,
)


def test_registration_returns_201_pending_and_issues_no_token():
    from app.services.auth.student_registration import RegistrationResponse

    created = RegistrationResponse(
        message="Registration submitted. Your account is pending approval.",
        student_id=STUDENT_ID,
        institution_id=INSTITUTION_A,
        email="phase622.student@demo.collegelocal.dev",
        approval_status="pending",
    )
    with patch("app.api.auth.registration.register_student", return_value=created):
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
        response = client.post(
            "/api/v1/registration", json=_registration_payload(**injected)
        )
        assert response.status_code == 422, injected
        _envelope(response)


def test_admin_approval_transitions_pending_to_approved():
    approved = {
        "student_id": STUDENT_ID,
        "approval_status": "approved",
        "institution_id": INSTITUTION_A,
    }
    # The audit write is a privileged mutation against the real admin_audit_log
    # table; stub it (Phase 6.19/6.20 pattern) so the approval contract itself
    # is what this test observes, not database reachability.
    with (
        _auth("admin"),
        patch(
            "app.services.admin.admin_academics.approve_student", return_value=approved
        ) as approve,
        patch(
            "app.api.admin.common.record_admin_action", return_value={"audit_id": "a-1"}
        ),
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_ID}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    # The approving tenant is resolved SERVER-SIDE from the principal, never
    # from the request body/query.
    tenant_argument = approve.call_args.args[1]
    assert str(tenant_argument) in (INSTITUTION_A, "None")


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
    with (
        _auth("staff", tenant=INSTITUTION_A),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as pending,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    # admin.list_pending_students passes the tenant POSITIONALLY:
    #   list_pending_approvals(effective, limit=limit, offset=offset)
    assert str(pending.call_args.args[0]) == INSTITUTION_A


def test_stale_approval_of_an_already_decided_student_conflicts():
    with (
        _auth("admin"),
        patch(
            "app.services.admin.admin_academics.approve_student",
            side_effect=AppError(
                "Student is not pending approval",
                status_code=409,
                code="STUDENT_NOT_PENDING",
            ),
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


def test_login_normalizes_unknown_identifier_and_pending_state_to_401():
    from app.services.auth.student_auth import SafeAuthFailure

    with patch(
        "app.api.auth.student_auth.authenticate_student", side_effect=SafeAuthFailure()
    ):
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
        payload = {
            "identifier": "student@college.edu",
            "password": "secret123",
            **injected,
        }
        response = client.post(_LOGIN_URL, json=payload)
        assert response.status_code == 422, injected
        _envelope(response)


def test_retrieval_rejects_an_invalid_query_embedding():
    from app.services.knowledge import retrieval as retrieval_service

    with pytest.raises(AppError) as excinfo:
        retrieval_service.retrieve_chunks([0.0] * 10, institution_id=INSTITUTION_A)
    assert excinfo.value.code == "INVALID_QUERY_EMBEDDING"
