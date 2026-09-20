"""Phase 6.14.5 — Personalized retrieval boundary.

Single server-side service that combines, for one AUTHENTICATED student:

    current_user (get_current_user: JWT user_id + server-resolved tenant)
         |
         +-- tenant/institution resolution (server-side, Phase 6.13.7 guard)
         |       |
         |       +-- institution-scoped RAG retrieval (existing Phase 3
         |       |   retrieval service, SAME vector-search implementation)
         |       |       -> authorized knowledge chunks
         |       |          (Phase 6.13.8 visibility boundary: published
         |       |          sources of the student's own institution only;
         |       |          private/cross-tenant sources are dropped)
         |
         +-- academic context (existing Phase 6.14.4 resolver:
             |   attendance + published results + identity labels)
             |
        PersonalizedContext  (knowledge and academic kept EXPLICITLY
                              separated — never flattened into one list)

Security model (nothing weakened, nothing duplicated):

* Identity is derived EXCLUSIVELY from ``current_user``. The function accepts
  NO identity parameters — there is no ``student_id`` / ``user_id`` /
  ``institution_id`` / ``organization_id`` / ``scope_id`` argument — so a
  client-supplied identifier can never select another student's data or
  another institution's knowledge.
* Institutional retrieval stays limited to the student's authorized
  institution: the scope is resolved server-side from the JWT-derived tenant,
  never from the query or any client field. The underlying vector search is
  the EXISTING Phase 3 service (``app.services.retrieval.retrieve``); no
  second vector-search implementation is created and the Phase 6.13.7 scope
  guards are not weakened.
* Knowledge visibility reuses the Phase 6.13.8 boundary: only chunks whose
  provenance knowledge source is a PUBLISHED source of the student's own
  institution enter the context. Private / draft / archived sources and every
  other tenant's documents are dropped (defense in depth: even a mis-scoped
  vector row can never leak).
* Academic data comes ONLY from
  ``app.services.student_academic_context.get_student_academic_context`` (the
  Phase 6.14.4 authorization boundary). Attendance tables, results tables,
  and student tables are never queried directly from this module.
* The two sources stay separated in the contract:
  ``PersonalizedContext.knowledge`` (institutional RAG chunks) vs
  ``PersonalizedContext.academic`` (private student academic data). The
  system can always distinguish institutional knowledge from private student
  data — required by the later prompt-construction and security phases.
* Authorization is INDEPENDENT of natural-language wording. The query is
  passed to retrieval verbatim; no keyword heuristic ("my", "attendance", ...)
  ever decides what may be exposed. Both sources are always resolved for the
  authenticated student; how the later generation phase combines them is a
  prompt-construction concern, not a security decision made here.
* Empty data is NOT an authorization failure: no RAG chunks, no attendance,
  and/or no results all yield a valid context with empty collections
  (mirroring the Phase 6.14.4 empty-data rule).
* Limits are respected, never invented: institutional retrieval uses the
  existing ``settings.retrieval_top_k`` budget via the existing service
  default; academic context is bounded by the existing Phase 6.14.4 defaults
  (attendance 200 / test results 100) via the existing resolver defaults.
  No context compression/summarization here (Phase 6.14.6).

This phase does NOT touch the generation pipeline, ``AIContext`` assembly,
prompts, model selection, token billing, OpenRouter configuration, retrieval,
vector search, attendance, results, authentication, tenancy, or RLS code.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.config import settings
from app.core.errors import AppError
from app.schemas.generation import RetrievedChunk
from app.schemas.personalized_context import (
    InstitutionalKnowledge,
    PersonalizedContext,
)
from app.schemas.retrieval import RetrievalRequest
from app.services import student_academic_context as academic_context_service

# Institutional knowledge visibility (Phase 6.13.8 boundary, reused verbatim):
# only these knowledge-source types are part of the institution's published
# knowledge corpus that an authenticated user may retrieve. Anything else —
# private documents, student records, attendance, results — is dropped at the
# data-access boundary BEFORE any chunk can enter the personalized context.
#
# source_type values are defined by the admin knowledge ingestion layer and
# enforced by the knowledge_sources.source_type CHECK constraint. The set is
# imported from the locked Phase 6.13.8 module so both boundaries can never
# drift apart.
from app.services.public_chat import PUBLIC_SOURCE_TYPES

from app.repositories import tenancy as tenancy_repo
from app.services.retrieval import retrieve

# ============================================================================
# Tenant resolution + lifecycle guard (Phase 6.13.7, reused — not weakened)
# ============================================================================


def _resolve_authorized_institution_id(
    current_user: dict[str, Any],
    client: Any | None,
) -> UUID | None:
    """Resolve the institution whose knowledge this user may retrieve.

    Server-side only: the tenant comes from the authenticated user's resolved
    context (JWT -> users row -> students.institution_id), never from a
    client-supplied field. A tenant-bound user may only ever retrieve their
    OWN institution's knowledge.

    The Phase 6.13.7 tenant lifecycle semantics are applied on top: a
    pending / rejected / suspended (non-active) institution fails closed —
    its knowledge is never retrievable (403 TENANT_INACTIVE, the same code
    the existing ``assert_tenant_context_active`` guard raises).
    """
    tenant = current_user.get("institution_id") if current_user else None
    if tenant is None:
        # Personalized retrieval is defined for authenticated STUDENTS, i.e.
        # tenant-bound accounts. A platform-level account (no tenant) has no
        # student tenant to resolve — fail closed.
        raise AppError(
            "No institution is bound to this account",
            status_code=403,
            code="NO_TENANT_BOUND",
        )

    db = client
    institution = tenancy_repo.get_institution_by_id(db, tenant)
    if (
        institution is None
        or institution.get("status") != "active"
        or not institution.get("is_active", False)
    ):
        # Same fail-closed semantics as assert_tenant_context_active
        # (Phase 6.13.7): pending/rejected/suspended institutions expose no
        # knowledge and no personalization context.
        raise AppError(
            "This institution is not active",
            status_code=403,
            code="TENANT_INACTIVE",
        )
    return tenant if isinstance(tenant, UUID) else UUID(str(tenant))


# ============================================================================
# Institutional RAG retrieval (existing Phase 3 service + Phase 6.13.8 filter)
# ============================================================================


def _resolve_chunk_knowledge_sources(
    client: Any, processing_run_ids: set[str]
) -> dict[str, str | None]:
    """Resolve chunk -> knowledge_source_id via the processing run provenance.

    Chain: chunk.processing_run_id -> document_processing_runs
          -> document_versions.knowledge_source_id -> documents.knowledge_source_id

    Returns ``{processing_run_id: knowledge_source_id}``.  Runs whose
    projection has no knowledge_source_id yield ``None``; they are treated as
    unauthorized and filtered out.  (Same provenance resolution as the locked
    Phase 6.13.8 public boundary.)
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


