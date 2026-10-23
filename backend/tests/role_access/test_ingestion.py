"""Test ingestion."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import uuid4

from .support import (
    KS_ID,
    RUN_ID,
    STUDENT_A,
    TENANT_A,
    TENANT_B,
    _active_scope_lookup,
    _as,
    _clear,
    _user,
    client,
)


def test_faculty_can_reach_permitted_ingestion_operation():
    faculty = {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "faculty@college.edu",
        "roles": ["faculty"],
        "status": "active",
        "role_assignments": [
            {
                "role": "faculty",
                "scope_type": "institution",
                "scope_id": TENANT_A,
                "scope_organization_id": None,
                "is_active": True,
                "permissions": ["ai.knowledge.create"],
            }
        ],
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
    }
    run = {
        "processing_run_id": RUN_ID,
        "status": "ready",
        "document_versions": {
            "document_version_id": str(uuid4()),
            "knowledge_source_id": KS_ID,
        },
    }
    claims = {"sub": faculty["auth_user_id"], "email": faculty["email"]}
    p1 = patch("app.core.security.tokens.verify_jwt", return_value=claims)
    p2 = patch(
        "app.db.supabase.get_user_by_auth_id",
        new=AsyncMock(return_value=faculty),
    )
    with (
        p1,
        p2,
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch(
            "app.api.knowledge.ingestion.get_processing_run_with_version",
            return_value=run,
        ),
        patch(
            "app.api.knowledge.ingestion.knowledge_repo.get_knowledge_source_detail",
            return_value={"knowledge_source_id": KS_ID, "institution_id": TENANT_A},
        ),
        patch("app.api.knowledge.ingestion.get_extracted_text", return_value="text"),
        patch("app.api.knowledge.ingestion.delete_chunks_for_run"),
        patch("app.api.knowledge.ingestion.insert_chunks"),
        patch("app.api.knowledge.ingestion.update_run_status"),
    ):
        resp = client.post(
            f"/api/v1/documents/{RUN_ID}/chunk",
            headers={"Authorization": "Bearer faculty.token"},
        )
    assert resp.status_code == 200


def test_faculty_cannot_access_admin_only_operation():
    _as(_user(TENANT_A, roles=("faculty",)))
    try:
        resp = client.get("/api/v1/admin/me")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_faculty_cannot_access_staff_only_approval_operation():
    _as(_user(TENANT_A, roles=("faculty",)))
    try:
        r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
        r2 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
        r3 = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert (r1.status_code, r2.status_code, r3.status_code) == (403, 403, 403)


def test_faculty_cannot_cross_tenant_on_ingest():
    faculty = {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "faculty@college.edu",
        "roles": ["faculty"],
        "status": "active",
        "institution_id": TENANT_A,
        "role_assignments": [
            {
                "role": "faculty",
                "scope_type": "institution",
                "scope_id": TENANT_A,
                "scope_organization_id": None,
                "is_active": True,
                "permissions": ["ai.knowledge.create"],
            }
        ],
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
    }
    ks = {"knowledge_source_id": KS_ID, "institution_id": TENANT_B}
    claims = {"sub": faculty["auth_user_id"], "email": faculty["email"]}
    p1 = patch("app.core.security.tokens.verify_jwt", return_value=claims)
    p2 = patch(
        "app.db.supabase.get_user_by_auth_id",
        new=AsyncMock(return_value=faculty),
    )
    with (
        p1,
        p2,
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=ks),
    ):
        resp = client.post(
            "/api/v1/documents/ingest",
            headers={"Authorization": "Bearer faculty.token"},
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", b"%PDF", "application/pdf")},
        )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
