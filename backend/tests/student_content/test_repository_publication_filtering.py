from .support import (
    NOTICE_A,
    NOTICE_B,
    RESOURCE_A,
    RESOURCE_B,
    TENANT_A,
    STUDENT_USER_ID,
    _FakeClient,
    _clear_dependency_overrides,
    _notice_row,
    _resource_row,
    dashboard_repo,
)


class TestRepositoryPublicationFiltering:
    def test_notices_require_active_and_published(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A),
                    _notice_row(notice_id=NOTICE_B, is_active=False),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(db, TENANT_A)
        assert [r["notice_id"] for r in rows] == [NOTICE_A]
        assert ("notices", "eq", "is_active", True) in db.calls
        assert ("notices", "eq", "is_published", True) in db.calls

    def test_unpublished_notices_are_never_returned(self):
        db = _FakeClient({"notices": [_notice_row(is_published=False)]})
        assert dashboard_repo.list_published_notices(db, TENANT_A) == []

    def test_expired_notices_are_excluded(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A, expires_at=None),
                    _notice_row(
                        notice_id=NOTICE_B, expires_at="2000-01-01T00:00:00+00:00"
                    ),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(
            db, TENANT_A, now="2026-09-21T00:00:00+00:00"
        )
        assert [r["notice_id"] for r in rows] == [NOTICE_A]
        expiry_filters = [c for c in db.calls if c[1] == "or_"]
        assert expiry_filters, "the expiry boundary must always be applied"
        assert "expires_at.is.null" in expiry_filters[0][2]

    def test_future_dated_expiry_is_kept(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(
                        notice_id=NOTICE_A, expires_at="2999-01-01T00:00:00+00:00"
                    )
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(
            db, TENANT_A, now="2026-09-21T00:00:00+00:00"
        )
        assert [r["notice_id"] for r in rows] == [NOTICE_A]

    def test_pinned_notices_come_first(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(
                        notice_id=NOTICE_A,
                        is_pinned=False,
                        published_at="2026-09-20T00:00:00+00:00",
                    ),
                    _notice_row(
                        notice_id=NOTICE_B,
                        is_pinned=True,
                        published_at="2026-09-01T00:00:00+00:00",
                    ),
                ]
            }
        )
        rows = dashboard_repo.list_published_notices(db, TENANT_A)
        assert [r["notice_id"] for r in rows] == [NOTICE_B, NOTICE_A]
        assert ("notices", "order", "is_pinned", True) in db.calls
        assert ("notices", "order", "published_at", True) in db.calls

    def test_notice_limit_is_applied_server_side(self):
        db = _FakeClient(
            {
                "notices": [
                    _notice_row(notice_id=NOTICE_A),
                    _notice_row(notice_id=NOTICE_B),
                ]
            }
        )
        assert len(dashboard_repo.list_published_notices(db, TENANT_A, limit=1)) == 1
        assert ("notices", "limit", 1) in db.calls

    def test_resources_require_published_lifecycle_status(self):
        db = _FakeClient(
            {
                "knowledge_sources": [
                    _resource_row(
                        knowledge_source_id=RESOURCE_A, lifecycle_status="published"
                    ),
                    _resource_row(
                        knowledge_source_id=RESOURCE_B, lifecycle_status="draft"
                    ),
                ]
            }
        )
        rows = dashboard_repo.list_published_resources(db, TENANT_A, actor_user_id=STUDENT_USER_ID)
        assert [r["knowledge_source_id"] for r in rows] == [RESOURCE_A]
        assert ("knowledge_sources", "eq", "lifecycle_status", "published") in db.calls

    def test_resources_exclude_source_types_with_their_own_student_surface(self):
        db = _FakeClient(
            {
                "knowledge_sources": [
                    _resource_row(
                        knowledge_source_id=RESOURCE_A, source_type="handbook"
                    ),
                    _resource_row(knowledge_source_id=RESOURCE_B, source_type="notice"),
                ]
            }
        )
        rows = dashboard_repo.list_published_resources(db, TENANT_A, actor_user_id=STUDENT_USER_ID)
        assert [r["knowledge_source_id"] for r in rows] == [RESOURCE_A]
        assert ("knowledge_sources", "neq", "source_type", "notice") in db.calls
        assert ("knowledge_sources", "neq", "source_type", "faq") in db.calls

    def test_excluded_source_types_match_the_locked_public_vocabulary(self):
        """Drift guard against the locked Phase 6.13.8 source-type vocabulary."""
        from app.services.ai.public_chat import PUBLIC_SOURCE_TYPES

        assert set(dashboard_repo.EXCLUDED_RESOURCE_SOURCE_TYPES) <= set(
            PUBLIC_SOURCE_TYPES
        )
