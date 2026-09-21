"""Registration must never crash the API — regression tests.

Bug fixed alongside this file: the student registration duplicate check calls
``app.repositories.admin_academics.get_student_by_email``, which read
``response.data`` directly. postgrest-py >= 2.x returns ``None`` from
``maybe_single().execute()`` when the query matches ZERO rows, so the ordinary
"this student does not exist yet" outcome raised::

    AttributeError: 'NoneType' object has no attribute 'data'

and the request died as an unhandled HTTP 500 (``Unhandled server error on
/api/v1/users/register``).

Covered here:

1. Repository contract — a missing row is ``None`` (not an error); a database
   failure is RAISED and is never silently converted into ``None``.
2. Registration end-to-end over the REAL repositories and the REAL duplicate
   checks (email / register number / university roll number, tenant-scoped).
3. Registration error handling — expected validation errors stay 4xx, an
   unexpected database/service failure becomes a controlled 5xx
   (``REGISTRATION_FAILED``) that is logged server-side without leaking any
   internal detail or credential to the client.
4. Server resilience — after a failed registration the process still serves
   ``/health`` and further requests.

Every test is hermetic: the fake PostgREST builder below reproduces the
postgrest-py >= 2.x chain semantics exactly, so no live database is touched.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import admin_academics as repo
from app.services import student_registration as student_svc
from app.services import user_registration as user_reg_service

# ``raise_server_exceptions=True`` (the TestClient default) is deliberate: if a
# registration failure ever escapes the app's controlled error handling the
# test fails loudly instead of silently accepting a 500.
client = TestClient(app)

ORG_A = "a0000000-0000-0000-0000-00000000000a"
INST_A = "b0000000-0000-0000-0000-0000000000a1"
INST_B = "b0000000-0000-0000-0000-0000000000b1"
USER_ID = "71000000-0000-0000-0000-000000000001"
AUTH_ID = "81000000-0000-0000-0000-000000000001"
STUDENT_ID = "30000000-0000-0000-0000-000000000151"
REQUEST_ID = "e1000000-0000-0000-0000-000000000001"

INSTITUTION_ROW = {
    "institution_id": INST_A,
    "organization_id": ORG_A,
    "name": "Imphal College",
    "code": "IMPHAL",
    "status": "active",
    "is_active": True,
}

STUDENT_ROW = {
    "student_id": STUDENT_ID,
    "user_id": USER_ID,
    "institution_id": INST_A,
    "student_number": "1001",
    "email": "brand.new@example.com",
    "register_number": "1001",
    "university_roll_number": "2026-1001",
    "approval_status": "pending",
    "status": "active",
    "is_active": True,
}


# ============================================================================
# Fake PostgREST surface (postgrest-py >= 2.x semantics)
# ============================================================================


class _DbFailure(RuntimeError):
    """Stand-in for a PostgREST / gateway / driver failure raised by the client."""


class _Response:
    """Minimal ``APIResponse`` substitute (only ``.data`` is ever read)."""

    def __init__(self, data) -> None:
        self.data = data


class _Table:
    """Fake PostgREST builder reproducing postgrest-py >= 2.x behaviour.

    * ``maybe_single().execute()`` returns ``None`` for ZERO matching rows — it
      does NOT return an ``APIResponse`` whose ``data`` is ``None``. This is
      exactly the production behaviour that triggered the AttributeError.
    * ``execute()`` without ``maybe_single()`` returns a list-bearing response.
    * ``insert(...).execute()`` returns the created row(s).
    * A configured failure raises; it is never turned into empty data.
    """

    def __init__(self, name, rows=None, defaults=None, fail=False, recorder=None):
        self.name = name
        self._rows = list(rows or [])
        self._defaults = dict(defaults or {})
        self._fail = fail
        self._recorder = recorder
        self._filters: dict[str, object] = {}
        self._single = False
        self._created: list[dict] | None = None
        self._updated: dict | None = None

    # -- chainable query surface --------------------------------------------
    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def maybe_single(self):
        self._single = True
        return self

    def insert(self, row):
        self._created = [{**self._defaults, **dict(row)}]
        if self._recorder is not None:
            self._recorder.append(self._created[0])
        return self

    def update(self, values):
        self._updated = dict(values)
        return self

    def delete(self, *args, **kwargs):
        return self

    # -- execution -----------------------------------------------------------
    def execute(self):
        if self._fail:
            raise _DbFailure(f"database failure on table {self.name!r}")
        if self._created is not None:
            return _Response(self._created)
        matched = [
            row
            for row in self._rows
            if all(
                str(row.get(key)) == str(value)
                for key, value in self._filters.items()
            )
        ]
        if self._single:
            return _Response(matched[0]) if matched else None
        return _Response(matched)


class _FakeDb:
    """Fake service-role Supabase client backed by in-memory tables."""

    def __init__(
        self,
        *,
        institutions=(),
        students=(),
        users=(),
        fail_tables=(),
    ) -> None:
        self._rows = {
            "institutions": list(institutions),
            "students": list(students),
            "users": list(users),
        }
        self.fail_tables = set(fail_tables)
        self.inserted: dict[str, list[dict]] = {}

    def table(self, name):
        defaults = {
            "students": {"student_id": STUDENT_ID},
            "users": {"user_id": USER_ID},
            "institution_membership_requests": {"request_id": REQUEST_ID},
        }.get(name, {})
        return _Table(
            name,
            rows=self._rows.get(name),
            defaults=defaults,
            fail=name in self.fail_tables,
            recorder=self.inserted.setdefault(name, []),
        )


class _FakeAuthUser:
    def __init__(self, auth_id: str) -> None:
        self.id = auth_id
        self.email = None


class _FakeSignUpResult:
    def __init__(self, auth_id: str) -> None:
        self.user = _FakeAuthUser(auth_id)


class _FakeAuth:
    def __init__(self, auth_id: str) -> None:
        self._auth_id = auth_id
        self.admin = self

    def sign_up(self, credentials):
        return _FakeSignUpResult(self._auth_id)

    def delete_user(self, auth_user_id):
        return None


class _FakeAuthClient:
    """Fake GoTrue client (``create_supabase_client``) — no network I/O."""

    def __init__(self, auth_id: str = AUTH_ID) -> None:
        self.auth = _FakeAuth(auth_id)


# ============================================================================
# Registration harness
# ============================================================================


def payload(**over):
    """Valid student registration payload (extra fields overridable)."""
    body = {
        "registration_type": "student",
        "institution_code": "IMPHAL",
        "email": "brand.new@example.com",
        "password": "secret123",
        "first_name": "Brand",
        "last_name": "New",
        "register_number": "1001",
        "university_roll_number": "2026-1001",
    }
    body.update(over)
    return body


@contextmanager
def _patched(db, *, admin_client=None, auth_id=AUTH_ID):
    """Patch the registration plumbing onto the in-memory fake database.

    The REAL repositories, the REAL duplicate checks and the REAL
    ``public.users`` / ``students`` insert code paths stay in place; only the
    Supabase clients (DB + GoTrue) and the best-effort compensation helpers are
    replaced. ``admin_client`` overrides ``get_admin_client`` (e.g. to make the
    client construction itself fail).
    """
    calls = {"deleted_auth": [], "deleted_user": []}
    admin = (
        patch.object(user_reg_service, "get_admin_client", side_effect=admin_client)
        if admin_client is not None
        else patch.object(user_reg_service, "get_admin_client", return_value=db)
    )
    with (
        admin,
        patch.object(student_svc, "get_admin_client", return_value=db),
        patch.object(
            student_svc,
            "create_supabase_client",
            return_value=_FakeAuthClient(auth_id),
        ),
        patch.object(
            student_svc,
            "_try_delete_auth_user",
            side_effect=lambda auth_user_id, **kw: calls["deleted_auth"].append(
                auth_user_id
            ),
        ),
        patch.object(
            student_svc,
            "_try_delete_user_row",
            side_effect=lambda db_arg, user_id, **kw: calls["deleted_user"].append(
                user_id
            ),
        ),
    ):
        yield calls


def post_registration(body, db, **kwargs):
    """POST the unified registration endpoint with the fake database in place."""
    with _patched(db, **kwargs) as calls:
        response = client.post("/api/v1/users/register", json=body)
    return response, calls



# ============================================================================
# 1. Repository contract — missing row is None, failure is RAISED
# ============================================================================


def test_fake_postgrest_returns_none_for_zero_rows():
    """The reproduction mechanism itself matches postgrest-py >= 2.x."""
    raw = (
        _FakeDb(students=[])
        .table("students")
        .select(repo.STUDENT_IDENTITY_COLUMNS)
        .eq("email", "nobody@collegea.test")
        .maybe_single()
        .execute()
    )
    assert raw is None


def test_get_student_by_email_returns_existing_student():
    db = _FakeDb(students=[STUDENT_ROW])
    student = repo.get_student_by_email(db, INST_A, "BRAND.NEW@example.com")
    assert student == STUDENT_ROW


def test_get_student_by_email_returns_none_when_missing():
    """A brand-new email must resolve to None — never AttributeError."""
    db = _FakeDb(students=[])
    assert repo.get_student_by_email(db, INST_A, "nobody@collegea.test") is None


def test_get_student_by_register_number_returns_none_when_missing():
    db = _FakeDb(students=[])
    assert repo.get_student_by_register_number(db, INST_A, "9999") is None


def test_get_student_by_university_roll_number_returns_none_when_missing():
    db = _FakeDb(students=[])
    assert repo.get_student_by_university_roll_number(db, INST_A, "2026-9999") is None


def test_get_student_by_user_id_returns_none_when_missing():
    db = _FakeDb(students=[])
    assert repo.get_student_by_user_id(db, USER_ID) is None


def test_get_student_returns_none_when_missing():
    db = _FakeDb(students=[])
    assert repo.get_student(db, STUDENT_ID) is None


def test_get_student_for_approval_returns_none_when_missing():
    db = _FakeDb(students=[])
    assert repo.get_student_for_approval(db, STUDENT_ID) is None


def test_set_student_approval_status_returns_none_when_no_row_matched():
    """No pending row matched (already processed / cross-tenant) -> None."""
    db = _FakeDb(students=[])
    assert (
        repo.set_student_approval_status(db, STUDENT_ID, INST_A, "approved") is None
    )


def test_identity_lookups_are_institution_scoped():
    """A student at ANOTHER institution is not a match for this tenant."""
    other_tenant_row = {**STUDENT_ROW, "institution_id": INST_B}
    db = _FakeDb(students=[other_tenant_row])
    assert repo.get_student_by_email(db, INST_A, "brand.new@example.com") is None
    assert repo.get_student_by_register_number(db, INST_A, "1001") is None
    assert (
        repo.get_student_by_university_roll_number(db, INST_A, "2026-1001") is None
    )


def test_resolve_student_by_identifier_returns_none_when_no_match():
    db = _FakeDb(students=[])
    assert repo.resolve_student_by_identifier(db, INST_A, "nobody@collegea.test") is None


def test_resolve_student_by_identifier_finds_by_register_number():
    db = _FakeDb(students=[STUDENT_ROW])
    student = repo.resolve_student_by_identifier(db, INST_A, "1001")
    assert student is not None and student["student_id"] == STUDENT_ID


@pytest.mark.parametrize(
    "lookup",
    [
        lambda db: repo.get_student_by_email(db, INST_A, "brand.new@example.com"),
        lambda db: repo.get_student_by_email_global(db, "brand.new@example.com"),
        lambda db: repo.get_student_by_register_number(db, INST_A, "1001"),
        lambda db: repo.get_student_by_university_roll_number(db, INST_A, "2026-1001"),
        lambda db: repo.get_student_by_user_id(db, USER_ID),
        lambda db: repo.get_student(db, STUDENT_ID),
        lambda db: repo.get_student_for_approval(db, STUDENT_ID),
        lambda db: repo.resolve_student_by_identifier(db, INST_A, "1001"),
    ],
    ids=[
        "by_email",
        "by_email_global",
        "by_register_number",
        "by_university_roll_number",
        "by_user_id",
        "by_student_id",
        "for_approval",
        "resolve_identifier",
    ],
)
def test_database_failure_is_raised_never_returns_none(lookup):
    """A failing database operation must NOT be reported as 'not found'."""
    db = _FakeDb(students=[STUDENT_ROW], fail_tables=("students",))
    with pytest.raises(_DbFailure):
        lookup(db)



# ============================================================================
# 2. Registration end-to-end over the REAL repositories (root-cause regression)
# ============================================================================


def _active_institution_db(**over):
    return _FakeDb(institutions=[INSTITUTION_ROW], **over)


def test_new_student_registration_succeeds_with_real_repositories():
    """The original crash: a brand-new student (zero matching rows)."""
    db = _active_institution_db(students=[], users=[])
    response, calls = post_registration(payload(), db)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["registration_type"] == "student"
    assert body["approval_status"] == "pending"
    assert body["student_id"] == STUDENT_ID
    assert body["institution_id"] == INST_A
    assert calls["deleted_auth"] == [] and calls["deleted_user"] == []
    created = db.inserted["students"][0]
    assert created["institution_id"] == INST_A
    assert created["email"] == "brand.new@example.com"
    assert created["register_number"] == "1001"
    assert created["university_roll_number"] == "2026-1001"
    assert created["student_number"] == "1001"
    assert created["approval_status"] == "pending"


def test_existing_student_email_with_real_repository_is_a_conflict():
    db = _active_institution_db(students=[STUDENT_ROW], users=[{"user_id": USER_ID, "email": "brand.new@example.com"}])
    response, _ = post_registration(payload(), db)
    # The public.users email check fires first; either way this is a controlled
    # duplicate response, never a 500.
    assert response.status_code == 409
    assert response.json()["error"]["code"] in (
        "EMAIL_ALREADY_REGISTERED",
        "STUDENT_ALREADY_REGISTERED",
    )
    assert db.inserted["students"] == []


def test_duplicate_student_email_with_real_repository_is_a_conflict():
    db = _active_institution_db(students=[{**STUDENT_ROW, "user_id": "other"}], users=[])
    response, _ = post_registration(payload(), db)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert db.inserted["students"] == []


def test_duplicate_register_number_with_real_repository_is_a_conflict():
    existing = {
        **STUDENT_ROW,
        "email": "someone.else@example.com",
        "university_roll_number": "2026-2222",
    }
    db = _active_institution_db(students=[existing], users=[])
    response, _ = post_registration(payload(), db)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REGISTER_NUMBER_ALREADY_REGISTERED"
    assert db.inserted["students"] == []


def test_duplicate_university_roll_number_with_real_repository_is_a_conflict():
    existing = {
        **STUDENT_ROW,
        "email": "someone.else@example.com",
        "register_number": "9999",
    }
    db = _active_institution_db(students=[existing], users=[])
    response, _ = post_registration(payload(), db)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ROLL_NUMBER_ALREADY_REGISTERED"
    assert db.inserted["students"] == []


def test_duplicate_identities_at_another_institution_are_not_a_conflict():
    """Tenant scoping is preserved: another tenant's identifiers never block."""
    other_tenant = {**STUDENT_ROW, "institution_id": INST_B}
    db = _active_institution_db(students=[other_tenant], users=[])
    response, _ = post_registration(payload(), db)
    assert response.status_code == 201, response.text
    assert db.inserted["students"][0]["institution_id"] == INST_A


