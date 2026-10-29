CREATE FUNCTION public.knowledge_revision_view(revision uuid) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
    SELECT to_jsonb(r) || jsonb_build_object(
        'policy_version', s.policy_version,
        'audience_roles', COALESCE((SELECT jsonb_agg(a.role ORDER BY a.role)
            FROM public.knowledge_source_revision_audiences a WHERE a.revision_id = r.revision_id), '[]'),
        'documents', COALESCE((SELECT jsonb_agg(jsonb_build_object(
            'document_id', v.document_id, 'document_version_id', v.document_version_id,
            'original_filename', v.original_filename, 'file_type', v.file_type,
            'version_number', v.version_number, 'file_size_bytes', v.file_size_bytes,
            'indexing_status', CASE WHEN EXISTS (SELECT 1 FROM public.document_processing_runs run
                WHERE run.document_version_id = v.document_version_id AND run.status = 'ready'
                    AND run.embedding_status = 'embedded' AND run.completed_at IS NOT NULL)
                THEN 'indexed' ELSE COALESCE((SELECT CASE WHEN run.status = 'failed' OR run.embedding_status = 'failed'
                    THEN 'failed' WHEN run.status = 'queued' THEN 'queued' ELSE 'processing' END FROM public.document_processing_runs run
                    WHERE run.document_version_id = v.document_version_id ORDER BY run.created_at DESC LIMIT 1), 'queued') END
        ) ORDER BY v.original_filename)
        FROM public.knowledge_source_revision_documents m JOIN public.document_versions v USING(document_version_id)
        WHERE m.revision_id = r.revision_id), '[]'))
    FROM public.knowledge_source_revisions r
    JOIN public.knowledge_sources s USING(knowledge_source_id) WHERE r.revision_id = revision;
$$;

CREATE FUNCTION public.read_knowledge_revisions(actor uuid, tenant uuid, mode text DEFAULT 'own',
    selected_revision uuid DEFAULT NULL, page_limit integer DEFAULT 20, page_offset integer DEFAULT 0)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result jsonb;
BEGIN
    IF mode = 'review' THEN
        PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.read', true);
    ELSIF mode = 'own' THEN
        PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.create');
    ELSE RAISE EXCEPTION 'Unknown resource view' USING ERRCODE = '22023'; END IF;
    IF page_limit NOT BETWEEN 1 AND 100 OR page_offset NOT BETWEEN 0 AND 100000 THEN
        RAISE EXCEPTION 'Invalid pagination' USING ERRCODE = '22023';
    END IF;
    WITH permitted AS (
        SELECT r.* FROM public.knowledge_source_revisions r WHERE r.institution_id = tenant
            AND (mode = 'review' OR r.created_by_user_id = actor)
            AND (selected_revision IS NULL OR r.revision_id = selected_revision)
    ), page AS (SELECT * FROM permitted ORDER BY updated_at DESC, revision_id LIMIT page_limit OFFSET page_offset)
    SELECT jsonb_build_object('items', COALESCE((SELECT jsonb_agg(public.knowledge_revision_view(p.revision_id)
        ORDER BY p.updated_at DESC, p.revision_id) FROM page p), '[]'), 'total', (SELECT count(*) FROM permitted)) INTO result;
    IF selected_revision IS NOT NULL AND (result->>'total')::integer = 0 THEN
        RAISE EXCEPTION 'Revision not found' USING ERRCODE = 'P0002';
    END IF;
    RETURN result;
END;
$$;
