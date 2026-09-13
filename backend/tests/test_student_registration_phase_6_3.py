"""Phase 6.3 - Student registration tests (mocked Supabase client)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app
from app.services import student_registration as reg

client = TestClient(app, raise_server_exceptions=False)

INST_A = "a1111111-0000-0000-0000-000000000001"
INST_B = "b2222222-0000-0000-0000-000000000002"
USER_ID = "71000000-0000-0000-0000-000000000001"
AUTH_ID = "81000000-0000-0000-0000-000000000001"
STUDENT_ID = "30000000-0000-0000-0000-000000000151"


def _payload(**over):
    body = {
        "institution_id": INST_A,
        "email": "New.Student@collegea.example.com",
        "password": "secret123",
        "first_name": "New",
        "last_name": "Student",
        "register_number": "1001",
        "university_roll_number": "2026-1001",
    }
    body.update(over)
    return body

def _user_row(**over):
    row = {
        "user_id": USER_ID,
        "auth_user_id": AUTH_ID,
        "email": "new.student@collegea.example.com",
        "first_name": "New",
        "last_name": "Student",
    }
    row.update(over)
    return row


def _student_row(**over):
    row = {
        "student_id": STUDENT_ID,
        "user_id": USER_ID,
        "institution_id": INST_A,
        "student_number": "1001",
        "email": "new.student@collegea.example.com",
        "register_number": "1001",
        "university_roll_number": "2026-1001",
        "approval_status": "pending",
    }
    row.update(over)
    return row


class _Q:
    """Minimal chainable query builder returning canned rows."""

    def __init__(self, single=None, rows=None):
        self._single = single
        self._rows = rows if rows is not None else []

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def insert(self, *a, **k):
        state = getattr(self, "_state", None)
        row = a[0] if a else {}
        if state is not None:
            state.setdefault("inserted", []).append(dict(row))
        created = dict(row)
        if "student_id" not in created and "user_id" in created:
            created.setdefault("student_id", STUDENT_ID)
            created.setdefault("approval_status", "pending")
        self._single = [created] if "student_id" in created else created
        return self

    def delete(self, *a, **k):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return MagicMock(data=self._single)


def _attach(db, state):
    db._state = state
    return db


def _db(state):
    """Fake service-role client answering per-table reads/writes from state."""
    db = MagicMock()

    def table(name):
        if name == "institutions":
            inst = state.get("institution")
            if inst == "error":
                raise RuntimeError("boom")
            q = _Q(single=inst)
            q._state = state
            return q
        if name == "users":
            q = _Q(single=state.get("public_user"))
            q._state = state

            def insert(row, _q=q):
                if state.get("users_error"):
                    raise RuntimeError("boom")
                state.setdefault("inserted_users", []).append(dict(row))
                created = dict(row)
                created.setdefault("user_id", USER_ID)
                _q._single = [created]
                return _q

            q.insert = insert
            return q
        if name == "students":
            stub = state.get("students_stub")
            if stub == "error":
                raise RuntimeError("boom")

            class _Students(_Q):
                def insert(self, row):
                    state.setdefault("inserted", []).append(dict(row))
                    created = dict(row)
                    created.setdefault("student_id", STUDENT_ID)
                    created.setdefault("approval_status", "pending")
                    # PostgREST insert returns a list of created rows.
                    self._single = [created]
                    return self

                def execute(self):
                    if isinstance(self._single, list):
                        return MagicMock(data=self._single)
                    data = state.get("student_rows")
                    if data is None:
                        data = []
                    return MagicMock(data=data)

            q = _Students(single=stub, rows=state.get("student_rows"))
            q._state = state
            return q
        return _Q(single=None)

    db.table.side_effect = table
    return _attach(db, state)


def _auth_ok(auth_id=AUTH_ID):
    created = MagicMock()
    created.user = MagicMock(
        id=auth_id, email="new.student@collegea.example.com"
    )
    anon = MagicMock()
    anon.auth.sign_up.return_value = created
    return anon


def _run(payload, state, auth_client=None):
    with (
        patch.object(reg, "get_admin_client", return_value=_db(state)),
        patch.object(
            reg, "create_supabase_client",
            return_value=auth_client or _auth_ok(),
        ),
        patch.object(
            reg.academics_repo, "get_student_by_user_id",
            return_value=state.get("linked_student"),
        ),
        patch.object(
            reg.academics_repo, "get_student_by_email",
            return_value=state.get("dup_email"),
        ),
        patch.object(
            reg.academics_repo, "get_student_by_register_number",
            return_value=state.get("dup_register"),
        ),
        patch.object(
            reg.academics_repo, "get_student_by_university_roll_number",
            return_value=state.get("dup_roll"),
        ),
    ):
        return client.post("/api/v1/registration", json=payload)



# ============================================================================
# Success + pending + institution + identity storage
# ============================================================================


def test_successful_registration_returns_201_pending():
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["approval_status"] == "pending"
    assert body["institution_id"] == INST_A
    assert body["email"] == "new.student@collegea.example.com"
    assert body["student_id"] == STUDENT_ID
    assert "pending" in body["message"].lower()
    assert "password" not in body
    assert "access_token" not in body
    assert "token" not in body


def test_identity_fields_stored_normalized_with_pending():
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    resp = _run(_payload(), state)
    assert resp.status_code == 201, resp.text
    assert len(state["inserted"]) == 1
    row = state["inserted"][0]
    assert row["institution_id"] == INST_A
    assert row["email"] == "new.student@collegea.example.com"
    assert row["register_number"] == "1001"
    assert row["university_roll_number"] == "2026-1001"
    assert row["student_number"] == "1001"
    assert row["approval_status"] == "pending"
    assert "password" not in row
    assert len(state["inserted_users"]) == 1
    assert "password" not in state["inserted_users"][0]


def test_roll_number_only_becomes_student_number():
    """University roll number alone is a genuine academic number."""
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    resp = _run(_payload(register_number=None), state)
    assert resp.status_code == 201, resp.text
    assert resp.json()["approval_status"] == "pending"
    row = state["inserted"][0]
    assert row["register_number"] is None
    assert row["university_roll_number"] == "2026-1001"
    assert row["student_number"] == "2026-1001"


def test_missing_both_identifiers_rejected_no_synthetic_number():
    """No academic identity -> 422, nothing created, nothing fabricated."""
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    created_auth = []
    anon = _auth_ok()
    orig_sign_up = anon.auth.sign_up

    def _spy(payload):
        created_auth.append(payload)
        return orig_sign_up(payload)

    anon.auth.sign_up = _spy
    resp = _run(
        _payload(register_number=None, university_roll_number=None),
        state,
        auth_client=anon,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "IDENTIFIER_REQUIRED"
    assert created_auth == []
    assert state.get("inserted") in (None, [])
    assert state.get("inserted_users") in (None, [])


def test_blank_identifiers_treated_as_missing():
    """Whitespace-only numbers normalize to None -> same 422 path."""
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    resp = _run(
        _payload(register_number="   ", university_roll_number="  "),
        state,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "IDENTIFIER_REQUIRED"


# ============================================================================
# Institution validation + duplicates
# ============================================================================


def test_invalid_institution_rejected():
    state = {"institution": None, "public_user": None}
    resp = _run(_payload(), state)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "INSTITUTION_NOT_FOUND"


def test_inactive_institution_rejected():
    state = {
        "institution": {"institution_id": INST_A, "is_active": False},
        "public_user": None,
    }
    resp = _run(_payload(), state)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == (
        "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"
    )


def _dup_state(**over):
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    state.update(over)
    return state


def test_duplicate_email_same_institution_rejected():
    state = _dup_state(dup_email=_student_row())
    resp = _run(_payload(), state)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_duplicate_register_number_same_institution_rejected():
    state = _dup_state(dup_register=_student_row())
    resp = _run(_payload(), state)
    assert resp.status_code == 409
    got = resp.json()["error"]["code"]
    assert got == "REGISTER_NUMBER_ALREADY_REGISTERED"


def test_duplicate_roll_number_same_institution_rejected():
    state = _dup_state(dup_roll=_student_row())
    resp = _run(_payload(), state)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ROLL_NUMBER_ALREADY_REGISTERED"


# Existing accounts + scoping + security


def test_existing_public_user_without_profile_rejected():
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": _user_row(),
        "linked_student": None,
    }
    resp = _run(_payload(), state)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert state.get("inserted") in (None, [])


def test_existing_student_profile_rejected():
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": _user_row(),
        "linked_student": _student_row(),
    }
    resp = _run(_payload(), state)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "STUDENT_ALREADY_REGISTERED"


def test_existing_supabase_auth_conflict_maps_to_409():
    from supabase_auth.errors import AuthApiError

    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    failing = MagicMock()
    failing.auth.sign_up.side_effect = AuthApiError(
        "User already registered", 422, "email_exists"
    )
    resp = _run(_payload(), state, auth_client=failing)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_duplicate_lookups_scoped_to_requested_institution():
    state = _dup_state()
    with (
        patch.object(reg, "get_admin_client", return_value=_db(state)),
        patch.object(reg, "create_supabase_client", return_value=_auth_ok()),
        patch.object(
            reg.academics_repo, "get_student_by_user_id", return_value=None
        ),
        patch.object(
            reg.academics_repo, "get_student_by_email", return_value=None
        ) as m_email,
        patch.object(
            reg.academics_repo,
            "get_student_by_register_number",
            return_value=None,
        ) as m_register,
        patch.object(
            reg.academics_repo,
            "get_student_by_university_roll_number",
            return_value=None,
        ) as m_roll,
    ):
        resp = client.post("/api/v1/registration", json=_payload())
    assert resp.status_code == 201, resp.text
    for mock in (m_email, m_register, m_roll):
        assert str(mock.call_args.args[1]) == INST_A
        assert INST_B not in str(mock.call_args)


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "admin"},
        {"roles": ["admin"]},
        {"role": "staff"},
        {"approval_status": "approved"},
        {"approval_status": "rejected"},
        {"is_admin": True},
        {"institution_name": "Evil College"},
    ],
)
def test_privilege_escalation_fields_rejected_with_422(extra):
    resp = client.post("/api/v1/registration", json={**_payload(), **extra})
    assert resp.status_code == 422, resp.text


def test_password_length_validated():
    resp = client.post("/api/v1/registration", json=_payload(password="short"))
    assert resp.status_code == 422, resp.text


def test_password_never_echoed_or_stored():
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    resp = _run(_payload(password="secret123"), state)
    assert resp.status_code == 201, resp.text
    assert "secret123" not in resp.text
    assert state["inserted"][0].get("password") is None


def test_public_users_insert_failure_compensates_auth_account():
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
        "users_error": True,
    }
    deleted = []
    with (
        patch.object(reg, "get_admin_client", return_value=_db(state)),
        patch.object(reg, "create_supabase_client", return_value=_auth_ok()),
        patch.object(
            reg.academics_repo, "get_student_by_user_id", return_value=None
        ),
        patch.object(
            reg.academics_repo, "get_student_by_email", return_value=None
        ),
        patch.object(
            reg.academics_repo,
            "get_student_by_register_number",
            return_value=None,
        ),
        patch.object(
            reg.academics_repo,
            "get_student_by_university_roll_number",
            return_value=None,
        ),
        patch.object(
            reg, "_try_delete_auth_user",
            side_effect=lambda *a: deleted.append(a),
        ),
    ):
        failed = client.post("/api/v1/registration", json=_payload())
    assert failed.status_code in (500, 502)
    assert deleted, "auth account must be compensated on users failure"


def test_students_insert_failure_compensates_user_and_auth():
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    db = _db(state)
    orig_table = db.table

    def table(name):
        q = orig_table(name)
        if name == "students":

            def insert(row):
                raise RuntimeError("students insert boom")

            q.insert = insert
        return q

    db.table = table
    removed_users = []
    removed_auth = []
    with (
        patch.object(reg, "get_admin_client", return_value=db),
        patch.object(reg, "create_supabase_client", return_value=_auth_ok()),
        patch.object(
            reg.academics_repo, "get_student_by_user_id", return_value=None
        ),
        patch.object(
            reg.academics_repo, "get_student_by_email", return_value=None
        ),
        patch.object(
            reg.academics_repo,
            "get_student_by_register_number",
            return_value=None,
        ),
        patch.object(
            reg.academics_repo,
            "get_student_by_university_roll_number",
            return_value=None,
        ),
        patch.object(
            reg, "_try_delete_user_row",
            side_effect=lambda *a: removed_users.append(a),
        ),
        patch.object(
            reg, "_try_delete_auth_user",
            side_effect=lambda *a: removed_auth.append(a),
        ),
    ):
        resp = client.post("/api/v1/registration", json=_payload())
    assert resp.status_code in (500, 502), resp.text
    assert removed_users, "public.users row must be compensated"
    assert removed_auth, "auth account must be compensated"


def test_registration_for_a_never_touches_b():
    state = {
        "institution": {"institution_id": INST_A, "is_active": True},
        "public_user": None,
    }
    db = _db(state)
    with (
        patch.object(reg, "get_admin_client", return_value=db),
        patch.object(reg, "create_supabase_client", return_value=_auth_ok()),
        patch.object(
            reg.academics_repo, "get_student_by_user_id", return_value=None
        ),
        patch.object(
            reg.academics_repo, "get_student_by_email", return_value=None
        ) as m_email,
        patch.object(
            reg.academics_repo,
            "get_student_by_register_number",
            return_value=None,
        ),
        patch.object(
            reg.academics_repo,
            "get_student_by_university_roll_number",
            return_value=None,
        ),
    ):
        resp = client.post("/api/v1/registration", json=_payload())
    assert resp.status_code == 201, resp.text
    assert resp.json()["institution_id"] == INST_A
    assert state["inserted"][0]["institution_id"] == INST_A
    assert str(m_email.call_args.args[1]) == INST_A
