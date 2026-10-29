-- Legacy processing endpoints also write these tables. Freeze derived evidence
-- with its reviewed manifest, and serialize draft index changes against review.
CREATE FUNCTION public.guard_knowledge_index_content() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE data jsonb; parent_column text; parent_id uuid; run_id uuid; version_id uuid;
    target_revision_id uuid; revision_status text;
BEGIN
    data := CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
    parent_column := CASE WHEN TG_TABLE_NAME = 'knowledge_chunks' THEN 'processing_run_id' ELSE 'chunk_id' END;
    IF TG_OP = 'UPDATE' AND data->parent_column IS DISTINCT FROM to_jsonb(OLD)->parent_column THEN
        RAISE EXCEPTION 'Indexed evidence cannot be moved' USING ERRCODE = '23514';
    END IF;
    parent_id := (data->>parent_column)::uuid;
    IF TG_TABLE_NAME = 'knowledge_chunks' THEN
        run_id := parent_id;
    ELSE
        SELECT c.processing_run_id INTO run_id FROM public.knowledge_chunks c WHERE c.chunk_id = parent_id;
    END IF;
    SELECT run.document_version_id INTO version_id FROM public.document_processing_runs run WHERE run.processing_run_id = run_id;
    FOR target_revision_id, revision_status IN
        SELECT r.revision_id, r.lifecycle_status FROM public.knowledge_source_revisions r
        JOIN public.knowledge_source_revision_documents m USING(revision_id)
        WHERE m.document_version_id = version_id ORDER BY r.revision_id FOR UPDATE OF r
    LOOP
        IF revision_status <> 'draft' THEN
            RAISE EXCEPTION 'Reviewed indexed evidence is immutable' USING ERRCODE = '23514';
        END IF;
        UPDATE public.knowledge_source_revisions SET updated_at = clock_timestamp()
            WHERE revision_id = target_revision_id;
    END LOOP;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER knowledge_chunk_revision_guard BEFORE INSERT OR UPDATE OR DELETE ON public.knowledge_chunks
    FOR EACH ROW EXECUTE FUNCTION public.guard_knowledge_index_content();
CREATE TRIGGER knowledge_embedding_revision_guard BEFORE INSERT OR UPDATE OR DELETE ON public.chunk_embeddings
    FOR EACH ROW EXECUTE FUNCTION public.guard_knowledge_index_content();
