"""Exercise registration, the approval queue, decisions and login together.

Only Supabase clients are replaced. HTTP routing, registration validation,
repositories, approval authorization and student login guards remain real.
The approval RPC is an external transaction boundary; its SQL needs a database
replay in addition to these application-level journey checks.
"""

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core.security import get_current_user
from app.main import app

INST = "11000000-0000-0000-0000-000000000001"
ORG = "12000000-0000-0000-0000-000000000001"
USER = "13000000-0000-0000-0000-000000000001"
AUTH = "14000000-0000-0000-0000-000000000001"
STUDENT = "15000000-0000-0000-0000-000000000001"
ACTOR = {
    "user_id": "16000000-0000-0000-0000-000000000001",
    "auth_user_id": "17000000-0000-0000-0000-000000000001",
    "status": "active", "roles": ["admin"], "institution_id": INST,
    "role_assignments": [{"role": "admin", "scope_type": "institution",
                          "scope_id": INST, "scope_organization_id": ORG, "is_active": True}],
}


class Table:
    def __init__(self, database, name):
        self.database, self.name = database, name
        self.filters, self.columns, self.insertion, self.updates = {}, "", None, None
        self.single = False

    def select(self, columns):
        self.columns = columns
        return self

    def eq(self, column, value):
        self.filters[column] = str(value)
        return self

    def maybe_single(self):
        self.single = True
        return self

    def insert(self, row):
        self.insertion = dict(row)
        return self

    def update(self, values):
        self.updates = values
        return self

    def order(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def range(self, *_args):
        return self

    def execute(self):
        rows = self.database.rows.setdefault(self.name, [])
        if self.insertion is not None:
            defaults = {"users": {"id": USER}, "students": {"student_id": STUDENT}}
            row = defaults.get(self.name, {}) | self.insertion
            rows.append(row)
            return SimpleNamespace(data=[dict(row)])
        matches = [row for row in rows if all(str(row.get(k)) == v for k, v in self.filters.items())]
        if self.updates:
            for row in matches:
                row.update(self.updates)
        result = [dict(row) for row in matches]
        if "user_id:id" in self.columns:
            for row in result:
                row["user_id"] = row["id"]
        return (SimpleNamespace(data=result[0]) if result else None) if self.single else SimpleNamespace(data=result)


class Database:
    def __init__(self):
        self.rows = {
            "institutions": [{"institution_id": INST, "organization_id": ORG,
                              "code": "QUEST123", "name": "Quest", "status": "active", "is_active": True}],
            "organizations": [{"organization_id": ORG, "status": "active", "is_active": True}],
            "user_roles": [], "admin_audit_log": [],
        }

    def table(self, name):
        return Table(self, name)

    def rpc(self, name, parameters):
        assert name == "b05_approve_student"
        assert parameters == {"p_student_id": STUDENT, "p_institution_id": INST,
                              "p_actor_user_id": ACTOR["user_id"], "p_actor_auth_user_id": ACTOR["auth_user_id"]}
        def commit():
            student = self.rows["students"][0]
            student["approval_status"] = "approved"
            self.rows["user_roles"].append({"user_id": USER, "role": "student", "scope_id": INST})
            self.rows["admin_audit_log"].append({"action": "student.approve"})
            return SimpleNamespace(data={"student": dict(student), "role_granted": True, "audit_persisted": True})
        return SimpleNamespace(execute=commit)


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_student_registration_through_institution_decision_and_login(decision):
    database = Database()
    provider = MagicMock()
    provider.auth.sign_up.return_value = SimpleNamespace(user=SimpleNamespace(id=AUTH, identities=[{}]))
    provider.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id=AUTH, email="student@example.com"),
        session=SimpleNamespace(access_token="student-token", refresh_token="student-refresh", expires_in=3600),
    )
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: ACTOR
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(settings, "auth_rate_limit_enabled", False))
            for module in ["services.auth.user_registration", "services.auth.student_registration", "services.admin.admin_academics",
                           "services.auth.student_auth", "services.auth.auth_security", "services.auth.authorization", "services.platform.tenancy", "api.admin.common"]:
                stack.enter_context(patch(f"app.{module}.get_admin_client", return_value=database))
            for module in ["services.auth.student_registration", "services.auth.student_auth"]:
                stack.enter_context(patch(f"app.{module}.create_supabase_client", return_value=provider))
            client = TestClient(app)
            assert client.get("/api/v1/institutions/lookup?code=quest123").status_code == 200
            payload = {"registration_type": "student", "institution_code": "QUEST123",
                       "email": "student@example.com", "password": "test-password",
                       "first_name": "Test", "last_name": "Student",
                       "register_number": "REG-1001", "university_roll_number": "ROLL-1001"}
            # Lookup uses the same client through the tenancy service.
            registered = client.post("/api/v1/users/register", json=payload)
            assert registered.status_code == 201, registered.text
            assert registered.json()["approval_status"] == "pending"
            assert "access_token" not in registered.json()
            assert database.rows["user_roles"] == []
            duplicate = client.post("/api/v1/users/register", json=payload)
            assert duplicate.status_code == 409
            login = {"identifier": "REG-1001", "institution_code": "QUEST123", "password": "test-password"}
            assert client.post("/api/v1/auth/student/login", json=login).status_code == 401
            provider.auth.sign_in_with_password.assert_not_called()
            queue = client.get("/api/v1/admin/students/pending")
            assert queue.status_code == 200, queue.text
            assert [row["student_id"] for row in queue.json()] == [STUDENT]
            decided = client.post(f"/api/v1/admin/students/{STUDENT}/{decision}")
            assert decided.status_code == 200, decided.text
            assert decided.json()["approval_status"] == ("approved" if decision == "approve" else "rejected")
            assert client.get("/api/v1/admin/students/pending").json() == []
            for identifier in ["student@example.com", "REG-1001", "ROLL-1001"]:
                result = client.post("/api/v1/auth/student/login", json=login | {"identifier": identifier})
                assert result.status_code == (200 if decision == "approve" else 401), result.text
            assert len(database.rows["user_roles"]) == (1 if decision == "approve" else 0)
            assert database.rows["admin_audit_log"][0]["action"] == f"student.{decision}"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
