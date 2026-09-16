"""Append helper functions to public_chat.py."""

import os
os.chdir('F:\\Git Project\\CollegeAIChatbot\\backend')

helpers = '''
# ============================================================================
# Source reference extraction (mirrors chat.py)
# ============================================================================

_CHUNK_REF_RE = re.compile(
    r"\[Retrieved chunk ([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\]",
    re.IGNORECASE,
)


def _extract_source_references(
    answer: str | None,
    retrieved_chunks: list[RetrievedChunk],
) -> list[SourceReference]:
    """Extract source references from answer text using explicit chunk refs."""
    if not answer or not retrieved_chunks:
        return []
    referenced_ids = {
        UUID(m.group(1)) for m in _CHUNK_REF_RE.finditer(answer)
    }
    references = []
    for chunk in retrieved_chunks:
        if chunk.chunk_id in referenced_ids:
            references.append(
                SourceReference(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_version_id=chunk.document_version_id,
                    quote=chunk.text,
                    similarity_score=chunk.similarity_score,
                )
            )
    return references


# ============================================================================
# Structured sources / usage (mirrors chat.py)
# ============================================================================

def _build_structured_sources(
    source_references: list[SourceReference],
    retrieved_chunks: list[RetrievedChunk],
) -> list[StructuredSource]:
    """Build frontend-friendly StructuredSource list from source references."""
    chunks_by_id = {c.chunk_id: c for c in retrieved_chunks}
    sources: list[StructuredSource] = []
    for ref in source_references:
        chunk = chunks_by_id.get(ref.chunk_id)
        sources.append(
            StructuredSource(
                chunk_id=ref.chunk_id,
                quote=ref.quote,
                relevance_score=ref.similarity_score,
                section=(
                    chunk.metadata.get("section")
                    if chunk and chunk.metadata
                    else None
                ),
            )
        )
    return sources


def _build_chat_usage(metadata: dict | None) -> ChatUsage | None:
    """Map generation metadata["usage"] into a ChatUsage."""
    if not isinstance(metadata, dict):
        return None
    usage = metadata.get("usage")
    if not isinstance(usage, dict):
        return None
    return ChatUsage(
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
    )
'''

with open('app/services/public_chat.py', 'a') as f:
    f.write('\n' + helpers.lstrip('\n'))

print('Helper functions appended')