def _knowledge_source_is_authorized(
    client: Any,
    knowledge_source_id: str,
    institution_id: UUID,
) -> bool:
    """True when a knowledge source is published AND belongs to the institution.

    The student's authorized corpus is the published knowledge of their OWN
    institution. A source of another institution — or an unpublished
    (draft/under_review/archived/superseded) source — is never authorized.
    """
    row = tenancy_repo.get_knowledge_source_by_id(client, knowledge_source_id)
    if not row:
        return False
    if row.get("institution_id") != str(institution_id):
        return False
    if row.get("lifecycle_status") != "published":
        return False
    return True


def _build_authorized_knowledge_source_ids(
    client: Any,
    institution_id: UUID,
) -> set[str]:
    """Return the knowledge source IDs this institution's users may read.

    Published sources of the resolved institution, restricted to the
    authorized source-type whitelist (reused from the Phase 6.13.8 public
    boundary — private/student/attendance/result source types are excluded).
    """
    rows = tenancy_repo.list_published_knowledge_sources_for_institution(
        client, institution_id
    )
    return {
        str(row["knowledge_source_id"])
        for row in rows
        if row.get("knowledge_source_id")
        and row.get("source_type") in PUBLIC_SOURCE_TYPES
    }


def _filter_to_authorized_chunks(
    retrieved_chunks: list[Any],
    run_to_ks: dict[str, str | None],
    allowed_ks: set[str],
) -> list[Any]:
    """Filter retrieved chunks to only those backed by authorized sources.

    Defense in depth: even if the vector retrieval returned a chunk, drop it
    when its provenance knowledge source is not in the authorized allow-list
    for the student's resolved institution.  Chunks without a resolvable
    provenance are dropped (fail closed).  (Same boundary semantics as the
    locked Phase 6.13.8 ``_filter_to_public_chunks``.)
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


def _retrieve_institutional_knowledge(
    query: str,
    institution_id: UUID,
    client: Any | None,
    top_k: int | None,
) -> list[RetrievedChunk]:
    """Run the EXISTING institution-scoped RAG retrieval + visibility filter.

    The query is passed to the existing retrieval system verbatim. The scope
    is the server-resolved institution id — never a client value. Only
    authorized (published, own-institution, whitelisted source type) chunks
    are returned; empty results are a valid outcome, not a failure.
    """
    if not isinstance(query, str) or not query.strip():
        raise AppError(
            "query must be a non-empty string",
            status_code=422,
            code="INVALID_RETRIEVAL_QUERY",
        )

    db = client
    allowed_ks = _build_authorized_knowledge_source_ids(db, institution_id)
    if not allowed_ks:
        # No authorized corpus for this institution -> no knowledge is
        # retrievable. Empty knowledge is a valid context (not a failure).
        return []

    retrieval_request = RetrievalRequest(
        query=query,
        top_k=top_k if top_k is not None else settings.retrieval_top_k,
        institution_id=institution_id,
    )
    retrieval_response = retrieve(retrieval_request)

    chunks = [
        RetrievedChunk(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            document_version_id=result.document_version_id,
            text=result.text,
            similarity_score=result.similarity_score,
            metadata=result.metadata,
        )
        for result in retrieval_response.results
    ]
    if not chunks:
        return []

    # Phase 6.13.8 visibility boundary (defense in depth): hard-filter the
    # retrieved chunks by knowledge-source provenance before anything can
    # enter the personalized context.
    run_ids = {
        str(c.metadata.get("processing_run_id"))
        for c in chunks
        if c.metadata and c.metadata.get("processing_run_id")
    }
    run_to_ks = _resolve_chunk_knowledge_sources(db, run_ids)
    return [
        chunk
        for chunk in _filter_to_authorized_chunks(chunks, run_to_ks, allowed_ks)
    ]


# ============================================================================
# Main entry point
# ============================================================================


def get_personalized_context(
    current_user: dict[str, Any],
    query: str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    client: Any | None = None,
    top_k: int | None = None,
) -> PersonalizedContext:
    """Build the authenticated student's secure personalized retrieval context.

    Combines (and keeps EXPLICITLY separated):

    * ``knowledge`` — institution-scoped RAG chunks, retrieved through the
      EXISTING Phase 3 retrieval service and filtered through the Phase 6.13.8
      knowledge-visibility boundary (published sources of the student's own
      institution only);
    * ``academic`` — the Phase 6.14.4 resolver output (student identity,
      attendance, published academic + test results).

    Args:
        current_user: the dict returned by ``get_current_user()``. This is the
            ONLY identity source: the student and their institution are
            derived server-side from the JWT. There is no client-supplied
            ``student_id`` / ``user_id`` / ``institution_id`` /
            ``organization_id`` / ``scope_id`` parameter, so client identity
            overrides are structurally impossible.
        query: the natural-language retrieval query. Passed to the existing
            RAG retrieval system verbatim; wording NEVER changes what the
            student is authorized to see (no keyword-based security).
        academic_year_id / semester_id: optional NON-identity academic
            filters, forwarded verbatim to the Phase 6.14.4 resolver.
        client: optional already-created Supabase client (tests inject a
            mock; production uses the service-role admin client).
        top_k: optional retrieval budget override; the default reuses the
            EXISTING ``settings.retrieval_top_k`` limit (no new limit system).

    Returns:
        PersonalizedContext — student-safe model (``extra="forbid"``), with
        empty knowledge/attendance/results when none exist (empty data is not
        an authorization failure).

    Raises:
        AppError 422 INVALID_RETRIEVAL_QUERY: empty/blank query.
        AppError 400 INVALID_USER_CONTEXT / 404 STUDENT_PROFILE_NOT_FOUND /
        403 TENANT_MISMATCH / 422 INVALID_FILTER: raised by the existing
        delegated services, never caught or bypassed here.
        AppError 403 NO_TENANT_BOUND: account without a student tenant.
        AppError 403 TENANT_INACTIVE: pending/rejected/suspended institution.
    """
    if not isinstance(query, str) or not query.strip():
        raise AppError(
            "query must be a non-empty string",
            status_code=422,
            code="INVALID_RETRIEVAL_QUERY",
        )

    db = client

    # --- Tenant/institution resolution (server-side, lifecycle-guarded) ----
    institution_id = _resolve_authorized_institution_id(current_user, db)

    # --- Institutional RAG retrieval (existing service, institution scope) --
    knowledge = _retrieve_institutional_knowledge(
        query, institution_id, db, top_k
    )

    # --- Academic context (existing Phase 6.14.4 authorization boundary) ----
    # Attendance/results/student tables are NEVER queried here directly; the
    # existing resolver keeps its own full authorization chain. A service
    # denial (400/403/404/422) propagates — it is never caught or bypassed.
    academic = academic_context_service.get_student_academic_context(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        client=db,
    )

    return PersonalizedContext(
        query=query,
        knowledge=InstitutionalKnowledge(
            institution_id=institution_id,
            chunks=knowledge,
        ),
        academic=academic,
    )





