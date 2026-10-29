CREATE FUNCTION public.guard_knowledge_revision_member() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE parent_id uuid; parent_status text;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.revision_id IS DISTINCT FROM OLD.revision_id THEN
        RAISE EXCEPTION 'Revision members cannot be moved' USING ERRCODE = '23514';
    END IF;
    parent_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.revision_id ELSE NEW.revision_id END;
    -- Serialize child changes against review/publication and advance the same
    -- concurrency token as parent edits. A stale approval cannot ignore a file
    -- or audience edit made by a concurrent transaction.
    SELECT lifecycle_status INTO parent_status
    FROM public.knowledge_source_revisions WHERE revision_id = parent_id FOR UPDATE;
    IF NOT FOUND AND TG_OP = 'DELETE' THEN
        RETURN OLD; -- A permitted draft-parent deletion cascades its members.
    END IF;
    IF parent_status IS DISTINCT FROM 'draft' THEN
        RAISE EXCEPTION 'Only draft audiences and file manifests can change' USING ERRCODE = '23514';
    END IF;
    UPDATE public.knowledge_source_revisions
        SET updated_at = clock_timestamp() WHERE revision_id = parent_id;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER knowledge_audience_guard
BEFORE INSERT OR UPDATE OR DELETE ON public.knowledge_source_revision_audiences
FOR EACH ROW EXECUTE FUNCTION public.guard_knowledge_revision_member();
CREATE TRIGGER knowledge_manifest_guard
BEFORE INSERT OR UPDATE OR DELETE ON public.knowledge_source_revision_documents
FOR EACH ROW EXECUTE FUNCTION public.guard_knowledge_revision_member();
