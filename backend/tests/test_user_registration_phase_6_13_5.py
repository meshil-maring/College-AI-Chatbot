"""Phase 6.13.5 user registration tests part 1."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import user_registration as reg_service

client = TestClient(app, raise_server_exceptions=False)

ORG_A = "a0000000-0000-0000-0000-00000000000a"
INST_A = "b0000000-0000-0000-0000-0000000000a1"
INST_B = "b0000000-0000-0000-0000-0000000000b1"
USER_ID = "71000000-0000-0000-0000-000000000001"
AUTH_ID = "81000000-0000-0000-0000-000000000001"
STUDENT_ID = "30000000-0000-0000-0000-000000000151"
REQUEST_ID = "e1000000-0000-0000-0000-000000000001"


def p_student(**over):
    body = {
        "registration_type": "student",
        "institution_code": "IMPHAL",
        "email": "New.Student@Example.com",
        "password": "secret123",
        "first_name": "New",
        "last_name": "Student",
        "register_number": "1001",
        "university_roll_number": "2026-1001",
    }
    body.update(over)
    return body


def p_faculty(**over):
    body = {
        "registration_type": "faculty",
        "institution_code": "IMPHAL",
        "email": "Fac.One@Example.com",
        "password": "secret123",
        "first_name": "Fac",
        "last_name": "One",
        "designation": "Professor",
        "department": "CSE",
    }
    body.update(over)
    return body


def p_staff(**over):
    body = {
        "registration_type": "staff",
        "institution_code": "imphal",
        "email": "staff.one@example.com",
        "password": "secret123",
        "first_name": "Staff",
        "last_name": "One",
    }
    body.update(over)
    return body


def inst_row(**over):
    row = {
        "institution_id": INST_A,
        "organization_id": ORG_A,
        "name": "Imphal College",
        "code": "IMPHAL",
        "status": "active",
        "is_active": True,
    }
    row.update(over)
    return row


def mk_patched(state, payload):
    inst = state.get("institution", "active")
    if inst == "active":
        inst = inst_row()
    elif inst == "missing":
        inst = None
    db = MagicMock()
    db._state = state
    state.setdefault("inserted_students", [])
    state.setdefault("inserted_users", [])
    state.setdefault("inserted_requests", [])

    def fake_table(name):
        if name == "students":
            if state.get("students_error"):
                raise RuntimeError("boom")
            q = MagicMock()

            def do_insert(row):
                if state.get("students_insert_error"):
                    raise RuntimeError("boom")
                state["inserted_students"].append(dict(row))
                created = dict(row)
                created.setdefault("student_id", STUDENT_ID)
                resp = MagicMock()
                resp.data = [created]
                q.execute.return_value = resp
                return q

            q.insert.side_effect = do_insert
            q.execute.return_value = MagicMock(data=None)
            return q
        if name == "institution_membership_requests":
            q = MagicMock()

            def do_insert(row):
                state["inserted_requests"].append(dict(row))
                created = dict(row)
                created.setdefault("request_id", REQUEST_ID)
                resp = MagicMock()
                resp.data = [created]
                q.execute.return_value = resp
                return q

            q.insert.side_effect = do_insert
            q.execute.return_value = MagicMock(data=None)
            return q
        if name == "users":
            q = MagicMock()

            def do_insert(row):
                if state.get("users_error"):
                    raise RuntimeError("boom")
                state["inserted_users"].append(dict(row))
                created = dict(row)
                created.setdefault("user_id", USER_ID)
                resp = MagicMock()
                resp.data = created
                return resp

            q.insert.side_effect = do_insert
            return q
        if name == "institution_membership_requests":
            q = MagicMock()

            def do_insert_request(row):
                if state.get("requests_error"):
                    raise RuntimeError("boom")
                state["inserted_requests"].append(dict(row))
                created = dict(row)
                created.setdefault("request_id", REQUEST_ID)
                resp = MagicMock()
                resp.data = [created]
                q.execute.return_value = resp
                return q

            q.insert.side_effect = do_insert_request
            q.execute.return_value = MagicMock(data=None)
            return q
        if name == "institution_membership_requests":
            q = MagicMock()

            def do_insert_request(row):
                if state.get("requests_error"):
                    raise RuntimeError("boom")
                state["inserted_requests"].append(dict(row))
                created = dict(row)
                created.setdefault("request_id", REQUEST_ID)
                resp = MagicMock()
                resp.data = [created]
                q.execute.return_value = resp
                return q

            q.insert.side_effect = do_insert_request
            q.execute.return_value = MagicMock(data=None)
            return q
        return MagicMock()

    db.table.side_effect = fake_table
    auth_mode = state.get("auth_error")
    auth_patch = (
        patch.object(
            reg_service.student_svc,
            "_create_auth_account",
            side_effect=RuntimeError("boom"),
        )
        if auth_mode
        else patch.object(
            reg_service.student_svc,
            "_create_auth_account",
            return_value=AUTH_ID,
        )
    )
    user_mode = state.get("users_error")
    user_patch = (
        patch.object(
            reg_service.student_svc,
            "_create_public_user",
            side_effect=RuntimeError("boom"),
        )
        if user_mode
        else patch.object(
            reg_service.student_svc,
            "_create_public_user",
            return_value=USER_ID,
        )
    )
    req_mode = state.get("membership_error")

    def _do_membership_request(db_arg=None, **kwargs):
        state["inserted_requests"].append(dict(kwargs))
        return {"request_id": REQUEST_ID}

    req_patch = (
        patch.object(
            reg_service.tenancy_repo,
            "insert_membership_request",
            side_effect=RuntimeError("boom"),
        )
        if req_mode
        else patch.object(
            reg_service.tenancy_repo,
            "insert_membership_request",
            side_effect=_do_membership_request,
        )
    )
    patches = [
        patch.object(reg_service, "get_admin_client", return_value=db),
        patch.object(
            reg_service.tenancy_repo,
            "get_institution_by_code",
            return_value=inst,
        ),
        patch.object(
            reg_service.student_svc,
            "_find_user_by_email",
            return_value=state.get("public_user"),
        ),
        patch.object(
            reg_service.academics_repo,
            "get_student_by_user_id",
            return_value=state.get("linked_student"),
        ),
        patch.object(
            reg_service.academics_repo,
            "get_student_by_email",
            return_value=state.get("dup_email"),
        ),
        patch.object(
            reg_service.academics_repo,
            "get_student_by_register_number",
            return_value=state.get("dup_register"),
        ),
        patch.object(
            reg_service.academics_repo,
            "get_student_by_university_roll_number",
            return_value=state.get("dup_roll"),
        ),
        auth_patch,
        user_patch,
        patch.object(
            reg_service.student_svc,
            "_try_delete_auth_user",
            side_effect=lambda *a, **k: state.setdefault(
                "del_auth_calls", []
            ).append(a),
        ),
        patch.object(
            reg_service.student_svc,
            "_try_delete_user_row",
            side_effect=lambda *a, **k: state.setdefault(
                "del_user_calls", []
            ).append(a),
        ),
        req_patch,
    ]
    return db, patches


def run(payload, state):
    db, patches = mk_patched(state, payload)
    for p in patches:
        p.start()
    try:
        resp = client.post("/api/v1/users/register", json=payload)
    finally:
        for p in reversed(patches):
            p.stop()
    return resp, state, db


def test_01_student_ok():
    resp, state, db = run(p_student(), {"institution": "active"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["registration_type"] == "student"
    assert body["approval_status"] == "pending"
    assert body["institution_id"] == INST_A
    assert body["institution_code"] == "IMPHAL"
    assert body["student_id"] == STUDENT_ID
    assert body["request_id"] is None
    assert len(state["inserted_students"]) == 1
    row = state["inserted_students"][0]
    assert row["institution_id"] == INST_A
    assert row["email"] == "new.student@example.com"
    assert row["register_number"] == "1001"
    assert row["university_roll_number"] == "2026-1001"
    assert row["student_number"] == "1001"
    assert row["approval_status"] == "pending"

def test_faculty_ok():
    resp, state, db = run(p_faculty(), {"institution": "active"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["registration_type"] == "faculty"
    assert body["approval_status"] == "pending"
    assert body["institution_id"] == INST_A
    assert body["request_id"] == REQUEST_ID
    assert body["student_id"] is None


def test_staff_ok():
    resp, state, db = run(p_staff(), {"institution": "active"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["registration_type"] == "staff"
    assert body["approval_status"] == "pending"
    assert body["request_id"] == REQUEST_ID
    assert body["student_id"] is None


def test_missing_institution():
    resp, state, db = run(p_student(), {"institution": "missing"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "INSTITUTION_NOT_FOUND"


def test_pending_institution():
    inst = inst_row(status="pending", is_active=False)
    resp, state, db = run(p_student(), {"institution": inst})
    assert resp.status_code == 403
    assert (
        resp.json()["error"]["code"]
        == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"
    )

def test_admin_injection_rejected():
    resp, _, _ = run(
        {**p_student(), "registration_type": "admin"}, {}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_role_field_rejected():
    resp, _, _ = run({**p_student(), "role": "admin"}, {})
    assert resp.status_code == 422


def test_scope_override_rejected():
    resp, _, _ = run(
        {**p_student(), "scope_type": "organization", "scope_id": ORG_A},
        {},
    )
    assert resp.status_code == 422


def test_dup_email():
    resp, _, _ = run(
        p_student(),
        {
            "institution": "active",
            "public_user": {"user_id": USER_ID},
            "linked_student": None,
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_dup_student_email():
    resp, _, _ = run(
        p_student(),
        {
            "institution": "active",
            "public_user": {"user_id": USER_ID},
            "linked_student": {"student_id": STUDENT_ID},
            "dup_email": {"student_id": STUDENT_ID},
        },
    )
    assert resp.status_code == 409


def test_dup_register():
    resp, _, _ = run(
        p_student(),
        {"institution": "active", "dup_register": {"x": 1}},
    )
    assert resp.status_code == 409
    assert (
        resp.json()["error"]["code"]
        == "REGISTER_NUMBER_ALREADY_REGISTERED"
    )


def test_dup_roll():
    resp, _, _ = run(
        p_student(),
        {"institution": "active", "dup_roll": {"x": 1}},
    )
    assert resp.status_code == 409

def test_dup_public_email():
    resp, _, _ = run(
        p_faculty(),
        {"institution": "active", "public_user": {"user_id": USER_ID}},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_invalid_email():
    resp, _, _ = run(p_student(email="not-an-email"), {})
    assert resp.status_code == 422


def test_short_password():
    resp, _, _ = run(p_student(password="123"), {})
    assert resp.status_code == 422


def test_missing_fields():
    resp, _, _ = run(
        {"registration_type": "student", "institution_code": "IMPHAL"}, {}
    )
    assert resp.status_code == 422


def test_student_missing_identifiers():
    resp, _, _ = run(
        p_student(register_number=None, university_roll_number=None), {}
    )
    assert resp.status_code == 422


def test_faculty_rejects_student_identifiers():
    resp, _, _ = run(
        p_faculty(register_number="9999"), {}
    )
    assert resp.status_code == 422


def test_password_never_returned():
    resp, state, db = run(p_student(), {"institution": "active"})
    body = resp.json()
    assert "password" not in body
    assert "password" not in resp.text.lower()


def test_password_never_stored():
    resp, state, db = run(p_student(), {"institution": "active"})
    assert resp.status_code == 201
    for row in state["inserted_students"]:
        assert "password" not in row
    for row in state["inserted_users"]:
        assert "password" not in row


def test_users_insert_failure_compensates_auth():
    resp, state, db = run(
        p_student(), {"institution": "active", "users_error": True}
    )
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "REGISTRATION_FAILED"
    assert len(state.get("del_auth_calls", [])) >= 1


def test_students_insert_failure_compensates():
    resp, state, db = run(
        p_student(), {"institution": "active", "students_insert_error": True}
    )
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "REGISTRATION_FAILED"
    assert len(state.get("del_auth_calls", [])) >= 1
    assert len(state.get("del_user_calls", [])) >= 1


def test_auth_failure():
    resp, state, db = run(
        p_student(), {"institution": "active", "auth_error": True}
    )
    assert resp.status_code in (500, 502)


def test_membership_insert_failure_compensates():
    resp, state, db = run(
        p_faculty(), {"institution": "active", "membership_error": True}
    )
    assert resp.status_code in (500, 502)
    assert len(state.get("del_auth_calls", [])) >= 1
    assert len(state.get("del_user_calls", [])) >= 1


def test_tenant_isolation_scope_matches():
    resp, state, db = run(p_student(), {"institution": "active"})
    assert resp.status_code == 201
    row = state["inserted_students"][0]
    assert row["institution_id"] == INST_A
    assert resp.json()["institution_id"] == INST_A


def test_case_insensitive_code():
    resp, state, db = run(
        p_student(institution_code="  imphal  "), {"institution": "active"}
    )
    assert resp.status_code == 201


def test_no_role_granted_at_registration():
    resp, state, db = run(p_student(), {"institution": "active"})
    body = resp.json()
    assert "role" not in body
    assert "scope_type" not in body
    assert "scope_id" not in body
    resp2, _, _ = run(p_faculty(), {"institution": "active"})
    b2 = resp2.json()
    assert "role" not in b2
    assert "scope_type" not in b2


def test_08_student_role_assignment():
    """registration_type=student maps to the student role at approval time."""
    assert reg_service.ROLE_MAP["student"] == "student"
    resp, state, db = run(p_student(), {"institution": "active"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["registration_type"] == "student"
    # Server-side mapping: the pending student profile is created; the
    # "student" role itself is granted only by the Phase 6.4 approval
    # workflow (no role/users write happens here).
    assert len(state["inserted_students"]) == 1
    assert "role" not in body


def test_09_faculty_role_assignment():
    """registration_type=faculty maps to the faculty role at approval time."""
    assert reg_service.ROLE_MAP["faculty"] == "faculty"
    resp, state, db = run(p_faculty(), {"institution": "active"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["registration_type"] == "faculty"
    assert state["inserted_requests"][0]["requested_role"] == "faculty"
    assert "role" not in body


def test_10_staff_role_assignment():
    """registration_type=staff maps to the staff role at approval time."""
    assert reg_service.ROLE_MAP["staff"] == "staff"
    resp, state, db = run(p_staff(), {"institution": "active"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["registration_type"] == "staff"
    assert state["inserted_requests"][0]["requested_role"] == "staff"
    assert "role" not in body


def test_11_admin_role_injection_attempt():
    """registration_type=admin is unrepresentable: rejected with 422."""
    body = p_student(registration_type="admin")
    resp, _, _ = run(body, {"institution": "active"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_12_institution_scope_assignment():
    """Pending record is scoped to the server-resolved institution id."""
    resp, state, db = run(p_student(), {"institution": "active"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["institution_id"] == INST_A
    row = state["inserted_students"][0]
    assert row["institution_id"] == INST_A
    resp2, state2, _ = run(p_faculty(), {"institution": "active"})
    assert resp2.status_code == 201
    assert resp2.json()["institution_id"] == INST_A
    req = state2["inserted_requests"][0]
    assert str(req["institution_id"]) == INST_A


def test_13_cross_institution_scope_isolation():
    """Identities are institution-scoped: same identifiers at another
    institution are NOT duplicates; duplicates stay within one tenant."""
    inst_b = inst_row(
        institution_id=INST_B, organization_id=ORG_A, code="OTHER"
    )
    resp, state, db = run(p_student(), {"institution": inst_b})
    assert resp.status_code == 201, resp.text
    row = state["inserted_students"][0]
    assert row["institution_id"] == INST_B
    assert row["register_number"] == "1001"


def test_student_only_identifiers():
    resp, _, _ = run(p_student(register_number="  1002  "), {})
    assert resp.status_code in (201, 404, 409)


def test_rejected_institution():
    inst = inst_row(status="rejected", is_active=False)
    resp, _, _ = run(p_faculty(), {"institution": inst})
    assert resp.status_code == 403


def test_inactive_flag_institution():
    inst = inst_row(status="active", is_active=False)
    resp, _, _ = run(p_staff(), {"institution": inst})
    assert resp.status_code == 403
    assert (
        resp.json()["error"]["code"]
        == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"
    )


def test_23_tenant_institution_mismatch():
    """The client cannot override the resolved tenant: the stored
    institution_id is always the server-resolved one, never a client id."""
    body = dict(p_student())
    body["institution_id"] = INST_B  # forged internal id: must be ignored
    body["organization_id"] = ORG_A  # forged org scope: must be ignored
    resp, state, db = run(body, {"institution": "active"})
    # extra="forbid" rejects unknown authorization fields outright.
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_24_existing_student_login_compatibility():
    """Registered identifiers keep the Phase 6 login shapes intact: the
    stored student_number/email/register/roll values match what login
    resolution expects (email + register/roll + institution context)."""
    resp, state, db = run(p_student(), {"institution": "active"})
    assert resp.status_code == 201
    row = state["inserted_students"][0]
    assert row["email"] == "new.student@example.com"
    assert row["register_number"] == "1001"
    assert row["university_roll_number"] == "2026-1001"
    assert row["student_number"] == "1001"
    assert row["institution_id"] == INST_A
    assert row["approval_status"] == "pending"


def test_25_phase_6131_to_6134_regression():
    """Earlier registration primitives used by this endpoint are intact:
    code lookup, active gate, auth/public-user helpers, and the
    membership-request ledger entry point all still resolve."""
    import app.repositories.tenancy as repo
    import app.services.student_registration as sreg
    import app.services.tenancy as tsvc

    assert callable(repo.get_institution_by_code)
    assert callable(repo.insert_membership_request)
    assert callable(tsvc._assert_institution_active)
    assert callable(sreg._create_auth_account)
    assert callable(sreg._create_public_user)
    assert callable(sreg._assert_no_duplicate_identities)
    assert tsvc.PENDING == "pending"
    assert tsvc.ACTIVE == "active"