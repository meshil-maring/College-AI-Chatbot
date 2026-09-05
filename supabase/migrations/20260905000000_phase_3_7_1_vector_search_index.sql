-- Phase 3.7.1 - Vector storage DB/index only
-- Adds the ANN index for the existing Phase 3.6 embeddings.
--
-- Does NOT modify knowledge_chunks or chunk_embeddings definitions,
-- constraints, stored vectors, embedding generation, or retrieval behavior.


-- ---------------------------------------------------------------------------
-- A. ANN index for cosine-distance vector search
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS "chunk_embeddings_embedding_hnsw_idx"
    ON "public"."chunk_embeddings"
    USING hnsw ("embedding" "extensions"."vector_cosine_ops")
    WITH (m = 16, ef_construction = 64);