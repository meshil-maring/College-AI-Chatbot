-- Phase 3.8 - Metadata and access filtering for scoped vector search

DROP FUNCTION IF EXISTS "public"."search_similar_chunks"(
    "extensions"."vector"(1536), integer
);

DROP FUNCTION IF EXISTS "public"."search_similar_chunks"(
    "extensions"."vector"(1536), integer, uuid, uuid, uuid, uuid, uuid, text
);

CREATE OR REPLACE FUNCTION "public"."search_similar_chunks"(
    "query_embedding" "extensions"."vector"(1536),
    "match_count" integer,
    "filter_institution_id" uuid DEFAULT NULL,
    "filter_knowledge_source_id" uuid DEFAULT NULL,
    "filter_document_id" uuid DEFAULT NULL,
    "filter_document_version_id" uuid DEFAULT NULL,
    "filter_processing_run_id" uuid DEFAULT NULL,
    "filter_model_name" text DEFAULT NULL
)
RETURNS TABLE (
    "chunk_id" uuid,
    "document_id" uuid,
    "document_version_id" uuid,
    "content_text" text,
    "processing_run_id" uuid,
    "chunk_sequence" integer,
    "section_title" text,
    "model_name" text,
    "distance" double precision
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT
        kc.chunk_id,
        dv.document_id,
        dv.document_version_id,
        kc.content_text,
        kc.processing_run_id,
        kc.chunk_sequence,
        kc.section_title,
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
    WHERE (filter_institution_id IS NULL OR ks.institution_id = filter_institution_id)
      AND (filter_knowledge_source_id IS NULL OR ks.knowledge_source_id = filter_knowledge_source_id)
      AND (filter_document_id IS NULL OR d.document_id = filter_document_id)
      AND (filter_document_version_id IS NULL OR dv.document_version_id = filter_document_version_id)
      AND (filter_processing_run_id IS NULL OR kc.processing_run_id = filter_processing_run_id)
      AND (filter_model_name IS NULL OR ce.model_name = filter_model_name)
      AND (
          filter_institution_id IS NOT NULL
          OR filter_knowledge_source_id IS NOT NULL
          OR filter_document_id IS NOT NULL
          OR filter_document_version_id IS NOT NULL
          OR filter_processing_run_id IS NOT NULL
          OR filter_model_name IS NOT NULL
      )
    ORDER BY ce.embedding <=> query_embedding ASC
    LIMIT match_count;
$$;

REVOKE ALL ON FUNCTION "public"."search_similar_chunks"(
    "extensions"."vector"(1536), integer, uuid, uuid, uuid, uuid, uuid, text
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION "public"."search_similar_chunks"(
    "extensions"."vector"(1536), integer, uuid, uuid, uuid, uuid, uuid, text
) TO service_role;