CREATE FUNCTION public.read_knowledge_resources(actor uuid, tenant uuid,
    source_id uuid DEFAULT NULL, page_limit integer DEFAULT 20, page_offset integer DEFAULT 0,
    excluded_types text[] DEFAULT '{}') RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result jsonb; roles text[];
BEGIN
    roles := public.knowledge_actor_roles(actor, tenant, 'documents.read');
    IF cardinality(roles) = 0 THEN RAISE EXCEPTION 'Resource read permission required' USING ERRCODE = '42501'; END IF;
    IF page_limit NOT BETWEEN 1 AND 100 OR page_offset NOT BETWEEN 0 AND 100000 THEN
        RAISE EXCEPTION 'Invalid pagination' USING ERRCODE = '22023';
    END IF;
    WITH permitted AS (
        SELECT s.* FROM public.knowledge_sources s
        WHERE s.institution_id = tenant AND NOT s.source_type = ANY(excluded_types)
            AND (source_id IS NULL OR s.knowledge_source_id = source_id)
            AND public.knowledge_source_allowed(actor, tenant, s.knowledge_source_id, 'documents.read')
    ), page AS (SELECT * FROM permitted ORDER BY created_at DESC, knowledge_source_id LIMIT page_limit OFFSET page_offset)
    SELECT jsonb_build_object('total', (SELECT count(*) FROM permitted), 'items', COALESCE((
        SELECT jsonb_agg(jsonb_build_object('knowledge_source_id', p.knowledge_source_id, 'title', p.title,
            'description', p.description, 'source_type', p.source_type, 'visibility', p.visibility,
            'effective_from', p.effective_from, 'effective_until', p.effective_until,
            'policy_version', p.policy_version, 'audience_roles', COALESCE((SELECT jsonb_agg(a.role ORDER BY a.role)
                FROM public.knowledge_source_revision_audiences a WHERE a.revision_id = p.published_revision_id), '[]'),
            'documents', COALESCE((SELECT jsonb_agg(jsonb_build_object('document_id', v.document_id,
                'document_version_id', v.document_version_id, 'original_filename', v.original_filename,
                'file_type', v.file_type, 'version_number', v.version_number) ORDER BY v.original_filename)
                FROM public.documents d JOIN public.document_versions v USING(document_id)
                WHERE d.knowledge_source_id = p.knowledge_source_id
                    AND public.knowledge_version_allowed(p.knowledge_source_id, v.document_version_id)), '[]')
        ) ORDER BY p.created_at DESC, p.knowledge_source_id) FROM page p), '[]')) INTO result;
    IF source_id IS NOT NULL AND (result->>'total')::integer = 0 THEN
        RAISE EXCEPTION 'Resource not found' USING ERRCODE = 'P0002';
    END IF;
    RETURN result;
END;
$$;
