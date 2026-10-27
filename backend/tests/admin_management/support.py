"""Shared authorization principals and test doubles."""

import itertools

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

import pytest

from fastapi.testclient import TestClient

from app.api.admin.dependencies import _ADMIN

from app.api.admin.dependencies import _APPROVAL

from app.core.security import get_current_user

from app.main import app

from app.schemas.admin.admin_dashboard import DashboardRecentNotice

from tests.dashboard_contract import build_dashboard
from tests.auth_fixtures.principals import institution_grant, resolved_principal

client = TestClient(app, raise_server_exceptions=False)

ADMIN_USER = resolved_principal({
    "user_id": "70000000-0000-0000-0000-000000000001",
    "auth_user_id": "70000000-0000-0000-0000-0000000000aa",
    "email": "admin@example.com",
    "roles": ["admin"],
    "status": "active",
    "institution_id": "30000000-0000-0000-0000-000000000001",
    "role_assignments": [institution_grant("admin", "30000000-0000-0000-0000-000000000001")],
})

STUDENT_USER = {
    "user_id": "70000000-0000-0000-0000-000000000002",
    "auth_user_id": "70000000-0000-0000-0000-0000000000bb",
    "email": "student@example.com",
    "status": "active",
    "roles": ["student"],
}

INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"

KS_ID = str(uuid4())

FAQ_ID = str(uuid4())

NOTICE_ID = str(uuid4())

DOC_ID = str(uuid4())


@pytest.fixture(autouse=True)
def admin_auth():
    """All tests in this module run as an authenticated admin by default."""
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
    app.dependency_overrides[_ADMIN] = lambda: ADMIN_USER
    app.dependency_overrides[_APPROVAL] = lambda: ADMIN_USER
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch(
            "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
            return_value={"institution_id": INSTITUTION_ID, "status": "active", "is_active": True},
        ),
        patch(
            "app.repositories.admin.admin_knowledge.get_knowledge_source_detail",
            return_value={
                "knowledge_source_id": KS_ID,
                "institution_id": INSTITUTION_ID,
            },
        ),
        patch(
            "app.repositories.admin.admin_knowledge.get_document_with_versions",
            return_value={
                "document_id": DOC_ID,
                "knowledge_source_id": KS_ID,
            },
        ),
    ):
        yield
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)


def _audit_db(first_insert: dict | None = None):
    """Mock service-role client for the API layer (audit + simple inserts).

    The first ``.insert()`` returns ``first_insert`` (the created entity row);
    every later insert (typically the audit-log row) returns a generic row.
    """
    db = MagicMock()
    first = MagicMock(data=[first_insert if first_insert is not None else {"id": "x"}])
    audit = MagicMock(data=[{"audit_id": str(uuid4())}])
    db.table.return_value.insert.return_value.execute.side_effect = itertools.chain(
        [first], itertools.repeat(audit)
    )
    return db


def _audit_rows(db):
    """Extract rows passed to .insert() calls on the shared mock chain."""
    return [
        call.args[0]
        for call in db.table.return_value.insert.call_args_list
        if call.args
    ]


def _faq_row() -> dict:
    return {
        "faq_id": FAQ_ID,
        "institution_id": INSTITUTION_ID,
        "category": "general",
        "question": "When is the library open?",
        "answer": "8am to 10pm on weekdays.",
        "display_order": 0,
        "is_active": True,
    }
