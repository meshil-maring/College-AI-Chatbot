-- Snapshot only already-published public/authenticated sources with usable files.
-- Restricted, draft, expired, future-dated, incomplete or metadata-only sources
-- receive no live pointer. Never infer role audiences or manufacture approval.
INSERT INTO public.knowledge_source_revisions (
    knowledge_source_id, institution_id, revision_number, title, description,
    source_type, authority_level, visibility, lifecycle_status, effective_from,
    effective_until, created_by_user_id, reviewed_by_user_id, approved_by_user_id,
    published_at, created_at, updated_at, is_legacy_snapshot
)
SELECT ks.knowledge_source_id, ks.institution_id, 1, ks.title, ks.description,
    ks.source_type, ks.authority_level, ks.visibility, 'published', ks.effective_from,
    ks.effective_until, ks.created_by_user_id, ks.reviewed_by_user_id,
    ks.approved_by_user_id, ks.updated_at, ks.created_at, ks.updated_at, true
FROM public.knowledge_sources ks
WHERE ks.lifecycle_status = 'published'
    AND ks.visibility IN ('public', 'authenticated')
    AND ks.source_type NOT IN ('faq', 'notice')
    AND (ks.effective_from IS NULL OR ks.effective_from <= CURRENT_DATE)
    AND (ks.effective_until IS NULL OR ks.effective_until >= CURRENT_DATE)
    AND btrim(ks.title) <> ''
    AND EXISTS (
        SELECT 1 FROM public.documents d
        JOIN public.document_versions dv USING (document_id)
        JOIN public.document_processing_runs run USING (document_version_id)
        WHERE d.knowledge_source_id = ks.knowledge_source_id
            AND dv.lifecycle_status = 'published'
            AND (dv.effective_from IS NULL OR dv.effective_from <= CURRENT_DATE)
            AND (dv.effective_until IS NULL OR dv.effective_until >= CURRENT_DATE)
            AND run.status = 'ready' AND run.embedding_status = 'embedded'
            AND run.completed_at IS NOT NULL
    );

INSERT INTO public.knowledge_source_revision_documents (
    revision_id, knowledge_source_id, document_id, document_version_id
)
SELECT DISTINCT ON (revision.revision_id, d.document_id)
    revision.revision_id, revision.knowledge_source_id, d.document_id, dv.document_version_id
FROM public.knowledge_source_revisions revision
JOIN public.documents d USING (knowledge_source_id)
JOIN public.document_versions dv USING (document_id)
WHERE revision.is_legacy_snapshot
    AND dv.lifecycle_status = 'published'
    AND (dv.effective_from IS NULL OR dv.effective_from <= CURRENT_DATE)
    AND (dv.effective_until IS NULL OR dv.effective_until >= CURRENT_DATE)
    AND EXISTS (
        SELECT 1 FROM public.document_processing_runs run
        WHERE run.document_version_id = dv.document_version_id
            AND run.status = 'ready' AND run.embedding_status = 'embedded'
            AND run.completed_at IS NOT NULL
    )
ORDER BY revision.revision_id, d.document_id, dv.version_number DESC;

UPDATE public.knowledge_sources ks
SET published_revision_id = revision.revision_id, policy_version = 1
FROM public.knowledge_source_revisions revision
WHERE revision.knowledge_source_id = ks.knowledge_source_id AND revision.is_legacy_snapshot;
