"""Real provider protocol: separate prose and selected evidence."""

import json
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest

from app.core.errors import AppError
from app.schemas.ai.generation import AIContext, RetrievedChunk
from app.schemas.ai.chat_response import StructuredSource
from app.services.ai.generation import AIGenerationService
from app.services.ai.generation_format import decode_answer
from app.services.ai.generation_provider import OpenRouterGenerationProvider
from app.services.ai.public_chat import _extract_source_references, _sanitize_public_answer


def context(public=False):
    return AIContext(
        system_instructions="Use supplied evidence.", user_question="What are the hostel rules?",
        public=public, institution_id=uuid4(), max_output_tokens=321, retrieved_knowledge=[
            RetrievedChunk(chunk_id=uuid4(), document_id=uuid4(), document_version_id=uuid4(),
                           text=text, similarity_score=0.8)
            for text in ["Draft sample only.", "Residents must apply.", "Unused context."]
        ],
    )


def test_public_provider_selections_survive_projection_without_internal_labels():
    supplied = context(public=True)
    answer = "This is a draft sample.\n\n- Residents must apply."
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        assert request.extensions["timeout"]["read"] == 17.0
        content = json.dumps({"answer": answer, "sources": [2, 1, 2], "status": "success"})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with patch.multiple("app.services.ai.generation_provider.settings",
                            openrouter_api_key="test-key", openrouter_model="server/model"):
            result = AIGenerationService(OpenRouterGenerationProvider(client, timeout=17.0)).generate(supplied)
    assert requests[0]["response_format"]["type"] == "json_schema"
    schema = requests[0]["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["properties"]["sources"]["items"]["enum"] == [1, 2, 3]
    assert "[Source 1]" in requests[0]["messages"][1]["content"]
    assert requests[0]["model"] == "server/model"
    assert requests[0]["max_tokens"] == 321
    assert "source numbers" in requests[0]["messages"][0]["content"]
    references = _extract_source_references(result.answer, supplied.retrieved_knowledge)
    assert {ref.chunk_id for ref in references} == {chunk.chunk_id for chunk in supplied.retrieved_knowledge[:2]}
    assert _sanitize_public_answer(result.answer) == answer
    assert len(result.source_references) == 2


@pytest.mark.parametrize("payload", [
    {"answer": "Claim", "sources": [], "status": "success"},
    {"answer": "Claim", "sources": [0], "status": "success"},
    {"answer": "Claim", "sources": [4], "status": "success"},
    {"answer": "Claim", "sources": [True], "status": "success"},
    {"answer": "Claim", "sources": [1.0], "status": "success"},
    {"answer": "Claim", "sources": ["1"], "status": "success"},
    {"answer": "Claim", "sources": [1], "status": "insufficient_context"},
    {"answer": None, "sources": [1], "status": "insufficient_context"},
    {"answer": "Claim", "sources": [1], "status": "success", "quote": "Invented"},
    {"answer": " ", "sources": [1], "status": "success"},
    [], None,
])
def test_invalid_provenance_envelopes_fail_safely(payload):
    with pytest.raises(AppError) as failure:
        decode_answer(json.dumps(payload), context())
    assert failure.value.code == "AI_PROVIDER_RESPONSE_ERROR"


def test_truncated_json_fails_without_fabricated_sources():
    with pytest.raises(AppError):
        decode_answer('{"answer": "unfinished', context())


def test_insufficient_evidence_and_nonretrieval_requests_remain_distinct():
    assert decode_answer(json.dumps({"answer": None, "sources": [], "status": "insufficient_context"}),
                         context()) == (None, [], "insufficient_context")
    supplied = context().model_copy(update={"retrieved_knowledge": []})
    assert decode_answer("Rewritten question?", supplied) == ("Rewritten question?", [], "success")


def test_signed_in_answer_and_quotes_use_selected_canonical_chunks():
    supplied = context()
    answer, sources, status = decode_answer(
        json.dumps({"answer": "Sample rules.\n\n- Apply first.", "sources": [2, 1], "status": "success"}), supplied,
    )
    assert status == "success"
    assert answer == "Sample rules.\n\n- Apply first."
    assert [source.quote for source in sources] == [chunk.text for chunk in reversed(supplied.retrieved_knowledge[:2])]
    assert all(source.document_version_id == chunk.document_version_id
               for source, chunk in zip(sources, reversed(supplied.retrieved_knowledge[:2])))


def test_pdf_whitespace_matches_fresh_and_restored_source_cards():
    supplied = context()
    raw = "Draft sample.\n\nResidents\t must apply."
    supplied.retrieved_knowledge[0] = supplied.retrieved_knowledge[0].model_copy(update={"text": raw})
    _, sources, _ = decode_answer(json.dumps({"answer": "Apply.", "sources": [1], "status": "success"}), supplied)
    restored = StructuredSource(chunk_id=sources[0].chunk_id, quote=raw)
    assert restored.quote == sources[0].quote == "Draft sample. Residents must apply."
