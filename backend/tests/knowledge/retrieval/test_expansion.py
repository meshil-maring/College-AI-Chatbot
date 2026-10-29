"""A second search retains the exact public/actor/tenant/version filters."""

from unittest.mock import MagicMock

import pytest

from app.core.errors import AppError
from app.schemas.knowledge.retrieval import RetrievalRequest
from app.services.knowledge import retrieval
from .conftest import ACTOR, DOCUMENT, RUN, SOURCE, TENANT, VERSION


@pytest.mark.parametrize('mode', ['public', 'authenticated', 'internal'])
def test_expansion_reuses_authorized_search_and_one_embedding(monkeypatch, metadata_rows, policy_rows, mode):
    embedding = [0.1] * 1536
    embed = MagicMock(return_value=embedding)
    search = MagicMock(side_effect=[metadata_rows, metadata_rows + policy_rows])
    client = object()
    target = {'public': 'search_public_chunks', 'authenticated': 'search_authorized_chunks',
        'internal': 'search_chunks'}[mode]
    monkeypatch.setattr(retrieval, 'embed_query', embed)
    monkeypatch.setattr(retrieval, 'get_admin_client', lambda: client)
    monkeypatch.setattr(retrieval, target, search)
    request = RetrievalRequest(query='Explain the hostel rules', top_k=4,
        institution_id=TENANT, knowledge_source_id=SOURCE, document_id=DOCUMENT,
        document_version_id=VERSION, processing_run_id=RUN, model_name='test-embedding',
        public_only=mode == 'public', actor_user_id=ACTOR if mode == 'authenticated' else None)

    result = retrieval.retrieve(request)

    embed.assert_called_once_with('Explain the hostel rules')
    assert search.call_count == 2
    first, expanded = search.call_args_list
    assert first.kwargs['top_k'] == 4 and expanded.kwargs['top_k'] == 12
    assert {key: value for key, value in first.kwargs.items() if key != 'top_k'} == {
        key: value for key, value in expanded.kwargs.items() if key != 'top_k'}
    assert expanded.kwargs['model_name'] == 'test-embedding'
    assert str(expanded.kwargs['knowledge_source_id']) == SOURCE
    if mode == 'authenticated':
        assert str(expanded.kwargs['actor']) == ACTOR
        assert str(expanded.kwargs['tenant']) == TENANT
        assert str(expanded.kwargs['document_version_id']) == VERSION
    else:
        assert str(expanded.kwargs['institution_id']) == TENANT
    assert len(result.results) == 4
    assert [item.text for item in result.results] == [metadata_rows[1]['content_text']] + [
        item['content_text'] for item in policy_rows]
    assert str(result.results[-1].document_version_id) == VERSION
    assert result.results[-1].metadata['processing_run_id'] == RUN
    assert result.results[-1].similarity_score == 1 - policy_rows[-1]['distance']


def test_substantive_results_keep_single_search_and_original_order(monkeypatch, policy_rows):
    search = MagicMock(return_value=policy_rows)
    monkeypatch.setattr(retrieval, 'embed_query', lambda _: [0.1] * 1536)
    monkeypatch.setattr(retrieval, 'get_admin_client', lambda: object())
    monkeypatch.setattr(retrieval, 'search_public_chunks', search)
    result = retrieval.retrieve(RetrievalRequest(query='What are hostel visitor rules?',
        top_k=3, institution_id=TENANT, public_only=True))
    search.assert_called_once()
    assert [str(item.chunk_id) for item in result.results] == [item['chunk_id'] for item in policy_rows]


def test_expansion_failure_is_not_silently_treated_as_success(monkeypatch, metadata_rows):
    search = MagicMock(side_effect=[metadata_rows, AppError('Access changed', 403, 'FORBIDDEN')])
    monkeypatch.setattr(retrieval, 'embed_query', lambda _: [0.1] * 1536)
    monkeypatch.setattr(retrieval, 'get_admin_client', lambda: object())
    monkeypatch.setattr(retrieval, 'search_public_chunks', search)
    with pytest.raises(AppError) as failure:
        retrieval.retrieve(RetrievalRequest(query='Hostel rules', top_k=4,
            institution_id=TENANT, public_only=True))
    assert failure.value.status_code == 403
    assert failure.value.code == 'RETRIEVAL_FAILED'
