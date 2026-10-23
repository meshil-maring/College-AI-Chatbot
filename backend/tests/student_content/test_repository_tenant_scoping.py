from .support import (
    NOTICE_A,
    NOTICE_B,
    RESOURCE_A,
    RESOURCE_B,
    TENANT_A,
    TENANT_B,
    _FakeClient,
    _clear_dependency_overrides,
    _notice_row,
    _resource_row,
    dashboard_repo,
    pytest,
)


class TestRepositoryTenantScoping:
    def test_notice_query_always_filters_on_the_given_institution(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A, institution_id=TENANT_A),
                    _notice_row(
                        notice_id=NOTICE_B,
                        institution_id=TENANT_B,
                        title="Other tenant",
                    ),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(db, TENANT_A)
        assert [r["notice_id"] for r in rows] == [NOTICE_A]
        assert ("notices", "eq", "institution_id", TENANT_A) in db.calls
        assert ("notices", "eq", "institution_id", TENANT_B) not in db.calls

    def test_notice_query_never_spans_institutions(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A, institution_id=TENANT_A),
                    _notice_row(notice_id=NOTICE_B, institution_id=TENANT_B),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(db, TENANT_B)
        assert [r["notice_id"] for r in rows] == [NOTICE_B]

    def test_resource_query_always_filters_on_the_given_institution(self):
        db = _FakeClient(
            {
                "knowledge_sources": [
                    _resource_row(
                        knowledge_source_id=RESOURCE_A, institution_id=TENANT_A
                    ),
                    _resource_row(
                        knowledge_source_id=RESOURCE_B, institution_id=TENANT_B
                    ),
                ]
            }
        )
        rows = dashboard_repo.list_published_resources(db, TENANT_A)
        assert [r["knowledge_source_id"] for r in rows] == [RESOURCE_A]
        assert ("knowledge_sources", "eq", "institution_id", TENANT_A) in db.calls

    def test_institution_id_is_a_mandatory_argument(self):
        with pytest.raises(TypeError):
            dashboard_repo.list_published_notices(_FakeClient())
        with pytest.raises(TypeError):
            dashboard_repo.list_published_resources(_FakeClient())
