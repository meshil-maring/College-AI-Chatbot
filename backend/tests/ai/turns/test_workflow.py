"""Replay and uncertain completion do not start duplicate provider work."""

from unittest.mock import MagicMock

import pytest

from app.core.errors import AppError
from app.services.ai.turns import workflow
from .conftest import ACTOR, CONVERSATION, TOKEN, TURN, receipt


def run(turn_request, session, process):
    return workflow.run(turn_request, session, object(), ACTOR, current_user={'user_id': ACTOR}, process=process)


def test_completed_receipt_skips_generation(monkeypatch, turn_request, session, reply):
    execute = MagicMock(return_value=receipt('completed', reply))
    process = MagicMock()
    monkeypatch.setattr(workflow, 'execute', execute)
    assert run(turn_request, session, process) == reply
    process.assert_not_called()
    assert execute.call_count == 1


def test_an_existing_worker_is_reported_pending_without_generation(monkeypatch, turn_request, session):
    monkeypatch.setattr(workflow, 'execute', MagicMock(return_value=receipt('processing')))
    process = MagicMock()
    with pytest.raises(AppError) as failure:
        run(turn_request, session, process)
    assert failure.value.code == 'CHAT_TURN_PENDING'
    assert failure.value.headers['Retry-After'] == '2'
    process.assert_not_called()


def test_claim_passes_one_fenced_execution_to_the_engine(monkeypatch, turn_request, session, reply):
    execute = MagicMock(return_value=receipt('claimed'))
    monkeypatch.setattr(workflow, 'execute', execute)
    process = MagicMock(return_value=reply)
    assert run(turn_request, session, process) == reply
    process.assert_called_once()
    assert process.call_args.kwargs['turn']['worker_token'] == TOKEN
    assert str(process.call_args.args[0].conversation_id) == CONVERSATION
    assert execute.call_args.kwargs['selected_turn'] == TURN


def test_failed_provider_releases_only_its_own_lease(monkeypatch, turn_request, session):
    execute = MagicMock(side_effect=[receipt('claimed'), None])
    monkeypatch.setattr(workflow, 'execute', execute)
    process = MagicMock(side_effect=AppError('Provider timed out', 504, 'AI_PROVIDER_TIMEOUT'))
    with pytest.raises(AppError, match='Provider timed out'):
        run(turn_request, session, process)
    operation, = execute.call_args.args
    assert operation == 'fail_chat_turn'
    assert execute.call_args.kwargs['token'] == TOKEN


def test_unknown_commit_failure_does_not_trigger_another_generation(monkeypatch, turn_request, session):
    execute = MagicMock(side_effect=[receipt('claimed'), RuntimeError('Unconfirmed failure update')])
    monkeypatch.setattr(workflow, 'execute', execute)
    process = MagicMock(side_effect=ConnectionError('Completion transport lost'))
    with pytest.raises(ConnectionError, match='Completion transport lost'):
        run(turn_request, session, process)
    process.assert_called_once()


def test_legacy_requests_keep_their_existing_engine_contract(monkeypatch, turn_request, session, reply):
    turn_request.turn_id = None
    execute = MagicMock()
    monkeypatch.setattr(workflow, 'execute', execute)
    process = MagicMock(return_value=reply)
    assert run(turn_request, session, process) == reply
    execute.assert_not_called()
    assert 'turn' not in process.call_args.kwargs
