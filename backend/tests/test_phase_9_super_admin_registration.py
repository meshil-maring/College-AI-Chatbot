"""Phase 9 â€” invitation-only Super Admin registration."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

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

    def is_(self, key, value):
        self.filters.append((key, None if value == "null" else value))
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
        self.auth = MagicMock()

    def table(self, name):
        return FakeQuery(self.store, name)

    def rpc(self, name, params):
        self.rpcs.append((name, params))
        def execute():
            operations = self.store.setdefault("b05_invitation_operations", [])
            if name == "b05_transition_invitation":
                row = next((r for r in self.store.get(svc.TABLE, []) if r["invitation_id"] == params["p_id"]), None)
                if not row or row["status"] not in ("invited",params["p_status"]):
                    return SimpleNamespace(data=None)
                repeated = row["status"] == params["p_status"]
                if not repeated and row.get("acceptance_id"):
                    return SimpleNamespace(data=None)
                row["status"] = params["p_status"]
                events = self.store.setdefault("lifecycle_audit", {})
                events.setdefault(("platform",params["p_id"],params["p_status"]),params["p_actor"])
                return SimpleNamespace(data={"closed":True,"already_applied":repeated,"audit_persisted":True,"invitation":row.copy()})
            if name == "b05_recover_accepted_invitation":
                row = next((r for r in self.store.get(svc.TABLE, []) if r["invitation_id"] == params["p_id"]), None)
                op = next((o for o in operations if row and o["acceptance_id"] == row.get("acceptance_id")), None)
                valid = row and row["token_hash"] == params["p_digest"] and row["status"] == "accepted" and op and op["new_account"]
                return SimpleNamespace(data=op.copy() if valid else None)
            if name == "b05_advance_invitation_operation":
                op = next(o for o in operations if o["acceptance_id"] == params["p_acceptance_id"])
                assert op["stage"] == params["p_expected_stage"]
                op["stage"] = params["p_stage"]
                if params["p_auth_user_id"]: op["auth_user_id"] = params["p_auth_user_id"]
                if op["stage"] == "user_created": op["user_id"] = "user-1"
                return SimpleNamespace(data=op.copy())
            row = next((r for r in self.store.get(svc.TABLE, [])
                        if r["invitation_id"] == params["p_invitation_id"]), None)
            data = None
            if row and row["token_hash"] == params["p_token_hash"]:
                if name == "b05_reserve_invitation":
                    if not row.get("acceptance_id"):
                        row["acceptance_id"] = params["p_acceptance_id"]
                        operations.append({"acceptance_id":row["acceptance_id"],"stage":"reserved",
                            "new_account":True,"auth_user_id":None,"user_id":None})
                    data = next(o.copy() for o in operations if o["acceptance_id"] == row["acceptance_id"])
                elif name == "b05_finalize_invitation" and row.get("acceptance_id") == params["p_acceptance_id"]:
                    row.update(status="accepted", accepted_user_id=params["p_target_user_id"])
                    next(o for o in operations if o["acceptance_id"] == row["acceptance_id"])["stage"] = "accepted"
                    data = {"accepted": True}
            return SimpleNamespace(data=data)
        return SimpleNamespace(execute=execute)


@pytest.fixture
def client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(svc, "get_admin_client", lambda: fake)
    monkeypatch.setattr(svc.student_svc, "_create_auth_account", lambda e, p, **k: "auth-1")
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


@pytest.mark.parametrize("status,reserved,expected", [
    ("invited",False,"cancelled"), ("invited",True,"INVITATION_CANCELLATION_CONFLICT"),
    ("accepted",False,"INVITATION_CANCELLATION_CONFLICT"),
    ("expired",False,"INVITATION_CANCELLATION_CONFLICT"), ("cancelled",False,"cancelled"),
])
def test_platform_cancellation_states(client,status,reserved,expected):
    created = _invite(client)
    row = client.store[svc.TABLE][0]
    row["status"] = status
    if reserved: row["acceptance_id"] = "operation-1"
    if expected == "cancelled":
        result = svc.cancel_invitation({"user_id":"actor-1"},str(created.invitation.invitation_id))
        assert result.status == "cancelled" and row["status"] == "cancelled"
    else:
        with pytest.raises(AppError) as caught:
            svc.cancel_invitation({"user_id":"actor-1"},str(created.invitation.invitation_id))
        assert caught.value.code == expected
        assert row["status"] == status


def test_expired_platform_reservation_cannot_be_replaced(client):
    _invite(client)
    row = client.store[svc.TABLE][0]
    row.update(acceptance_id="operation-1", expires_at="2000-01-01T00:00:00Z")
    with pytest.raises(AppError) as caught: _invite(client)
    assert caught.value.code == "INVITATION_RECONCILIATION_REQUIRED"
    assert len(client.store[svc.TABLE]) == 1


def test_platform_cancellation_lost_response_is_explicit(client, monkeypatch):
    created = _invite(client)
    monkeypatch.setattr(token_repo,"transition_invitation",MagicMock(side_effect=TimeoutError()))
    with pytest.raises(AppError) as caught:
        svc.cancel_invitation({"user_id":"actor-1"},str(created.invitation.invitation_id))
    assert caught.value.code == "INVITATION_CANCELLATION_UNCERTAIN"


def test_register_grants_platform_super_admin_once(client):
    created = _invite(client)
    result = svc.register_super_admin(created.invitation_token, _body())
    assert result.role == "super_admin" and result.email == "new@example.com"
    assert [name for name, _ in client.rpcs] == [
        "b05_reserve_invitation", "b05_advance_invitation_operation", "b05_advance_invitation_operation",
        "b05_advance_invitation_operation", "b05_finalize_invitation", "b05_advance_invitation_operation"]
    assert all(params["p_kind"] == "platform" for name, params in client.rpcs
               if name in ("b05_reserve_invitation","b05_finalize_invitation"))
    assert svc.register_super_admin(created.invitation_token,_body()).email == result.email
    assert sum(name == "b05_finalize_invitation" for name, _ in client.rpcs) == 1
    client.auth.admin.update_user_by_id.assert_called_once_with("auth-1", {"email_confirm":True})


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

