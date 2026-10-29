CREATE FUNCTION public.save_knowledge_draft(actor uuid, tenant uuid, payload jsonb,
    source_id uuid DEFAULT NULL, selected_revision uuid DEFAULT NULL, expected_version bigint DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE source public.knowledge_sources; revision public.knowledge_source_revisions;
    next_row public.knowledge_source_revisions; previous jsonb; key text; role_value text;
BEGIN
    PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.create');
    IF payload IS NULL OR jsonb_typeof(payload) <> 'object' THEN
        RAISE EXCEPTION 'Metadata required' USING ERRCODE = '22023';
    END IF;
    FOR key IN SELECT jsonb_object_keys(payload) LOOP
        IF NOT key = ANY(ARRAY['title', 'description', 'source_type', 'authority_level',
            'visibility', 'audience_roles', 'effective_from', 'effective_until']) THEN
            RAISE EXCEPTION 'Unsupported metadata field' USING ERRCODE = '22023';
        END IF;
    END LOOP;
    IF source_id IS NULL THEN
        IF selected_revision IS NOT NULL THEN RAISE EXCEPTION 'Source required' USING ERRCODE = '22023'; END IF;
        INSERT INTO public.knowledge_sources(institution_id, title, description, source_type, created_by_user_id, owner_user_id)
        VALUES(tenant, payload->>'title', payload->>'description', payload->>'source_type', actor, actor)
        RETURNING * INTO source;
    ELSE
        SELECT * INTO source FROM public.knowledge_sources s
            WHERE s.knowledge_source_id = source_id AND s.institution_id = tenant FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Source not found' USING ERRCODE = 'P0002'; END IF;
        IF source.created_by_user_id IS DISTINCT FROM actor THEN
            PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.update', true);
        END IF;
    END IF;
    IF COALESCE(payload->>'source_type', source.source_type) IN ('faq', 'notice') OR source.source_type IN ('faq', 'notice') THEN
        RAISE EXCEPTION 'Use the canonical editor for this source type' USING ERRCODE = '22023';
    END IF;
    IF selected_revision IS NULL THEN
        INSERT INTO public.knowledge_source_revisions(knowledge_source_id, institution_id, revision_number,
            title, description, source_type, authority_level, visibility, effective_from, effective_until, created_by_user_id)
        SELECT source.knowledge_source_id, tenant, COALESCE(max(r.revision_number), 0) + 1,
            source.title, source.description, source.source_type, source.authority_level,
            source.visibility, source.effective_from, source.effective_until, actor
        FROM public.knowledge_source_revisions r WHERE r.knowledge_source_id = source.knowledge_source_id
        RETURNING * INTO revision;
        IF source.published_revision_id IS NOT NULL THEN
            INSERT INTO public.knowledge_source_revision_audiences
                SELECT revision.revision_id, a.role FROM public.knowledge_source_revision_audiences a
                WHERE a.revision_id = source.published_revision_id;
            INSERT INTO public.knowledge_source_revision_documents
                SELECT revision.revision_id, m.knowledge_source_id, m.document_id, m.document_version_id
                FROM public.knowledge_source_revision_documents m WHERE m.revision_id = source.published_revision_id;
        END IF;
    ELSE
        SELECT * INTO revision FROM public.knowledge_source_revisions r
            WHERE r.revision_id = selected_revision AND r.knowledge_source_id = source.knowledge_source_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Revision not found' USING ERRCODE = 'P0002'; END IF;
        IF revision.created_by_user_id IS DISTINCT FROM actor THEN
            PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.update', true);
        END IF;
        IF expected_version IS NULL OR revision.revision_version <> expected_version THEN
            RAISE EXCEPTION 'Revision changed; reload before saving' USING ERRCODE = '40001';
        END IF;
        IF revision.lifecycle_status <> 'draft' THEN RAISE EXCEPTION 'Draft required' USING ERRCODE = '23514'; END IF;
    END IF;
    previous := to_jsonb(revision);
    next_row := jsonb_populate_record(revision, payload - 'audience_roles');
    UPDATE public.knowledge_source_revisions r SET title = next_row.title, description = next_row.description,
        source_type = next_row.source_type, authority_level = next_row.authority_level,
        visibility = next_row.visibility, effective_from = next_row.effective_from, effective_until = next_row.effective_until
        WHERE r.revision_id = revision.revision_id;
    IF payload ? 'audience_roles' THEN
        IF jsonb_typeof(payload->'audience_roles') <> 'array' THEN
            RAISE EXCEPTION 'Role targets must be an array' USING ERRCODE = '22023';
        END IF;
        DELETE FROM public.knowledge_source_revision_audiences a WHERE a.revision_id = revision.revision_id;
        FOR role_value IN SELECT jsonb_array_elements_text(payload->'audience_roles') LOOP
            INSERT INTO public.knowledge_source_revision_audiences VALUES(revision.revision_id, role_value);
        END LOOP;
    END IF;
    PERFORM public.audit_knowledge_revision(actor, tenant, 'draft.save', revision.revision_id, previous);
    RETURN public.knowledge_revision_view(revision.revision_id);
END;
$$;
