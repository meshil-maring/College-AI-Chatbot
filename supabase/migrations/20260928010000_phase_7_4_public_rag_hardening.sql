-- Phase 7.4 - public RAG retrieval hardening.
--
-- Retain the Phase 7.2 tenant/public/lifecycle predicate while failing closed
-- for inconsistent embedding metadata and bounding the server-side RPC limit.

CREATE OR REPLACE FUNCTION public.search_public_knowledge_chunks(
    query_embedding extensions.vector(1536),
    match_count integer,
    filter_institution_id uuid,
    filter_knowledge_source_id uuid DEFAULT NULL,
    filter_model_name text DEFAULT NULL
)
RETURNS TABLE (
    chunk_id uuid,
    document_id uuid,
    document_version_id uuid,
    content_text text,
    processing_run_id uuid,
    chunk_sequence integer,
    section_title text,
    source_title text,
    source_type text,
    model_name text,
    distance double precision
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT
        kc.chunk_id,
        d.document_id,
        dv.document_version_id,
        kc.content_text,
        dpr.processing_run_id,
        kc.chunk_sequence,
        kc.section_title,
        ks.title AS source_title,
        ks.source_type,
        ce.model_name,
        ce.embedding <=> query_embedding AS distance
    FROM public.chunk_embeddings AS ce
    JOIN public.knowledge_chunks AS kc
      ON kc.chunk_id = ce.chunk_id
    JOIN public.document_processing_runs AS dpr
      ON dpr.processing_run_id = kc.processing_run_id
    JOIN public.document_versions AS dv
      ON dv.document_version_id = dpr.document_version_id
    JOIN public.documents AS d
      ON d.document_id = dv.document_id
    JOIN public.knowledge_sources AS ks
      ON ks.knowledge_source_id = d.knowledge_source_id
    WHERE match_count BETWEEN 1 AND 20
      AND filter_institution_id IS NOT NULL
      AND ks.institution_id = filter_institution_id
      AND ks.visibility = 'public'
      AND ks.lifecycle_status = 'published'
      AND (ks.effective_from IS NULL OR ks.effective_from <= CURRENT_DATE)
      AND (ks.effective_until IS NULL OR ks.effective_until >= CURRENT_DATE)
      AND dv.lifecycle_status = 'published'
      AND (dv.effective_from IS NULL OR dv.effective_from <= CURRENT_DATE)
      AND (dv.effective_until IS NULL OR dv.effective_until >= CURRENT_DATE)
      AND dpr.status = 'ready'
      AND dpr.embedding_status = 'embedded'
      AND dpr.completed_at IS NOT NULL
      AND ce.embedding_dimensions = 1536
      AND (filter_knowledge_source_id IS NULL OR ks.knowledge_source_id = filter_knowledge_source_id)
      AND (filter_model_name IS NULL OR ce.model_name = filter_model_name)
    ORDER BY ce.embedding <=> query_embedding ASC
    LIMIT LEAST(match_count, 20);
$$;

REVOKE ALL ON FUNCTION public.search_public_knowledge_chunks(
    extensions.vector(1536), integer, uuid, uuid, text
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.search_public_knowledge_chunks(
    extensions.vector(1536), integer, uuid, uuid, text
) TO service_role;
