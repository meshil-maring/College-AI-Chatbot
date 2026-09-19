"""Phase 6.13 - Public (unauthenticated) chat endpoint service.

Mirrors app.services.chat.process_chat_request so that public conversations
reuse the same chat boundary, turn/conversation ownership model, bounded
history, query rewriting, retrieval, generation, and citation pipeline -
EXCEPT:

1. user_id is always PUBLIC_USER_ID (a constant, never derived from a JWT).
2. Personalization is never loaded (no current_user -> no student context).
3. institution_id is accepted for forward-compatibility but does not
   participate in any tenant-scoped authorization check.
"""

from __future__ import annotations

import re
import threading
import time
from uuid import UUID

from app.config import settings
from app.core.errors import AppError
from app.core.security import PUBLIC_USER_ID
from app.db.supabase import get_admin_client
from app.repositories import tenancy as tenancy_repo
from app.repositories.ai_response import create_ai_response
from app.repositories.conversation import (
    create_conversation,
    get_conversation,
    update_conversation_timestamp,
)
from app.repositories.message import create_message, get_next_message_sequence
from app.repositories.message_citation import create_message_citations
from app.repositories.retrieval_operation import (
    create_retrieval_operation,
    create_retrieved_chunks,
)
from app.schemas.citation import (
    MessageCitationCreate,
    RetrievedChunkCreate,
    RetrievalOperationCreate,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.chat_response import ChatUsage, StructuredSource
from app.schemas.conversation import (
    AIResponseCreate,
    ConversationCreate,
    MessageCreate,
)
from app.schemas.generation import (
    AIRequest,
    ConversationTurn,
    RetrievalScope,
    RetrievedChunk,
    SourceReference,
)
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult
from app.schemas.session import SessionContext
from app.services.context import assemble_context
from app.services.conversation_history import get_conversation_messages
from app.services.generation import AIGenerationService
from app.services.generation_provider import GenerationProvider
from app.services.personalization import classify_personalization_question
from app.services.query_rewriting import rewrite_query
from app.services.retrieval import retrieve

# Public knowledge sources are the only ones a public (unauthenticated) chat
# may retrieve. Anything else - private documents, student records, attendance,
# exam results, personalized academic data - must be filtered out BEFORE
# generation, at the data-access boundary.
#
# source_type values are defined by the admin knowledge ingestion layer and
# enforced by the knowledge_sources.source_type CHECK constraint. Public chat
# only ever retrieves sources that are BOTH published AND public-type.
PUBLIC_SOURCE_TYPES = frozenset({"faq", "notice", "handbook"})

# ============================================================================
# Phase 6.13.8 — Public tenant resolution + public-only retrieval filtering
# ============================================================================

_UNTRUSTED_INSTS = "client-supplied institution_id may not override server-side tenant resolution"
_UNTRUSTED_ORGS = "client-supplied organization_id may not override server-side tenant resolution"
_PERSONAL_NO_AUTH = "personalized academic data requires authentication"


def _validate_public_institution(
    client: Any, institution_id: UUID | str | None
) -> UUID:
    """Validate that a public request's institution is legit and active.

    Reused from Phase 6.13.1/6.13.6/6.13.7 primitives (with the same
    lifecycle semantics):

    * institution must exist
    * institution must be ACTIVE (pending/rejected/suspended -> denied)
    * institution must belong to a valid/active organization
    * inactive/pending/rejected institution must NOT expose public knowledge

    Raises an AppError (403/404) when the institution is invalid; returns the
    UUID when it is safe to proceed.  ``None`` is only accepted when the
    project is running without any institutions yet (development); in that
    case public knowledge is simply empty.
    """
    if institution_id is None:
        return None

    raw = institution_id if isinstance(institution_id, str) else str(institution_id)
    inst = tenancy_repo.get_institution_by_id(client, raw)
    if inst is None:
        raise AppError(
            "Institution not found",
            status_code=404,
            code="INSTITUTION_NOT_FOUND",
        )

    status = inst.get("status") or "unknown"
    if status != "active":
        _inactive_msg = {
            "pending": "Institution is pending approval",
            "rejected": "Institution has been rejected",
            "suspended": "Institution has been suspended",
        }.get(status, f"Institution status is {status!r}")
        raise AppError(
            _inactive_msg,
            status_code=403,
            code="INSTITUTION_NOT_ACTIVE",
        )

    org_id = inst.get("organization_id")
    if org_id is None:
        raise AppError(
            "Institution has no organization",
            status_code=500,
            code="INSTITUTION_NO_ORGANIZATION",
        )

    org = tenancy_repo.get_organization_by_id(client, org_id)
    if org is None:
        raise AppError(
            "Institution organization not found",
            status_code=404,
            code="ORGANIZATION_NOT_FOUND",
        )

    org_status = org.get("status") or "unknown"
    if org_status not in ("active", "pending"):
        raise AppError(
            "Institution organization is not active",
            status_code=403,
            code="ORGANIZATION_NOT_ACTIVE",
        )

    return UUID(str(inst["institution_id"]))


def _reject_personal_query_if_needed(request: ChatRequest) -> None:
    """Block personal-data questions from unauthenticated (public) callers.

    The public path carries no authenticated user, so it can never load a
    student context. A question that needs the student's own attendance,
    results, performance, courses, or profile must go through the protected
    (authenticated) chat endpoint instead, where the user's JWT-derived
    identity is used as the canonical data selector.

    Keyword concern: we deliberately do NOT rely on simple keywords such as
    ``"my"`` to decide whether a question is protected. We reuse the existing
    deterministic Phase 6.10 classifier, which already encodes the project's
    policy that rule/policy questions ("What attendance do I need...") stay
    general while true personal-data questions ("What is my attendance?") are
    protected.
    """
    intent = classify_personalization_question(request.user_query)
    if intent is None:
        return
    raise AppError(
        "Personalized academic data requires authentication",
        status_code=401,
        code="AUTH_REQUIRED",
    )


def _resolve_chunk_knowledge_sources(
    client: Any, processing_run_ids: set[str]
) -> dict[str, str | None]:
    """Resolve chunk -> knowledge_source_id via the processing run provenance.

    Chain: chunk.processing_run_id -> document_processing_runs
          -> document_versions.knowledge_source_id -> documents.knowledge_source_id

    Returns ``{processing_run_id: knowledge_source_id}``.  Runs whose
    projection has no knowledge_source_id yield ``None``; they are treated as
    non-public and filtered out.
    """
    if not processing_run_ids:
        return {}

    response = (
        client.table("document_processing_runs")
        .select("processing_run_id, document_versions(knowledge_source_id)")
        .in_("processing_run_id", sorted(processing_run_ids))
        .execute()
    )
    data: list | None = response.data if response and isinstance(response.data, list) else None
    if not data:
        return {}

    out: dict[str, str | None] = {}
    for row in data:
        pid = row.get("processing_run_id")
        if not pid:
            continue
        dvs = row.get("document_versions")
        ks_id: str | None = None
        if isinstance(dvs, list):
            for dv in dvs:
                ks_id = dv.get("knowledge_source_id") if isinstance(dv, dict) else None
                if ks_id:
                    break
        elif isinstance(dvs, dict):
            ks_id = dvs.get("knowledge_source_id")
        out[str(pid)] = str(ks_id) if ks_id else None
    return out


def _knowledge_source_is_public(
    client: Any,
    knowledge_source_id: str,
    institution_id: UUID,
) -> bool:
    """True when a knowledge source is public AND belongs to the resolved institution.

    Public knowledge sources are the *types* that the admin layer is configured
    to expose (faq, notice, handbook in this project).  We additionally verify
    the source actually belongs to the resolved institution so a public request
    from Institution A can never read Institution B's public documents.
    """
    row = tenancy_repo.get_knowledge_source_by_id(client, knowledge_source_id)
    if not row:
        return False
    if row.get("institution_id") != str(institution_id):
        return False
    if row.get("source_type") not in PUBLIC_SOURCE_TYPES:
        return False
    return True


def _build_allowed_public_knowledge_source_ids(
    client: Any,
    institution_id: UUID,
    requested_knowledge_source_id: str | None,
) -> set[str]:
    """Return the set of knowledge source IDs a public request may read.

    * If a ``requested_knowledge_source_id`` was supplied, validate it is a
      public source belonging to the resolved institution and return a
      single-element set when valid.  Invalid/tampered values raise or produce
      an empty set depending on whether the caller explicitly asked for a
      source.
    * Otherwise, enumerate all public sources for the institution.
    """
    if requested_knowledge_source_id:
        ks_id = str(requested_knowledge_source_id)
        if not _knowledge_source_is_public(client, ks_id, institution_id):
            if tenancy_repo.get_knowledge_source_by_id(client, ks_id) is not None:
                raise AppError(
                    "Requested knowledge source is not public for this institution",
                    status_code=403,
                    code="KNOWLEDGE_SOURCE_NOT_PUBLIC",
                )
            raise AppError(
                "Requested knowledge source not found",
                status_code=404,
                code="KNOWLEDGE_SOURCE_NOT_FOUND",
            )
        return {ks_id}

    rows = tenancy_repo.list_published_knowledge_sources_for_institution(
        client, institution_id
    )
    return {
        str(row["knowledge_source_id"])
        for row in rows
        if row.get("knowledge_source_id") and row.get("source_type") in PUBLIC_SOURCE_TYPES
    }


def _filter_to_public_chunks(
    retrieved_chunks: list[Any],
    run_to_ks: dict[str, str | None],
    allowed_ks: set[str],
) -> list[Any]:
    """Filter retrieved chunks to only those backed by public knowledge sources.

    Defense-in-depth: even if the vector/BM25 retrieval returned a chunk, drop it
    when its provenance knowledge source is not in the public-only allow-list for
    the resolved institution.

    Chain: chunk.metadata.processing_run_id -> run_to_ks -> knowledge_source_id
           -> membership in allowed_ks.
    """
    out: list[Any] = []
    for chunk in retrieved_chunks:
        pid = None
        if hasattr(chunk, "metadata") and chunk.metadata:
            pid = chunk.metadata.get("processing_run_id")
        if not pid:
            continue
        ks_id = run_to_ks.get(str(pid))
        if ks_id and ks_id in allowed_ks:
            out.append(chunk)
    return out

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

# ============================================================================
# Background persistence (mirrors chat.py)
# ============================================================================

_background_errors: list[str] = []
_BACKGROUND_ERROR_LIMIT = 20


def _persist_in_background(
    conversation_id: UUID,
    message_id: UUID,
    retrieval_query: str,
    retrieved_chunks: list[RetrievedChunk],
    source_references: list[SourceReference],
    generation_result,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int,
) -> None:
    """Persist AI response, retrieval operation, chunks, and citations in a
    background thread. The worker resolves its own admin client inside the
    thread instead of reusing the request thread's client."""
    try:
        client = get_admin_client()
        ai_response = create_ai_response(
            client,
            AIResponseCreate(
                message_id=message_id,
                provider_name="openrouter",
                model_name=generation_result.model_used or "unknown",
                validation_status="pending",
                input_token_count=input_tokens,
                output_token_count=output_tokens,
                latency_ms=latency_ms,
            ),
        )
        ai_response_id = UUID(ai_response["ai_response_id"])

        update_conversation_timestamp(client, conversation_id)

        retrieval_op = create_retrieval_operation(
            client,
            RetrievalOperationCreate(
                ai_response_id=ai_response_id,
                query_text=retrieval_query,
                status="completed",
                result_count=len(retrieved_chunks),
            ),
        )
        retrieval_op_id = UUID(retrieval_op["retrieval_operation_id"])

        create_retrieved_chunks(
            client,
            [
                RetrievedChunkCreate(
                    retrieval_operation_id=retrieval_op_id,
                    chunk_id=chunk.chunk_id,
                    retrieval_rank=rank,
                    relevance_score=chunk.similarity_score,
                    selected_for_context=True,
                )
                for rank, chunk in enumerate(retrieved_chunks, start=1)
            ],
        )

        create_message_citations(
            client,
            [
                MessageCitationCreate(
                    message_id=message_id,
                    retrieval_operation_id=retrieval_op_id,
                    chunk_id=ref.chunk_id,
                    display_order=order,
                )
                for order, ref in enumerate(source_references, start=1)
            ],
        )
    except Exception as exc:
        import logging

        logging.error("Background persistence failed: %s", exc, exc_info=True)
        _background_errors.append(f"{type(exc).__name__}: {exc}")
        while len(_background_errors) > _BACKGROUND_ERROR_LIMIT:
            _background_errors.pop(0)


def _start_background_persistence(
    conversation_id: UUID,
    message_id: UUID,
    retrieval_query: str,
    retrieved_chunks: list[RetrievedChunk],
    source_references: list[SourceReference],
    generation_result,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int,
) -> None:
    """Kick off persistence on a daemon thread so the response is not blocked."""
    thread = threading.Thread(
        target=_persist_in_background,
        args=(
            conversation_id,
            message_id,
            retrieval_query,
            retrieved_chunks,
            source_references,
            generation_result,
            input_tokens,
            output_tokens,
            latency_ms,
        ),
        daemon=True,
    )
    thread.start()

# ============================================================================
# Main entry point
# ============================================================================


def process_chat_request(
    request: ChatRequest,
    context: SessionContext,
    provider: GenerationProvider,
) -> ChatResponse:
    """Public-path equivalent of app.services.chat.process_chat_request.

    Ownership model is identical to the authenticated path - same
    ConversationCreate shape, same background persistence, same bounded
    turn history - but every public conversation is owned by PUBLIC_USER_ID
    so the public endpoint cannot read or write into any authenticated
    user's conversation or message rows.
    """
    if not isinstance(request, ChatRequest):
        raise TypeError("request must be a ChatRequest")
    if not isinstance(context, SessionContext):
        raise TypeError("context must be a SessionContext")

    timings: dict = {}
    request_start = time.perf_counter()
    client = get_admin_client()

    # Step 1: Resolve or create conversation (owned by PUBLIC_USER_ID)
    conversation_start = time.perf_counter()
    user_id = PUBLIC_USER_ID
    conversation_id = (
        request.conversation_id
        or request.session_id
        or context.session_id
    )
    conversation = get_conversation(client, conversation_id)

    if conversation is None:
        title = (
            request.user_query[:60]
            if len(request.user_query) > 60
            else request.user_query
        )
        conversation = create_conversation(
            client,
            ConversationCreate(
                user_id=user_id,
                title=title,
                status="active",
            ),
            conversation_id=conversation_id,
        )
        conversation_id = UUID(conversation["conversation_id"])
    else:
        conversation_id = UUID(conversation["conversation_id"])
    timings["conversation_resolution_ms"] = int(
        (time.perf_counter() - conversation_start) * 1000
    )

    # Step 1.5: Bounded conversation history (copy of chat.py logic)
    history_start = time.perf_counter()
    message_summaries = get_conversation_messages(
        conversation_id,
        user_id,
        conversation=conversation,
    )
    timings["history_latency_ms"] = int(
        (time.perf_counter() - history_start) * 1000
    )
    turns = [
        ConversationTurn(role=s.role, content=s.content)
        for s in message_summaries
    ]
    conversation_history = turns[-20:] if len(turns) > 20 else turns

    # Step 2: Persist user message
    user_sequence = get_next_message_sequence(client, conversation_id)
    create_message(
        client,
        MessageCreate(
            conversation_id=conversation_id,
            message_sequence=user_sequence,
            message_type="user",
            content_text=request.user_query,
        ),
    )

    # Step 2.5: Query rewriting - only rewrite if not self-contained
    rewrite_start = time.perf_counter()
    _self_contained = (
        len(request.user_query) >= 12
        and not re.search(
            r"\b(this|that|these|those|it|he|she|they|we|him|her|them|"
            r"his|its|their|our|you|your)\b",
            request.user_query,
            re.IGNORECASE,
        )
        or conversation_history
    )
    if _self_contained:
        retrieval_query = request.user_query
    else:
        rewritten = rewrite_query(
            request.user_query, conversation_history, provider
        ) or request.user_query
        retrieval_query = rewritten
    timings["query_rewrite_latency_ms"] = int(
        (time.perf_counter() - rewrite_start) * 1000
    )

    # --- Phase 6.13.8: Public AI access controls (before retrieval) ---

    # 1. Personal-data questions from the public path are rejected. The
    #    public path has no authenticated user, so it can never load a
    #    student context. Personal questions are routed to the protected
    #    (authenticated) endpoint instead.
    _reject_personal_query_if_needed(request)

    # 2. Institution is validated server-side: it must exist, be ACTIVE, and
    #    belong to a valid/active organization.  A client-supplied
    #    institution_id is never trusted blindly.
    _validated_institution_id = _validate_public_institution(
        client, institution_id=request.institution_id
    )

    # 3. Client-supplied scope overrides are rejected. Even if a client sends
    #    explicit knowledge_source_id / institution_id / organization_id, the
    #    public path must derive its scope from the validated institution, not
    #    from whatever the caller put in the request.
    if request.knowledge_source_id is not None:
        # A client may ask for a specific knowledge source; we validate it
        # belongs to the resolved institution AND is a public source.
        _allowed_ks = _build_allowed_public_knowledge_source_ids(
            client, _validated_institution_id, str(request.knowledge_source_id)
        )
        if not _allowed_ks:
            raise AppError(
                "Requested knowledge source is not accessible from this institution",
                status_code=403,
                code="KNOWLEDGE_SOURCE_NOT_PUBLIC",
            )
    else:
        _allowed_ks = _build_allowed_public_knowledge_source_ids(
            client, _validated_institution_id, None
        )

    # --- Phase 6.13.8: Retrieval scoped to the validated institution ---

    # Step 3: Retrieval (skip if chunks already provided)
    retrieved_chunks: list[RetrievedChunk] = list(request.retrieved_chunks)
    if not retrieved_chunks:
        retrieval_timings: dict = {}
        retrieval_request = RetrievalRequest(
            query=retrieval_query,
            top_k=settings.retrieval_top_k,
            institution_id=str(_validated_institution_id)
            if _validated_institution_id is not None
            else None,
            knowledge_source_id=(
                str(sorted(_allowed_ks)[0]) if len(_allowed_ks) == 1 else None
            ),
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            processing_run_id=request.processing_run_id,
            model_name=request.model_name,
        )
        retrieval_response = retrieve(
            retrieval_request, timings=retrieval_timings
        )
        timings["embedding_latency_ms"] = retrieval_timings.get(
            "embedding_latency_ms", 0
        )
        timings["retrieval_latency_ms"] = retrieval_timings.get(
            "vector_search_latency_ms", 0
        )
        retrieved_chunks = [
            RetrievedChunk(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_version_id=r.document_version_id,
                text=r.text,
                similarity_score=r.similarity_score,
                metadata=r.metadata,
            )
            for r in retrieval_response.results
        ]
    else:
        timings["embedding_latency_ms"] = 0
        timings["retrieval_latency_ms"] = 0

    # --- Phase 6.13.8: Public-only chunk filtering (data-access boundary) ---

    # Even though the retrieval above is already institution-scoped at the
    # vector-search level, we ALSO hard-filter the returned chunks by
    # knowledge-source provenance + public source_type.  This is defense in
    # depth: a misconfigured HBASE/pgvector payload, a future schema change,
    # or a client-supplied ``retrieved_chunks`` list can never slip a
    # private/student/institution-B chunk into the LLM context.
    if retrieved_chunks:
        _run_ids = {
            str(c.metadata.get("processing_run_id"))
            for c in retrieved_chunks
            if c.metadata and c.metadata.get("processing_run_id")
        }
        _run_to_ks = _resolve_chunk_knowledge_sources(client, _run_ids)
        _public_chunks = _filter_to_public_chunks(
            retrieved_chunks, _run_to_ks, _allowed_ks
        )
        if not _public_chunks:
            # No authorized public knowledge matched.  We keep the empty list
            # rather than the raw retrieval so the LLM only sees authorized
            # context.
            retrieved_chunks = []
        else:
            retrieved_chunks = _public_chunks

    # Step 4: Build AIRequest, assemble context, generate
    #
    # The retrieval_scope passed to context assembly uses the VALIDATED
    # institution id (not the client-supplied one) so that any provenance
    # metadata the LLM prompt renders is anchored to the server-selected
    # tenant.
    _scope_institution_id = (
        str(_validated_institution_id) if _validated_institution_id is not None else None
    )
    _scope_knowledge_source_id = (
        str(sorted(_allowed_ks)[0]) if len(_allowed_ks) == 1 else None
    )
    context_start = time.perf_counter()
    ai_request = AIRequest(
        user_query=request.user_query,
        retrieval_query=(
            retrieval_query
            if retrieval_query != request.user_query
            else None
        ),
        retrieval_scope=RetrievalScope(
            institution_id=_scope_institution_id,
            knowledge_source_id=_scope_knowledge_source_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            processing_run_id=request.processing_run_id,
        ),
        retrieved_chunks=retrieved_chunks,
        model_name=request.model_name,
        conversation_history=conversation_history,
    )
    assembled_context = assemble_context(ai_request)
    timings["context_build_latency_ms"] = int(
        (time.perf_counter() - context_start) * 1000
    )

    stage_start = time.perf_counter()
    generation_result = AIGenerationService(provider).generate(
        assembled_context
    )
    latency_ms = int((time.perf_counter() - stage_start) * 1000)
    timings["llm_request_latency_ms"] = latency_ms
    timings["llm_ttft_ms"] = latency_ms
    timings["llm_generation_latency_ms"] = latency_ms

    # Step 4.5: Extract source references from answer
    parse_start = time.perf_counter()
    source_references = _extract_source_references(
        generation_result.answer, retrieved_chunks
    )
    timings["response_parse_latency_ms"] = int(
        (time.perf_counter() - parse_start) * 1000
    )

    # Step 5: Persist assistant message + AI response
    persist_start = time.perf_counter()
    message_id: UUID | None = None
    if generation_result.answer is not None:
        assistant_sequence = get_next_message_sequence(
            client, conversation_id
        )
        assistant_message = create_message(
            client,
            MessageCreate(
                conversation_id=conversation_id,
                message_sequence=assistant_sequence,
                message_type="assistant",
                content_text=generation_result.answer,
            ),
        )
        message_id = UUID(assistant_message["message_id"])

        input_tokens: int | None = None
        output_tokens: int | None = None
        if isinstance(generation_result.metadata, dict) and isinstance(
            generation_result.metadata.get("usage"), dict
        ):
            usage = generation_result.metadata["usage"]
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")

        _start_background_persistence(
            conversation_id=conversation_id,
            message_id=message_id,
            retrieval_query=retrieval_query,
            retrieved_chunks=retrieved_chunks,
            source_references=source_references,
            generation_result=generation_result,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    timings["persistence_latency_ms"] = int(
        (time.perf_counter() - persist_start) * 1000
    )

    # Step 6: Build structured sources and usage
    sources = _build_structured_sources(
        source_references, retrieved_chunks
    )
    chat_usage = _build_chat_usage(generation_result.metadata)

    timings["total_latency_ms"] = int(
        (time.perf_counter() - request_start) * 1000
    )

    # Step 7: Return ChatResponse
    return ChatResponse(
        session_id=context.session_id,
        conversation_id=conversation_id,
        message_id=message_id,
        answer=generation_result.answer,
        source_references=source_references,
        status=generation_result.status,
        model_used=generation_result.model_used,
        metadata=(
            {**generation_result.metadata, "diagnostics": timings}
            if settings.debug
            else generation_result.metadata
        ),
        sources=sources,
        usage=chat_usage,
    )
