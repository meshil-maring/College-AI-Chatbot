"""Authority declarations stay attached to the exact cited document version."""

from uuid import uuid4
import pytest

from app.schemas.ai.generation import AIContext, RetrievedChunk, SourceReference
from app.services.ai.generation_qualification import qualified_answer


def chunk(version, text):
    return RetrievedChunk(chunk_id=uuid4(), document_id=uuid4(), document_version_id=version,
                          text=text, similarity_score=0.8)


def reference(item):
    return SourceReference(chunk_id=item.chunk_id, quote=item.text)


@pytest.mark.parametrize("declaration", [
    "authority_status: draft_sample_not_official",
    "Status: Draft sample — not an officially approved college policy",
])
def test_section_answer_inherits_explicit_authority_with_a_separate_citation(declaration):
    version = uuid4()
    authority = chunk(version, declaration)
    body = chunk(version, "Visitors must register.")
    context = AIContext(system_instructions="Use evidence", user_question="Guest rules?",
                        retrieved_knowledge=[authority, body])
    answer, sources = qualified_answer("Visitors must register.", [reference(body)], context)
    assert answer.startswith("The cited material includes a draft/sample document")
    assert answer.endswith("\n\nVisitors must register.")
    assert [source.chunk_id for source in sources] == [body.chunk_id, authority.chunk_id]
    assert sources[-1].quote == authority.text
    assert qualified_answer(answer, sources, context) == (answer, sources)


def test_uncited_sources_and_old_versions_cannot_qualify_another_document():
    authority = chunk(uuid4(), "authority_status: draft_sample_not_official")
    body = chunk(uuid4(), "Verified current guest rules.")
    context = AIContext(system_instructions="Use evidence", user_question="Guest rules?",
                        retrieved_knowledge=[authority, body])
    original = "Current guest rules.", [reference(body)]
    assert qualified_answer(*original, context) == original


def test_ordinary_mentions_of_drafts_do_not_reclassify_official_content():
    body = chunk(uuid4(), "Staff submit drafts. Sample applications are available.")
    context = AIContext(system_instructions="Use evidence", user_question="Process?", retrieved_knowledge=[body])
    original = "Staff submit drafts.", [reference(body)]
    assert qualified_answer(*original, context) == original