def test_duplicate_checks_are_still_invoked():
    """``_assert_no_duplicate_identities`` must stay on the registration path."""
    db = _active_institution_db(students=[], users=[])
    original = student_svc._assert_no_duplicate_identities
    seen = []

    def spy(*args, **kwargs):
        seen.append(args)
        return original(*args, **kwargs)

    with _patched(db):
        with patch.object(
            student_svc, "_assert_no_duplicate_identities", side_effect=spy
        ):
            response = client.post("/api/v1/users/register", json=payload())
    assert response.status_code == 201, response.text
    assert len(seen) == 1
    # (db, institution_id, email, register_number, university_roll_number)
    assert str(seen[0][1]) == INST_A
    assert seen[0][3] == "1001" and seen[0][4] == "2026-1001"



# ============================================================================
# 3. Error handling — 4xx for validation, controlled 5xx for DB/service failure
# ============================================================================

_USER_REG_LOGGER = "app.services.user_registration"


def test_database_failure_returns_controlled_5xx(caplog):
    """Unexpected DB failure -> controlled 5xx, never an unhandled traceback."""
    db = _active_institution_db(fail_tables=("students",))
    with caplog.at_level(logging.ERROR, logger=_USER_REG_LOGGER):
        response, _ = post_registration(payload(), db)

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "REGISTRATION_FAILED"
    # The fail-closed global handler would report INTERNAL_ERROR: reaching it
    # means the failure escaped the registration layer.
    assert error["code"] != "INTERNAL_ERROR"
    assert "unable to complete registration" in error["message"].lower()

    # No internal detail and no credential may reach the client.
    text = response.text.lower()
    for leaked in (
        "traceback",
        "attributerror",
        "nonetype",
        "'none'",
        "postgrest",
        "supabase",
        "secret123",
        "students",
    ):
        assert leaked not in text, f"leaked {leaked!r} in response"

    # ... while the real exception IS logged server-side for debugging.
    assert caplog.text
    assert "_DbFailure" in caplog.text
    assert "registration_type=student" in caplog.text
    # Logs must never contain credentials or the student's email.
    assert "secret123" not in caplog.text
    assert "brand.new@example.com" not in caplog.text


