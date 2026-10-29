CREATE FUNCTION public.decide_knowledge_revision(actor uuid, tenant uuid, revision uuid,
    action text, expected_version bigint, expected_policy bigint DEFAULT NULL, notes text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE draft public.knowledge_source_revisions; source public.knowledge_sources; previous jsonb;
BEGIN
    IF action = 'submit' THEN
        PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.create');
    ELSIF action IN ('request_changes', 'approve', 'publish', 'unpublish') THEN
        PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.update', true);
    ELSE RAISE EXCEPTION 'Unknown review action' USING ERRCODE = '22023'; END IF;
    SELECT * INTO draft FROM public.knowledge_source_revisions r
        WHERE r.revision_id = revision AND r.institution_id = tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Revision not found' USING ERRCODE = 'P0002'; END IF;
    IF action = 'submit' AND draft.created_by_user_id IS DISTINCT FROM actor THEN
        PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.update', true);
    END IF;
    IF expected_version IS NULL OR draft.revision_version <> expected_version THEN
        RAISE EXCEPTION 'Revision changed; reload before deciding' USING ERRCODE = '40001';
    END IF;
    SELECT * INTO source FROM public.knowledge_sources s
        WHERE s.knowledge_source_id = draft.knowledge_source_id FOR UPDATE;
    previous := to_jsonb(draft);
    IF action = 'submit' AND draft.lifecycle_status = 'draft' THEN
        IF EXISTS(SELECT 1 FROM public.knowledge_source_revision_documents m WHERE m.revision_id = revision
            AND NOT EXISTS(SELECT 1 FROM public.document_processing_runs run
                WHERE run.document_version_id = m.document_version_id AND run.status = 'ready'
                    AND run.embedding_status = 'embedded' AND run.completed_at IS NOT NULL)) THEN
            RAISE EXCEPTION 'Complete indexing before submitting for review' USING ERRCODE = '23514';
        END IF;
        UPDATE public.knowledge_source_revisions SET lifecycle_status = 'under_review', submitted_at = clock_timestamp()
            WHERE revision_id = revision;
    ELSIF action = 'request_changes' AND draft.lifecycle_status IN ('under_review', 'approved') THEN
        IF NULLIF(btrim(notes), '') IS NULL THEN RAISE EXCEPTION 'Review feedback required' USING ERRCODE = '22023'; END IF;
        UPDATE public.knowledge_source_revisions SET lifecycle_status = 'draft', review_notes = notes
            WHERE revision_id = revision;
    ELSIF action = 'approve' AND draft.lifecycle_status = 'under_review' THEN
        UPDATE public.knowledge_source_revisions SET lifecycle_status = 'approved', reviewed_by_user_id = actor,
            approved_by_user_id = actor, reviewed_at = clock_timestamp(), approved_at = clock_timestamp(), review_notes = notes
            WHERE revision_id = revision;
    ELSIF action IN ('publish', 'unpublish') THEN
        IF expected_policy IS NULL OR source.policy_version <> expected_policy THEN
            RAISE EXCEPTION 'Live policy changed; reload before publishing' USING ERRCODE = '40001';
        END IF;
        IF action = 'publish' AND draft.lifecycle_status = 'approved' THEN
            -- Lock versions before changing lifecycle; no early purge or supersession.
            PERFORM v.document_version_id FROM public.document_versions v
                JOIN public.knowledge_source_revision_documents m USING(document_version_id)
                WHERE m.revision_id = revision ORDER BY v.document_version_id FOR UPDATE OF v;
            UPDATE public.knowledge_source_revisions SET lifecycle_status = 'superseded'
                WHERE revision_id = source.published_revision_id;
            UPDATE public.document_versions v SET lifecycle_status = 'published'
                FROM public.knowledge_source_revision_documents m
                WHERE m.revision_id = revision AND m.document_version_id = v.document_version_id;
            UPDATE public.knowledge_source_revisions SET lifecycle_status = 'published', published_at = clock_timestamp()
                WHERE revision_id = revision;
            UPDATE public.knowledge_sources SET published_revision_id = revision, title = draft.title,
                description = draft.description, source_type = draft.source_type, authority_level = draft.authority_level,
                visibility = draft.visibility, lifecycle_status = 'published', effective_from = draft.effective_from,
                effective_until = draft.effective_until, reviewed_by_user_id = actor, approved_by_user_id = actor
                WHERE knowledge_source_id = draft.knowledge_source_id;
        ELSIF action = 'unpublish' AND source.published_revision_id = revision THEN
            UPDATE public.knowledge_source_revisions SET lifecycle_status = 'archived' WHERE revision_id = revision;
            UPDATE public.knowledge_sources SET published_revision_id = NULL, lifecycle_status = 'archived'
                WHERE knowledge_source_id = draft.knowledge_source_id;
        ELSE RAISE EXCEPTION 'Invalid publication state' USING ERRCODE = '23514'; END IF;
    ELSE RAISE EXCEPTION 'Invalid review state' USING ERRCODE = '23514'; END IF;
    PERFORM public.assert_knowledge_revision_integrity(revision);
    PERFORM public.audit_knowledge_revision(actor, tenant, 'revision.' || action, revision, previous);
    RETURN public.knowledge_revision_view(revision);
END;
$$;
