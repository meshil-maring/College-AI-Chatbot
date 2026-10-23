"""Test authentication."""

from __future__ import annotations

from uuid import uuid4

from .support import (
    RUN_ID,
    STUDENT_A,
    TENANT_A,
    _active_scope_lookup,
    _as,
    _clear,
    _user,
    client,
)


def test_unauthenticated_admin_me_is_401():
    _clear()
    try:
        resp = client.get("/api/v1/admin/me")
    finally:
        _clear()
    assert resp.status_code == 401


def test_unauthenticated_approval_endpoints_are_401():
    _clear()
    try:
        r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
        r2 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
        r3 = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert (r1.status_code, r2.status_code, r3.status_code) == (401, 401, 401)


def test_unauthenticated_ingest_endpoints_are_401():
    _clear()
    try:
        r0 = client.post("/api/v1/documents/ingest")
        r1 = client.post(f"/api/v1/documents/{RUN_ID}/extract")
        r2 = client.post(f"/api/v1/documents/{RUN_ID}/chunk")
        r3 = client.post(f"/api/v1/documents/{RUN_ID}/embed")
    finally:
        _clear()
    assert (r0.status_code, r1.status_code, r2.status_code, r3.status_code) == (
        401,
        401,
        401,
        401,
    )


def test_unauthenticated_student_me_endpoints_are_401():
    _clear()
    try:
        paths = [
            "/api/v1/students/me/profile",
            "/api/v1/students/me/notices",
            "/api/v1/students/me/resources",
        ]
        statuses = [client.get(path).status_code for path in paths]
    finally:
        _clear()
    assert statuses == [401, 401, 401]


def test_unauthenticated_conversations_and_chat_are_401():
    _clear()
    try:
        r1 = client.get("/api/v1/conversations")
        r2 = client.get(f"/api/v1/conversations/{uuid4()}/messages")
        r3 = client.post(
            "/api/v1/generation/chat",
            json={"user_query": "hello", "institution_id": TENANT_A},
        )
    finally:
        _clear()
    assert (r1.status_code, r2.status_code, r3.status_code) == (401, 401, 401)


def test_admin_can_access_permitted_admin_operation():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        resp = client.get("/api/v1/admin/me")
    finally:
        _clear()
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True
