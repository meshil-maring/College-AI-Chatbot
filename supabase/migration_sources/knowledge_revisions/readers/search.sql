CREATE FUNCTION public.search_audience_knowledge_chunks(actor uuid, query_embedding extensions.vector(1536),
    match_count integer, filter_institution_id uuid, filter_knowledge_source_id uuid DEFAULT NULL,
    filter_document_id uuid DEFAULT NULL, filter_document_version_id uuid DEFAULT NULL,
    filter_processing_run_id uuid DEFAULT NULL, filter_model_name text DEFAULT NULL)
RETURNS TABLE(chunk_id uuid, document_id uuid, document_version_id uuid, content_text text,
    processing_run_id uuid, chunk_sequence integer, section_title text, source_title text,
    source_type text, model_name text, distance double precision)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE = '42501';
    END IF;
    IF match_count NOT BETWEEN 1 AND 20 OR filter_institution_id IS NULL OR filter_model_name IS NULL THEN
        RAISE EXCEPTION 'Invalid retrieval scope or limit' USING ERRCODE = '22023';
    END IF;
    IF actor IS NOT NULL AND cardinality(public.knowledge_actor_roles(actor, filter_institution_id, 'ai.chat')) = 0 THEN
        RAISE EXCEPTION 'Chat permission required' USING ERRCODE = '42501';
    END IF;
    RETURN QUERY SELECT chunk.chunk_id, doc.document_id, version.document_version_id, chunk.content_text,
        run.processing_run_id, chunk.chunk_sequence, chunk.section_title, source.title,
        source.source_type, embedding.model_name,
        (embedding.embedding OPERATOR(extensions.<=>) query_embedding)::double precision
    FROM public.chunk_embeddings embedding
    JOIN public.knowledge_chunks chunk USING(chunk_id)
    JOIN public.document_processing_runs run USING(processing_run_id)
    JOIN public.document_versions version USING(document_version_id)
    JOIN public.documents doc USING(document_id)
    JOIN public.knowledge_sources source USING(knowledge_source_id)
    WHERE source.institution_id = filter_institution_id
        AND public.knowledge_source_allowed(actor, filter_institution_id, source.knowledge_source_id)
        AND public.knowledge_version_allowed(source.knowledge_source_id, version.document_version_id)
        AND run.status = 'ready' AND run.embedding_status = 'embedded' AND run.completed_at IS NOT NULL
        AND embedding.model_name = filter_model_name AND embedding.embedding_dimensions = 1536
        AND extensions.vector_dims(embedding.embedding) = 1536
        AND (filter_knowledge_source_id IS NULL OR source.knowledge_source_id = filter_knowledge_source_id)
        AND (filter_document_id IS NULL OR doc.document_id = filter_document_id)
        AND (filter_document_version_id IS NULL OR version.document_version_id = filter_document_version_id)
        AND (filter_processing_run_id IS NULL OR run.processing_run_id = filter_processing_run_id)
    ORDER BY embedding.embedding OPERATOR(extensions.<=>) query_embedding LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.search_public_knowledge_chunks(
    query_embedding extensions.vector(1536), match_count integer, filter_institution_id uuid,
    filter_knowledge_source_id uuid DEFAULT NULL, filter_model_name text DEFAULT NULL)
RETURNS TABLE(chunk_id uuid, document_id uuid, document_version_id uuid, content_text text,
    processing_run_id uuid, chunk_sequence integer, section_title text, source_title text,
    source_type text, model_name text, distance double precision)
LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
    SELECT * FROM public.search_audience_knowledge_chunks(NULL, query_embedding, match_count,
        filter_institution_id, filter_knowledge_source_id, NULL, NULL, NULL, filter_model_name);
$$;
