"""Phase 9 â€” invitation-only Super Admin registration."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.errors import AppError
from app.repositories import platform_admin_invitations as token_repo
from app.schemas.super_admin_registration import SuperAdminRegisterRequest
from app.services import invitation_abuse_controls as abuse
from app.services import super_admin_registration as svc


class FakeQuery:
    def __init__(self, store, table):
        self.store, self.table = store, table
        self.filters, self.op, self.payload, self.gt_filters = [], "select", None, []

    def select(self, *_a, **_k):
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def gt(self, key, value):
        self.gt_filters.append((key, value))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        rows = self.store.setdefault(self.table, [])
        if self.op == "insert":
            row = {"invitation_id": f"00000000-0000-0000-0000-{len(rows):012d}", "status": "invited",
                   "created_at": datetime.now(timezone.utc).isoformat(), **self.payload}
            rows.append(row)
            return SimpleNamespace(data=[row])
        matched = [r for r in rows if all(r.get(k) == v for k, v in self.filters)
                   and all(str(r.get(k)) > str(v) for k, v in self.gt_filters)]
        if self.op == "update":
            for r in matched:
                r.update(self.payload)
        return SimpleNamespace(data=matched)


class FakeClient:
    def __init__(self):
        self.store, self.rpcs = {}, []

    def table(self, name):
        return FakeQuery(self.store, name)

    def rpc(self, name, params):
        self.rpcs.append((name, params))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=[]))


@pytest.fixture
def client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(svc, "get_admin_client", lambda: fake)
    monkeypatch.setattr(svc.student_svc, "_create_auth_account", lambda e, p: "auth-1")
    monkeypatch.setattr(svc.student_svc, "_create_public_user", lambda *a: "user-1")
    monkeypatch.setattr(svc.student_svc, "_try_delete_user_row", lambda *a: None)
    monkeypatch.setattr(svc.student_svc, "_try_delete_auth_user", lambda *a: None)
    monkeypatch.setattr(abuse, "_enforce", lambda *a, **k: None)
    return fake


def _body(**over):
    data = {"password": "correct horse", "confirm_password": "correct horse",
            "first_name": "Ada", "last_name": "Root"}
    data.update(over)
    return SuperAdminRegisterRequest(**data)


def _invite(client):
    return svc.create_invitation({"user_id": "actor-1"}, "new@example.com")


def test_invite_stores_only_hash(client):
    created = _invite(client)
    row = client.store[svc.TABLE][0]
    assert created.invitation_token not in str(row)
    assert row["token_hash"] == token_repo.hash_invitation_token(created.invitation_token)


def test_duplicate_pending_invite_conflicts(client):
    _invite(client)
    with pytest.raises(AppError) as exc:
        _invite(client)
    assert exc.value.code == "INVITATION_ALREADY_PENDING"


def test_register_grants_platform_super_admin_once(client):
    created = _invite(client)
    result = svc.register_super_admin(created.invitation_token, _body())
    assert result.role == "super_admin" and result.email == "new@example.com"
    assert client.rpcs[0][0] == "phase712_assign_super_admin"
    assert client.rpcs[0][1]["p_target_email"] == "new@example.com"
    with pytest.raises(AppError) as exc:
        svc.register_super_admin(created.invitation_token, _body())
    assert exc.value.code == "INVITATION_ALREADY_ACCEPTED"


def test_password_mismatch_and_unknown_token(client):
    created = _invite(client)
    with pytest.raises(AppError) as exc:
        svc.register_super_admin(created.invitation_token, _body(confirm_password="other pass"))
    assert exc.value.code == "PASSWORD_MISMATCH"
    with pytest.raises(AppError) as exc:
        svc.register_super_admin("x" * 64, _body())
    assert exc.value.code == "INVITATION_INVALID"


def test_expired_and_cancelled_tokens_refused(client):
    created = _invite(client)
    client.store[svc.TABLE][0]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()
    with pytest.raises(AppError) as exc:
        svc.register_super_admin(created.invitation_token, _body())
    assert exc.value.code == "INVITATION_EXPIRED"

    client.store[svc.TABLE].clear()
    created = _invite(client)
    svc.cancel_invitation({"user_id": "actor-1"}, "00000000-0000-0000-0000-000000000000")
    with pytest.raises(AppError) as exc:
        svc.register_super_admin(created.invitation_token, _body())
    assert exc.value.code == "INVITATION_CANCELLED"


def test_request_rejects_role_field():
    with pytest.raises(Exception):
        SuperAdminRegisterRequest(**{**_body().model_dump(), "role": "super_admin"})

