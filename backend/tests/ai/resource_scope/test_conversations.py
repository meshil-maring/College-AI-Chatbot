"""Resource scope survives follow-ups and cannot be broadened or replaced."""

import pytest

from app.core.errors import AppError
from .conftest import ACTOR, TENANT, SOURCE, OTHER


def test_new_resource_chat_persists_scope_and_filters_retrieval(flow):
    response = flow.run()
    assert flow.state.conversation['knowledge_source_id'] == SOURCE
    assert flow.state.conversation['resource_institution_id'] == TENANT
    assert str(flow.retrieve.call_args.args[0].knowledge_source_id) == SOURCE
    assert response.resource_context.title == 'Library handbook'
    assert str(response.resource_context.knowledge_source_id) == SOURCE
    assert 'policy_version' not in response.resource_context.model_dump()
    assert flow.state.messages[-1].knowledge_policy['sources'] == {SOURCE: 3}


def test_followup_without_resource_id_still_uses_persisted_scope(flow):
    flow.run()
    flow.run('What about the borrowing period?', selected=None)
    assert str(flow.retrieve.call_args.args[0].knowledge_source_id) == SOURCE
    assert tuple(str(value) for value in flow.read.call_args.args[1:]) == (ACTOR, TENANT, SOURCE)


def test_resource_question_cannot_take_general_knowledge_path(flow):
    flow.run('What is photosynthesis?')
    flow.retrieve.assert_called_once()
    context = flow.provider.generate.call_args.args[0]
    assert context.retrieved_knowledge
    assert 'only the retrieved' in context.system_instructions


def test_empty_resource_evidence_does_not_fall_back_to_general_answer(flow):
    flow.retrieve.return_value.results = []
    response = flow.run('What is photosynthesis?')
    assert response.status == 'insufficient_context'
    flow.provider.generate.assert_not_called()


@pytest.mark.parametrize('selected,tenant,normal', [(OTHER, TENANT, False), (SOURCE, OTHER, False), (SOURCE, TENANT, True)])
def test_scope_switch_and_general_conversation_rebinding_are_rejected(flow, selected, tenant, normal):
    flow.run()
    if normal:
        flow.state.conversation['knowledge_source_id'] = None
        flow.state.conversation['resource_institution_id'] = None
    count = len(flow.state.messages)
    with pytest.raises(AppError) as failure:
        flow.run(selected=selected, tenant=tenant)
    assert failure.value.status_code == 409
    assert len(flow.state.messages) == count


def test_other_owners_conversation_is_hidden_before_resource_lookup(flow):
    flow.run()
    flow.state.conversation['user_id'] = OTHER
    flow.read.reset_mock()
    with pytest.raises(AppError) as failure:
        flow.run()
    assert failure.value.status_code == 404
    flow.read.assert_not_called()


def test_denied_first_context_is_not_created_and_denied_followup_is_blocked(flow):
    flow.read.side_effect = AppError('Unavailable', 404, 'RESOURCE_NOT_FOUND')
    with pytest.raises(AppError) as failure:
        flow.run()
    assert failure.value.status_code == 404
    assert flow.state.conversation is None and not flow.state.messages
    flow.read.side_effect = None
    flow.run()
    count = len(flow.state.messages)
    flow.read.side_effect = AppError('Unavailable', 404, 'RESOURCE_NOT_FOUND')
    with pytest.raises(AppError) as failure:
        flow.run(selected=None)
    assert failure.value.status_code == 409
    assert len(flow.state.messages) == count


def test_wrong_resource_retrieval_is_rejected_before_generation(flow):
    flow.state.policy['sources'] = {OTHER: 3}
    with pytest.raises(AppError) as failure:
        flow.run()
    assert failure.value.code == 'CONVERSATION_SCOPE_CHANGED'
    flow.provider.generate.assert_not_called()


def test_inflight_revocation_stops_delivery_and_casual_reply_keeps_source_proof(flow):
    flow.state.policy['sources'] = {}
    flow.current.side_effect = AppError('Access changed', 409, 'RESOURCE_CHANGED')
    with pytest.raises(AppError):
        flow.run('Hello')
    assert flow.current.call_args.args[2]['sources'] == {SOURCE: 3}
    assert flow.state.messages[-1].knowledge_policy['sources'] == {SOURCE: 3}
