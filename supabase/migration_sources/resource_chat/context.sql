-- Returns no metadata for an unpublished, unindexed or unauthorized source.
CREATE FUNCTION public.read_resource_chat_context(actor uuid, tenant uuid, source_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE source public.knowledge_sources;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' OR actor IS NULL THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE = '42501';
    END IF;
    SELECT * INTO source FROM public.knowledge_sources s
        WHERE s.knowledge_source_id = source_id AND s.institution_id = tenant FOR SHARE;
    IF NOT FOUND OR NOT public.knowledge_source_allowed(actor, tenant, source_id, 'ai.chat')
        OR NOT EXISTS (
            SELECT 1 FROM public.documents d
            JOIN public.document_versions v USING (document_id)
            JOIN public.document_processing_runs run USING (document_version_id)
            JOIN public.knowledge_chunks chunk USING (processing_run_id)
            JOIN public.chunk_embeddings embedding USING (chunk_id)
            WHERE d.knowledge_source_id = source_id
                AND public.knowledge_version_allowed(source_id, v.document_version_id)
                AND run.status = 'ready' AND run.embedding_status = 'embedded'
                AND run.completed_at IS NOT NULL
        ) THEN
        RAISE EXCEPTION 'Resource unavailable' USING ERRCODE = 'P0002';
    END IF;
    RETURN jsonb_build_object('knowledge_source_id', source.knowledge_source_id,
        'institution_id', source.institution_id, 'title', source.title,
        'policy_version', source.policy_version, 'available', true);
END;
$$;
REVOKE ALL ON FUNCTION public.read_resource_chat_context(uuid,uuid,uuid)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.read_resource_chat_context(uuid,uuid,uuid) TO service_role;
