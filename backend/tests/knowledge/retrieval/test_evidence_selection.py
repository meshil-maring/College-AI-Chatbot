"""Metadata cannot crowd all actual policy content out of a bounded answer."""

from copy import deepcopy

import pytest

from app.services.knowledge.evidence_selection import candidate_limit, select_evidence
from .conftest import row


def test_metadata_heavy_results_expand_without_increasing_final_context(metadata_rows, policy_rows):
    original = deepcopy(metadata_rows)
    expanded = metadata_rows + policy_rows
    assert candidate_limit(metadata_rows, 4) == 12

    selected = select_evidence(metadata_rows, expanded, 4)

    assert len(selected) == 4
    assert selected[0] == metadata_rows[1]
    assert selected[1:] == policy_rows
    assert 'not an officially approved college policy' in selected[0]['content_text']
    assert metadata_rows == original
    assert all(item in expanded for item in selected)


@pytest.mark.parametrize('count,limit', [(2, 6), (4, 12), (8, 20), (19, 20), (20, 20)])
def test_expansion_is_capped_at_database_search_limit(metadata_rows, count, limit):
    assert candidate_limit([metadata_rows[0]] * count, count) == limit


def test_empty_partial_and_substantive_results_do_not_expand(metadata_rows, policy_rows):
    assert candidate_limit([], 4) == 4
    assert candidate_limit(metadata_rows[:2], 4) == 4
    assert candidate_limit(policy_rows + [policy_rows[0]], 4) == 4
    assert candidate_limit(metadata_rows[:1], 1) == 1


def test_missing_or_multiple_document_versions_do_not_trigger_expansion(metadata_rows):
    missing = [dict(item, document_version_id=None) for item in metadata_rows]
    multiple = deepcopy(metadata_rows)
    multiple[0]['document_id'] = 'different-document'
    assert candidate_limit(missing, 4) == 4
    assert candidate_limit(multiple, 4) == 4


def test_expansion_cannot_introduce_a_new_document_or_version(metadata_rows, policy_rows):
    unrelated = [
        row(8, 'Other document', 'Other college rules.', document_id='another-document'),
        row(9, 'Other version', 'Superseded rules.', document_version_id='another-version'),
    ]
    selected = select_evidence(metadata_rows, unrelated + metadata_rows + policy_rows, 4)
    assert selected == [metadata_rows[1], *policy_rows]


def test_empty_expansion_and_metadata_only_files_keep_original_evidence(metadata_rows):
    assert select_evidence(metadata_rows, [], 4) == metadata_rows
    assert select_evidence(metadata_rows, list(reversed(metadata_rows)), 4) == metadata_rows


def test_source_qualification_is_retained_over_longer_general_scope(metadata_rows, policy_rows):
    metadata_rows[2]['content_text'] = 'The policy describes rules for residents. ' * 100
    selected = select_evidence(metadata_rows, metadata_rows + policy_rows, 4)
    assert selected[0] == metadata_rows[1]
    assert 'not an officially approved college policy' in selected[0]['content_text']


def test_repeated_text_does_not_displace_another_rule(metadata_rows, policy_rows):
    duplicate = dict(policy_rows[0], chunk_id='duplicate-chunk')
    selected = select_evidence(metadata_rows, metadata_rows + [duplicate] + policy_rows, 4)
    assert len({item['content_text'] for item in selected}) == 4
    assert selected[-1] == policy_rows[-1]
