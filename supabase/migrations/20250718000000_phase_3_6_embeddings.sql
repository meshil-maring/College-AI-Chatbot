-- Phase 3.6 — Embeddings
-- Adds pgvector support, chunk_embeddings table, and embedding status columns
-- on document_processing_runs.
--
-- Does NOT modify knowledge_chunks (Phase 3.5 — LOCKED).
-- Does NOT modify document_processing_runs.status or its CHECK constraint.
-- Does NOT create an ANN/HNSW/IVFFlat index (Phase 3.7).


-- ---------------------------------------------------------------------------
-- A. Enable pgvector
-- ---------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS vector
    SCHEMA extensions;


-- ---------------------------------------------------------------------------
-- B. chunk_embeddings
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS "public"."chunk_embeddings" (
    "chunk_id"             "uuid"           NOT NULL,
    "model_name"           "text"           NOT NULL,
    "embedding_dimensions" integer          NOT NULL,
    "embedding"            extensions.vector(1536) NOT NULL,
    "embedded_at"          timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "chunk_embeddings_model_name_check"
        CHECK (("btrim"("model_name") <> ''::"text")),
    CONSTRAINT "chunk_embeddings_embedding_dimensions_check"
        CHECK (("embedding_dimensions" > 0))
);

ALTER TABLE "public"."chunk_embeddings" OWNER TO "postgres";

ALTER TABLE ONLY "public"."chunk_embeddings"
    ADD CONSTRAINT "chunk_embeddings_pkey"
        PRIMARY KEY ("chunk_id", "model_name");

ALTER TABLE ONLY "public"."chunk_embeddings"
    ADD CONSTRAINT "chunk_embeddings_chunk_id_fkey"
        FOREIGN KEY ("chunk_id")
        REFERENCES "public"."knowledge_chunks"("chunk_id")
        ON DELETE CASCADE;


-- ---------------------------------------------------------------------------
-- C. Embedding status columns on document_processing_runs
--    Both columns are nullable so all existing rows remain valid.
--    The existing status column and its CHECK constraint are untouched.
-- ---------------------------------------------------------------------------

ALTER TABLE "public"."document_processing_runs"
    ADD COLUMN "embedding_status" "text",
    ADD COLUMN "embedding_error"  "text";

ALTER TABLE "public"."document_processing_runs"
    ADD CONSTRAINT "document_processing_runs_embedding_status_check"
        CHECK (
            ("embedding_status" IS NULL)
            OR ("embedding_status" = ANY (
                ARRAY[
                    'pending'::"text",
                    'processing'::"text",
                    'embedded'::"text",
                    'failed'::"text"
                ]
            ))
        );

ALTER TABLE "public"."document_processing_runs"
    ADD CONSTRAINT "document_processing_runs_embedding_failed_error_check"
        CHECK (
            ("embedding_status" <> 'failed'::"text")
            OR ("embedding_error" IS NOT NULL)
        );
