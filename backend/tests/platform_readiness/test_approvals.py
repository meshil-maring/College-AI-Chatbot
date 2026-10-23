from .support import (
    AUTH_HEADERS,
    AppError,
    MagicMock,
    STUDENT_A,
    STUDENT_B,
    TENANT_A,
    TENANT_B,
    USER_ID,
    _active_institution_authorization,
    _assert_no_leak,
    _auth,
    _envelope,
    _user,
    _validate,
    assert_tenant_object,
    client,
    patch,
    pytest,
    scope_tenant,
)


def test_login_rejects_client_role_injection_with_422():
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "a@college.edu", "password": "secret12", "role": "admin"},
    )
    assert r.status_code == 422
    assert _envelope(r)["code"] == "VALIDATION_ERROR"


def test_scope_tenant_rejects_foreign_tenant():
    with pytest.raises(AppError) as exc:
        scope_tenant(_user("student", TENANT_A), TENANT_B)
    assert exc.value.status_code == 403
    assert exc.value.code == "TENANT_MISMATCH"


def test_assert_tenant_object_rejects_cross_tenant_row():
    with pytest.raises(AppError) as exc:
        assert_tenant_object(_user("admin", TENANT_A), TENANT_B)
    assert exc.value.status_code == 403


def test_chat_rejects_cross_tenant_institution():
    with _auth("student", TENANT_A):
        r = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "Hello?", "institution_id": TENANT_B},
        )
    assert r.status_code == 403
    assert _envelope(r)["code"] == "TENANT_MISMATCH"
    _assert_no_leak(r.text)


def test_admin_pending_queue_rejects_foreign_institution():
    with _auth("admin", TENANT_A):
        r = client.get(
            f"/api/v1/admin/students/pending?institution_id={TENANT_B}",
            headers=AUTH_HEADERS,
        )
    assert r.status_code == 403
    assert _envelope(r)["code"] == "TENANT_MISMATCH"


def test_faculty_cannot_reach_pending_queue():
    with _auth("faculty", TENANT_A):
        r = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert r.status_code == 403


def test_registration_rejects_privileged_role_field():
    # first/last name supplied so the ONLY validation failure is the
    # forbidden extra field (proves `extra="forbid"`, not a missing field).
    r = client.post(
        "/api/v1/registration",
        json={
            "institution_id": TENANT_A,
            "email": "n@college.edu",
            "password": "secret12",
            "first_name": "Nia",
            "last_name": "Rao",
            "register_number": "REG-900",
            "role": "admin",
        },
    )
    assert r.status_code == 422
    assert "role" in str(_envelope(r).get("details"))


def test_registration_rejects_approval_status_field():
    r = client.post(
        "/api/v1/registration",
        json={
            "institution_id": TENANT_A,
            "email": "n@college.edu",
            "password": "secret12",
            "first_name": "Nia",
            "last_name": "Rao",
            "register_number": "REG-901",
            "approval_status": "approved",
        },
    )
    assert r.status_code == 422
    assert "approval_status" in str(_envelope(r).get("details"))


def test_student_cannot_approve():
    with _auth("student", TENANT_A):
        r = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/approve", headers=AUTH_HEADERS
        )
    assert r.status_code == 403


def test_faculty_cannot_reject():
    with _auth("faculty", TENANT_A):
        r = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/reject", headers=AUTH_HEADERS
        )
    assert r.status_code == 403


def test_stale_approval_decision_is_409_without_write():
    # A rejected account cannot be approved by a stale pending-queue action.
    # Approved rows remain repairable through the atomic provisioning command.
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "student_id": STUDENT_A,
        "user_id": USER_ID,
        "institution_id": TENANT_A,
        "approval_status": "rejected",
    }
    with (
        _auth("admin", TENANT_A),
        patch("app.services.admin.admin_academics.get_admin_client", return_value=db),
    ):
        r = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/approve", headers=AUTH_HEADERS
        )
    assert r.status_code == 409
    assert _envelope(r)["code"] == "STUDENT_NOT_PENDING"
    db.table.return_value.update.assert_not_called()
    db.rpc.assert_not_called()


def test_cross_tenant_approval_is_403_before_state_read():
    # Tenant mismatch is enforced BEFORE the approval state is disclosed.
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "student_id": STUDENT_B,
        "user_id": USER_ID,
        "institution_id": TENANT_B,
        "approval_status": "pending",
    }
    with (
        _auth("admin", TENANT_A),
        patch("app.services.admin.admin_academics.get_admin_client", return_value=db),
    ):
        r = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/approve", headers=AUTH_HEADERS
        )
    assert r.status_code == 403
    assert _envelope(r)["code"] == "TENANT_MISMATCH"
    db.table.return_value.update.assert_not_called()


def test_upload_validation_rejects_empty():
    with pytest.raises(AppError) as exc:
        _validate("doc.pdf", "application/pdf", 0)
    assert exc.value.code == "EMPTY_FILE"


def test_upload_validation_rejects_executable():
    with pytest.raises(AppError) as exc:
        _validate("malware.exe", "application/octet-stream", 100)
    assert exc.value.code == "INVALID_FILE_TYPE"
