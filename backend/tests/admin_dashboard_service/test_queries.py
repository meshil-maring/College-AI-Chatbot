from .support import (
    MagicMock,
    _db,
    _no_notices,
    svc,
    uuid4,
)


def test_dashboard_summary_scopes_every_institution_owned_count() -> None:
    """The core tenant guarantee: no count may run without the tenant filter."""
    db = _db()
    institution_id = str(uuid4())
    with _no_notices():
        svc.get_dashboard_summary(institution_id=institution_id, client=db)

    # Every table queried directly must carry the institution filter.
    for name in ("knowledge_sources", "faqs", "notices", "students"):
        eq_args = [
            call.args
            for call in db._registry[name].select.return_value.eq.call_args_list
        ]
        assert ("institution_id", institution_id) in eq_args, name

    # is_active filter applied for faqs and notices (chained .eq()).
    for name in ("faqs", "notices"):
        chained = db._registry[name].select.return_value.eq.return_value
        assert ("is_active", True) in [call.args for call in chained.eq.call_args_list]

    # Related tables resolve the tenant through an !inner join, never a direct
    # unscoped count.
    related_scopes = {
        "documents": "knowledge_sources.institution_id",
    }
    for name, field in related_scopes.items():
        db._registry[name].select.return_value.eq.assert_called_once_with(
            field, institution_id
        )


def test_count_returns_zero_when_count_missing() -> None:
    db = MagicMock()
    db.table.return_value.select.return_value.execute.return_value = MagicMock(
        count=None, data=[]
    )
    assert svc._count(db, "faqs") == 0


def test_related_count_uses_inner_tenant_relationship() -> None:
    db = MagicMock()
    response = MagicMock(count=7, data=[])
    chain = db.table.return_value.select.return_value
    chain.eq.return_value.execute.return_value = response
    institution_id = str(uuid4())

    assert (
        svc._count_related(
            db,
            "documents",
            "document_id",
            "knowledge_sources",
            institution_id,
        )
        == 7
    )
    db.table.assert_called_once_with("documents")
    db.table.return_value.select.assert_called_once_with(
        "document_id, knowledge_sources!inner(institution_id)", count="exact"
    )
    chain.eq.assert_called_once_with("knowledge_sources.institution_id", institution_id)


def test_count_in_applies_tenant_filter_on_the_same_query() -> None:
    """The ``in_`` variant must not drop the institution scoping."""
    db = MagicMock()
    response = MagicMock(count=3, data=[])
    chain = db.table.return_value.select.return_value
    chain.eq.return_value.in_.return_value.execute.return_value = response
    institution_id = str(uuid4())

    assert svc._count_in(db, "knowledge_sources", institution_id, ["published"]) == 3
    chain.eq.assert_called_once_with("institution_id", institution_id)
    chain.eq.return_value.in_.assert_called_once_with("lifecycle_status", ["published"])
