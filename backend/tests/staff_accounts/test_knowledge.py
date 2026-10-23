from .support import (
    INSTITUTION_A,
    INSTITUTION_B,
    _active_institution_authorization,
    _assert_staff_forbidden,
    _ingest_with_tenant,
)


def test_staff_denied_admin_knowledge_sources():
    _assert_staff_forbidden(
        "GET", f"/api/v1/admin/knowledge-sources?institution_id={INSTITUTION_A}"
    )


def test_staff_ingest_allowed_for_own_tenant():
    response = _ingest_with_tenant(INSTITUTION_A)
    # Reaching the pipeline (201) proves the role + tenant gate passed; the
    # pipeline itself is covered by test_ingestion.py.
    assert response.status_code == 201


def test_staff_ingest_denied_for_cross_tenant_knowledge_source():
    """Staff A (Institution A) cannot ingest into Institution B's source."""
    response = _ingest_with_tenant(INSTITUTION_B)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
