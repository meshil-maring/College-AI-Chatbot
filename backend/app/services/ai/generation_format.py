"""Decode provider-selected evidence without trusting model-written provenance."""

import json
import logging

from app.core.errors import AppError
from app.schemas.ai.generation import AIContext, SourceReference

logger = logging.getLogger(__name__)


CITATION_FORMAT = (
    'Return one JSON object with exactly three fields: "answer" (Markdown text '
    'or null), "sources" (an array of integer source numbers), and "status" '
    '("success" or "insufficient_context"). Source numbers are the 1-based '
    'numbers printed in the [Source N] labels of the supplied context. Select only '
    'chunks actually supporting the answer, including qualifications such as '
    'draft/sample status. If the supplied document is identified as a sample, '
    'draft, illustrative or unapproved policy, begin the answer with that '
    'qualification even when asked about just one section, and include its '
    'authority passage in sources. Do not select every chunk by default. Keep citations, '
    'source numbers, internal identifiers and retrieved-chunk labels out of '
    'the answer text; the application displays source cards separately. '
    'For insufficient evidence return null answer, empty sources and '
    'insufficient_context status. A successful factual answer requires at least '
    'one supporting source. Do not add fields, prose outside JSON or code fences.'
)


def citation_response_format(context: AIContext):
    """Constrain model selections to this request's exact authorized evidence."""
    return {"type": "json_schema", "json_schema": {
        "name": "grounded_answer", "strict": True,
        "schema": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "answer": {"type": ["string", "null"]},
                "sources": {"type": "array", "items": {
                    "type": "integer", "enum": list(range(1, len(context.retrieved_knowledge) + 1)),
                }},
                "status": {"type": "string", "enum": ["success", "insufficient_context"]},
            },
            "required": ["answer", "sources", "status"],
        },
    }}


def decode_answer(content: str, context: AIContext):
    """Resolve selected positions to exact authorized chunks and canonical quotes."""
    if not context.retrieved_knowledge:
        return content, [], "success"
    try:
        payload = json.loads(content)
        if not isinstance(payload, dict) or set(payload) != {"answer", "sources", "status"}:
            raise ValueError("Invalid answer envelope")
        answer, selected, status = payload["answer"], payload["sources"], payload["status"]
        if not isinstance(selected, list):
            raise ValueError("Invalid sources")
        if any(type(index) is not int or not 1 <= index <= len(context.retrieved_knowledge)
               for index in selected):
            raise ValueError("Unknown source")
        if status == "insufficient_context":
            if answer is not None or selected:
                raise ValueError("Inconsistent insufficient answer")
            return None, [], status
        if status != "success" or not isinstance(answer, str) or not answer.strip() or not selected:
            raise ValueError("Missing grounded answer")
        references = []
        for index in dict.fromkeys(selected):
            chunk = context.retrieved_knowledge[index - 1]
            references.append(SourceReference(
                chunk_id=chunk.chunk_id, document_id=chunk.document_id,
                document_version_id=chunk.document_version_id, quote=chunk.text,
                similarity_score=chunk.similarity_score,
            ))
        return answer, references, status
    except (ValueError, TypeError, KeyError) as failure:
        # Report schema failures without logging prompts, answers or identifiers.
        reason = str(failure) if type(failure) is ValueError else type(failure).__name__
        logger.warning("event=invalid_cited_answer reason=%s", reason)
        raise AppError("AI provider returned an invalid cited response", 502,
                       "AI_PROVIDER_RESPONSE_ERROR") from failure
