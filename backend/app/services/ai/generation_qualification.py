"""Preserve explicit document authority declarations in generated answers."""

import re

from app.schemas.ai.generation import SourceReference


_SAMPLE_AUTHORITY = re.compile(
    r"\bauthority_status\s*:\s*draft_sample_not_official\b|"
    r"\bstatus\s*:\s*draft sample\b.{0,80}\bnot an officially approved college policy\b",
    re.IGNORECASE | re.DOTALL,
)


def qualified_answer(answer, references, context):
    """Add a verified caveat only for cited versions explicitly marked as samples.

    These are document declarations, not instructions to the model. Ordinary
    mentions of drafts or samples do not classify a document's authority.
    Never carry a qualification across document versions or uncited sources.
    """
    if not answer or not references:
        return answer, references
    selected = {reference.chunk_id for reference in references}
    cited_versions = {chunk.document_version_id for chunk in context.retrieved_knowledge
                      if chunk.chunk_id in selected and chunk.document_version_id is not None}
    authorities = {}
    for chunk in context.retrieved_knowledge:
        if chunk.document_version_id in cited_versions and _SAMPLE_AUTHORITY.search(chunk.text):
            authorities.setdefault(chunk.document_version_id, chunk)
    if not authorities:
        return answer, references
    caveat = (
        "The cited material includes a draft/sample document, not an officially approved college policy. "
        "Its example rules and details are illustrative."
    )
    # A deterministic preface prevents an authoritative-looking section summary
    # even when the model omitted the document's explicit qualification.
    if not answer.startswith(caveat):
        answer = f"{caveat}\n\n{answer}"
    references = list(references)
    for chunk in authorities.values():
        if chunk.chunk_id not in selected:
            references.append(SourceReference(
                chunk_id=chunk.chunk_id, document_id=chunk.document_id,
                document_version_id=chunk.document_version_id, quote=chunk.text,
                similarity_score=chunk.similarity_score,
            ))
            selected.add(chunk.chunk_id)
    return answer, references