def test_database_client_construction_failure_returns_controlled_5xx(caplog):
    with caplog.at_level(logging.ERROR, logger=_USER_REG_LOGGER):
        response, calls = post_registration(
            payload(),
            _FakeDb(),
            admin_client=RuntimeError("supabase unavailable"),
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "REGISTRATION_FAILED"
    assert "supabase unavailable" not in response.text
    assert calls["deleted_auth"] == [] and calls["deleted_user"] == []


def test_failure_response_never_contains_the_submitted_password(caplog):
    db = _active_institution_db(fail_tables=("students",))
    with caplog.at_level(logging.ERROR, logger=_USER_REG_LOGGER):
        response, _ = post_registration(payload(password="sup3r-s3cret-pw"), db)
    assert response.status_code == 500
    assert "sup3r-s3cret-pw" not in response.text
    assert "sup3r-s3cret-pw" not in caplog.text


def test_unknown_institution_is_still_a_404():
    response, _ = post_registration(payload(), _FakeDb(institutions=[]))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INSTITUTION_NOT_FOUND"


def test_inactive_institution_is_still_a_403():
    inactive = {**INSTITUTION_ROW, "status": "pending", "is_active": False}
    response, _ = post_registration(payload(), _FakeDb(institutions=[inactive]))
    assert response.status_code == 403
    assert (
        response.json()["error"]["code"] == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"
    )


def test_missing_student_identifiers_is_still_a_422():
    response, _ = post_registration(
        payload(register_number=None, university_roll_number=None),
        _active_institution_db(),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] in (
        "IDENTIFIER_REQUIRED",
        "VALIDATION_ERROR",
    )


def test_invalid_payload_is_still_a_422():
    response, _ = post_registration(
        payload(email="not-an-email"), _active_institution_db()
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_authorization_fields_are_still_rejected():
    response, _ = post_registration(
        payload(role="admin", scope_type="organization", scope_id=ORG_A),
        _active_institution_db(),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"



# ============================================================================
# 4. Server resilience — the process keeps serving after a failed registration
# ============================================================================


def test_server_stays_alive_after_registration_failure():
    """Fail one registration, then confirm the app still accepts requests."""
    failing_db = _active_institution_db(fail_tables=("students",))

    # 1. Registration that triggers the failure.
    first, _ = post_registration(payload(), failing_db)
    assert first.status_code == 500
    assert first.json()["error"]["code"] == "REGISTRATION_FAILED"

    # 2. Health endpoint still works.
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    # 3. Another working endpoint still works.
    assert client.get("/").status_code == 200

    # 4. Another registration request is still processed.
    second, _ = post_registration(payload(), failing_db)
    assert second.status_code == 500
    assert second.json()["error"]["code"] == "REGISTRATION_FAILED"

    # 5. A healthy registration succeeds afterwards.
    third, _ = post_registration(payload(), _active_institution_db(users=[]))
    assert third.status_code == 201, third.text

    # 6. Still alive.
    assert client.get("/health").status_code == 200


def test_server_stays_alive_after_duplicate_conflict():
    duplicate_db = _active_institution_db(
        students=[{**STUDENT_ROW, "email": "other@example.com"}], users=[]
    )
    conflict, _ = post_registration(payload(), duplicate_db)
    assert conflict.status_code == 409

    assert client.get("/health").status_code == 200

    ok, _ = post_registration(payload(), _active_institution_db(users=[]))
    assert ok.status_code == 201, ok.text
    assert client.get("/health").status_code == 200


def test_health_endpoint_is_public_and_unchanged():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

