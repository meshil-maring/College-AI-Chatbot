CREATE FUNCTION public.assert_knowledge_revision_integrity(p_revision_id uuid)
RETURNS void LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE revision public.knowledge_source_revisions; target_count integer;
BEGIN
    SELECT * INTO revision FROM public.knowledge_source_revisions WHERE revision_id = p_revision_id;
    IF NOT FOUND THEN RETURN; END IF;
    IF revision.lifecycle_status <> 'published' AND EXISTS (
        SELECT 1 FROM public.knowledge_sources source
        WHERE source.published_revision_id = p_revision_id
    ) THEN
        RAISE EXCEPTION 'Only a published revision can be the live revision' USING ERRCODE = '23514';
    END IF;
    SELECT count(*) INTO target_count FROM public.knowledge_source_revision_audiences
        WHERE revision_id = p_revision_id;
    IF revision.visibility <> 'restricted' AND target_count <> 0 THEN
        RAISE EXCEPTION 'Public and institution audiences cannot have role targets' USING ERRCODE = '23514';
    END IF;
    IF revision.lifecycle_status IN ('under_review', 'approved', 'published') THEN
        IF revision.visibility = 'restricted' AND target_count = 0 THEN
            RAISE EXCEPTION 'Selected-role audience must not be empty' USING ERRCODE = '23514';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM public.knowledge_source_revision_documents
                       WHERE revision_id = p_revision_id) THEN
            RAISE EXCEPTION 'Submitted revisions require a file manifest' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF revision.lifecycle_status = 'published' THEN
        IF EXISTS (
            SELECT 1 FROM public.knowledge_source_revision_documents manifest
            JOIN public.document_versions version USING (document_version_id)
            WHERE manifest.revision_id = p_revision_id AND (
                version.lifecycle_status <> 'published' OR NOT EXISTS (
                    SELECT 1 FROM public.document_processing_runs run
                    WHERE run.document_version_id = version.document_version_id
                        AND run.status = 'ready' AND run.embedding_status = 'embedded'
                        AND run.completed_at IS NOT NULL
                )
            )
        ) THEN
            RAISE EXCEPTION 'Published manifest requires published, indexed versions' USING ERRCODE = '23514';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM public.knowledge_sources source
                       WHERE source.knowledge_source_id = revision.knowledge_source_id
                           AND source.published_revision_id = p_revision_id) THEN
            RAISE EXCEPTION 'Published revision must be the source live revision' USING ERRCODE = '23514';
        END IF;
    END IF;
END;
$$;

CREATE FUNCTION public.check_knowledge_revision_integrity() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF TG_OP <> 'INSERT' THEN
        PERFORM public.assert_knowledge_revision_integrity(OLD.revision_id);
    END IF;
    IF TG_OP <> 'DELETE' THEN
        PERFORM public.assert_knowledge_revision_integrity(NEW.revision_id);
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER knowledge_revision_integrity
AFTER INSERT OR UPDATE ON public.knowledge_source_revisions
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION public.check_knowledge_revision_integrity();
CREATE CONSTRAINT TRIGGER knowledge_audience_integrity
AFTER INSERT OR UPDATE OR DELETE ON public.knowledge_source_revision_audiences
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION public.check_knowledge_revision_integrity();
CREATE CONSTRAINT TRIGGER knowledge_manifest_integrity
AFTER INSERT OR UPDATE OR DELETE ON public.knowledge_source_revision_documents
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION public.check_knowledge_revision_integrity();
