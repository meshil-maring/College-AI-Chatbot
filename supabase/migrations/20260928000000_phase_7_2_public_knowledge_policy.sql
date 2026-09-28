-- Phase 7.2 - authoritative public knowledge/data access policy.
--
-- Visibility is independent of source_type.  The default is deliberately
-- fail-closed: new sources are restricted until an administrator explicitly
-- chooses a broader audience.

ALTER TABLE public.knowledge_sources
    ADD COLUMN IF NOT EXISTS visibility text NOT NULL DEFAULT 'restricted';

ALTER TABLE public.knowledge_sources
    DROP CONSTRAINT IF EXISTS knowledge_sources_visibility_check;

ALTER TABLE public.knowledge_sources
    ADD CONSTRAINT knowledge_sources_visibility_check
    CHECK (visibility = ANY (ARRAY['public'::text, 'authenticated'::text, 'restricted'::text]));

-- Backward-compatible, non-expansive backfill: these are exactly the source
-- categories and lifecycle state that the pre-7.2 public endpoint exposed.
-- No draft/approved/archived source and no other source type becomes public.
UPDATE public.knowledge_sources
SET visibility = 'public'
WHERE lifecycle_status = 'published'
  AND source_type = ANY (ARRAY['faq'::text, 'notice'::text, 'handbook'::text]);

CREATE INDEX IF NOT EXISTS idx_knowledge_sources_public_policy
    ON public.knowledge_sources (institution_id, visibility, lifecycle_status);

-- A separate RPC makes the public predicate impossible to confuse with the
-- broader authenticated metadata search.  The service-role backend remains
-- the caller; anon/authenticated roles receive no direct execution grant.
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
    WHERE filter_institution_id IS NOT NULL
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
      AND (filter_knowledge_source_id IS NULL OR ks.knowledge_source_id = filter_knowledge_source_id)
      AND (filter_model_name IS NULL OR ce.model_name = filter_model_name)
    ORDER BY ce.embedding <=> query_embedding ASC
    LIMIT match_count;
$$;

REVOKE ALL ON FUNCTION public.search_public_knowledge_chunks(
    extensions.vector(1536), integer, uuid, uuid, text
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.search_public_knowledge_chunks(
    extensions.vector(1536), integer, uuid, uuid, text
) TO service_role;
