CREATE FUNCTION public.register_knowledge_upload(actor uuid, tenant uuid, revision uuid,
    expected_version bigint, file_metadata jsonb, selected_document uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE draft public.knowledge_source_revisions; doc_id uuid; version_id uuid; run_id uuid;
    version_number integer; previous jsonb; allowed text[] := ARRAY['original_filename', 'file_type',
        'mime_type', 'file_size_bytes', 'storage_bucket', 'storage_object_key', 'file_checksum', 'version_label']; key text;
BEGIN
    PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.create');
    PERFORM public.assert_knowledge_actor(actor, tenant,
        CASE WHEN selected_document IS NULL THEN 'documents.create' ELSE 'documents.update' END);
    SELECT * INTO draft FROM public.knowledge_source_revisions r
        WHERE r.revision_id = revision AND r.institution_id = tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Revision not found' USING ERRCODE = 'P0002'; END IF;
    IF draft.created_by_user_id IS DISTINCT FROM actor THEN
        PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.update', true);
    END IF;
    IF draft.lifecycle_status <> 'draft' THEN RAISE EXCEPTION 'Draft required' USING ERRCODE = '23514'; END IF;
    IF expected_version IS NULL OR draft.revision_version <> expected_version THEN
        RAISE EXCEPTION 'Revision changed' USING ERRCODE = '40001';
    END IF;
    IF file_metadata IS NULL OR jsonb_typeof(file_metadata) <> 'object' THEN
        RAISE EXCEPTION 'File metadata required' USING ERRCODE = '22023';
    END IF;
    FOR key IN SELECT jsonb_object_keys(file_metadata) LOOP
        IF NOT key = ANY(allowed) THEN RAISE EXCEPTION 'Unsupported file metadata' USING ERRCODE = '22023'; END IF;
    END LOOP;
    previous := to_jsonb(draft);
    IF selected_document IS NULL THEN
        INSERT INTO public.documents(knowledge_source_id) VALUES(draft.knowledge_source_id) RETURNING document_id INTO doc_id;
    ELSE
        SELECT d.document_id INTO doc_id FROM public.documents d
            WHERE d.document_id = selected_document AND d.knowledge_source_id = draft.knowledge_source_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Document not found' USING ERRCODE = 'P0002'; END IF;
    END IF;
    SELECT COALESCE(max(v.version_number), 0) + 1 INTO version_number
        FROM public.document_versions v WHERE v.document_id = doc_id;
    INSERT INTO public.document_versions(document_id, version_number, original_filename, file_type,
        mime_type, file_size_bytes, storage_provider, storage_bucket, storage_object_key, file_checksum, version_label, created_by_user_id)
    VALUES(doc_id, version_number, file_metadata->>'original_filename', file_metadata->>'file_type',
        file_metadata->>'mime_type', (file_metadata->>'file_size_bytes')::bigint, 'r2',
        file_metadata->>'storage_bucket', file_metadata->>'storage_object_key', file_metadata->>'file_checksum', file_metadata->>'version_label', actor)
    RETURNING document_version_id INTO version_id;
    INSERT INTO public.document_processing_runs(document_version_id, processor_name, processor_version, created_at)
        VALUES(version_id, 'knowledge-revisions', '1', clock_timestamp()) RETURNING processing_run_id INTO run_id;
    INSERT INTO public.knowledge_source_revision_documents
        VALUES(revision, draft.knowledge_source_id, doc_id, version_id)
        ON CONFLICT(revision_id, document_id) DO UPDATE SET document_version_id = EXCLUDED.document_version_id;
    PERFORM public.audit_knowledge_revision(actor, tenant, 'document.stage', revision, previous);
    RETURN jsonb_build_object('revision', public.knowledge_revision_view(revision),
        'document_id', doc_id, 'document_version_id', version_id, 'processing_run_id', run_id);
END;
$$;

CREATE FUNCTION public.retry_knowledge_index(actor uuid, tenant uuid, revision uuid,
    expected_version bigint, version_id uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE draft public.knowledge_source_revisions; run_id uuid;
BEGIN
    PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.create');
    SELECT * INTO draft FROM public.knowledge_source_revisions r
        WHERE r.revision_id = revision AND r.institution_id = tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Revision not found' USING ERRCODE = 'P0002'; END IF;
    IF draft.created_by_user_id IS DISTINCT FROM actor THEN
        PERFORM public.assert_knowledge_actor(actor, tenant, 'ai.knowledge.update', true);
    END IF;
    IF draft.lifecycle_status <> 'draft' THEN RAISE EXCEPTION 'Draft required' USING ERRCODE = '23514'; END IF;
    IF expected_version IS NULL OR draft.revision_version <> expected_version THEN
        RAISE EXCEPTION 'Revision changed' USING ERRCODE = '40001';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM public.knowledge_source_revision_documents m
        WHERE m.revision_id = revision AND m.document_version_id = version_id) THEN
        RAISE EXCEPTION 'Version not found' USING ERRCODE = 'P0002';
    END IF;
    IF EXISTS(SELECT 1 FROM public.knowledge_source_revision_documents m
        JOIN public.knowledge_source_revisions r USING(revision_id)
        WHERE m.document_version_id = version_id AND r.lifecycle_status <> 'draft')
        OR EXISTS(SELECT 1 FROM public.document_processing_runs run
            WHERE run.document_version_id = version_id AND (run.status IN ('queued', 'processing')
                OR (run.status = 'ready' AND run.embedding_status IS DISTINCT FROM 'failed'))) THEN
        RAISE EXCEPTION 'Only failed draft indexing can be retried' USING ERRCODE = '23514';
    END IF;
    UPDATE public.knowledge_source_revisions SET updated_at = clock_timestamp() WHERE revision_id = revision;
    INSERT INTO public.document_processing_runs(document_version_id, processor_name, processor_version, created_at)
        VALUES(version_id, 'knowledge-revisions', '1', clock_timestamp()) RETURNING processing_run_id INTO run_id;
    PERFORM public.audit_knowledge_revision(actor, tenant, 'index.retry', revision, to_jsonb(draft));
    RETURN run_id;
END;
$$;
