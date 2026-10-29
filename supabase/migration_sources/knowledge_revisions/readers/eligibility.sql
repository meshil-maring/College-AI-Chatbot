CREATE FUNCTION public.knowledge_source_allowed(actor uuid, tenant uuid, source_id uuid, permission text DEFAULT 'ai.chat')
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE source public.knowledge_sources; roles text[];
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE = '42501';
    END IF;
    SELECT s.* INTO source FROM public.knowledge_sources s
    JOIN public.institutions i USING(institution_id)
    JOIN public.organizations o USING(organization_id)
    WHERE s.knowledge_source_id = source_id AND s.institution_id = tenant
        AND i.is_active AND i.status = 'active' AND o.status = 'active'
        AND s.lifecycle_status = 'published'
        AND (s.effective_from IS NULL OR s.effective_from <= CURRENT_DATE)
        AND (s.effective_until IS NULL OR s.effective_until >= CURRENT_DATE);
    IF NOT FOUND THEN RETURN false; END IF;
    IF source.published_revision_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM public.knowledge_source_revisions r
        WHERE r.revision_id = source.published_revision_id AND r.lifecycle_status = 'published'
    ) THEN RETURN false; END IF;
    IF actor IS NULL THEN RETURN source.visibility = 'public'; END IF;
    roles := public.knowledge_actor_roles(actor, tenant, permission);
    IF cardinality(roles) = 0 THEN RETURN false; END IF;
    IF source.visibility IN ('public', 'authenticated') THEN RETURN true; END IF;
    RETURN source.published_revision_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM public.knowledge_source_revision_audiences target
        WHERE target.revision_id = source.published_revision_id AND target.role = ANY(roles)
    );
END;
$$;

CREATE FUNCTION public.knowledge_version_allowed(source_id uuid, version_id uuid)
RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS(SELECT 1 FROM public.document_versions v
        JOIN public.documents d USING(document_id)
        JOIN public.knowledge_sources s USING(knowledge_source_id)
        WHERE s.knowledge_source_id = source_id AND v.document_version_id = version_id
            AND v.lifecycle_status = 'published'
            AND (v.effective_from IS NULL OR v.effective_from <= CURRENT_DATE)
            AND (v.effective_until IS NULL OR v.effective_until >= CURRENT_DATE)
            AND (s.published_revision_id IS NULL OR EXISTS (
                SELECT 1 FROM public.knowledge_source_revision_documents m
                WHERE m.revision_id = s.published_revision_id AND m.document_version_id = version_id))
            AND EXISTS(SELECT 1 FROM public.document_processing_runs run
                WHERE run.document_version_id = version_id AND run.status = 'ready'
                    AND run.embedding_status = 'embedded' AND run.completed_at IS NOT NULL));
$$;
