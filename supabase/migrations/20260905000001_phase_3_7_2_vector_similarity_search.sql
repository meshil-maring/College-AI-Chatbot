-- Phase 3.7.2 - Vector similarity search RPC
-- Searches the existing Phase 3.6 embedding corpus without access filtering.


DROP FUNCTION IF EXISTS "public"."search_similar_chunks"(
    "extensions"."vector"(1536), integer, uuid, uuid, uuid, uuid, uuid, text
);


CREATE OR REPLACE FUNCTION "public"."search_similar_chunks"(
    "query_embedding" "extensions"."vector"(1536),
    "match_count" integer
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
    WHERE ce.model_name = 'qwen/qwen3-embedding-8b'
    ORDER BY ce.embedding <=> query_embedding ASC
    LIMIT match_count;
$$;


REVOKE ALL ON FUNCTION "public"."search_similar_chunks"(
    "extensions"."vector"(1536), integer
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION "public"."search_similar_chunks"(
    "extensions"."vector"(1536), integer
) TO service_role;