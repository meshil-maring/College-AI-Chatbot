CREATE FUNCTION public.guard_knowledge_source_policy() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.published_revision_id IS NOT NULL OR NEW.policy_version <> 0 THEN
            RAISE EXCEPTION 'Sources start without a published revision' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.policy_version IS DISTINCT FROM OLD.policy_version THEN
        RAISE EXCEPTION 'Source policy version is server-maintained' USING ERRCODE = '23514';
    END IF;
    IF ROW(NEW.published_revision_id, NEW.visibility, NEW.lifecycle_status,
           NEW.effective_from, NEW.effective_until)
        IS DISTINCT FROM ROW(OLD.published_revision_id, OLD.visibility, OLD.lifecycle_status,
           OLD.effective_from, OLD.effective_until) THEN
        NEW.policy_version := OLD.policy_version + 1;
    END IF;
    -- Only the audited SECURITY DEFINER writer may switch a live policy.
    IF current_user <> 'postgres' AND (
        NEW.published_revision_id IS DISTINCT FROM OLD.published_revision_id
        OR ((OLD.published_revision_id IS NOT NULL OR NEW.published_revision_id IS NOT NULL)
            AND (to_jsonb(NEW) - ARRAY['updated_at', 'policy_version'])
                IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['updated_at', 'policy_version']))
    ) THEN
        RAISE EXCEPTION 'Revision-managed sources require the authorized writer' USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION public.check_knowledge_source_revision() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE source public.knowledge_sources; revision public.knowledge_source_revisions;
BEGIN
    SELECT * INTO source FROM public.knowledge_sources WHERE knowledge_source_id = NEW.knowledge_source_id;
    IF NOT FOUND THEN RETURN NULL; END IF;
    IF source.published_revision_id IS NULL THEN
        IF EXISTS (SELECT 1 FROM public.knowledge_source_revisions r
                   WHERE r.knowledge_source_id = source.knowledge_source_id AND r.lifecycle_status = 'published') THEN
            RAISE EXCEPTION 'Unpublishing must retire the live revision atomically' USING ERRCODE = '23514';
        END IF;
        RETURN NULL;
    END IF;
    SELECT * INTO revision FROM public.knowledge_source_revisions
        WHERE revision_id = source.published_revision_id;
    IF NOT FOUND OR revision.lifecycle_status <> 'published' OR source.lifecycle_status <> 'published'
        OR ROW(source.institution_id, source.knowledge_source_id, source.title, source.description,
               source.source_type, source.authority_level, source.visibility,
               source.effective_from, source.effective_until)
            IS DISTINCT FROM
            ROW(revision.institution_id, revision.knowledge_source_id, revision.title, revision.description,
               revision.source_type, revision.authority_level, revision.visibility,
               revision.effective_from, revision.effective_until) THEN
        RAISE EXCEPTION 'Live source must match its published revision' USING ERRCODE = '23514';
    END IF;
    PERFORM public.assert_knowledge_revision_integrity(revision.revision_id);
    RETURN NULL;
END;
$$;

CREATE FUNCTION public.guard_knowledge_manifest_version() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE parent_id uuid; parent_status text; content_changed boolean;
BEGIN
    content_changed := (to_jsonb(NEW) - ARRAY['lifecycle_status', 'updated_at', 'reviewed_by_user_id', 'approved_by_user_id'])
        IS DISTINCT FROM
        (to_jsonb(OLD) - ARRAY['lifecycle_status', 'updated_at', 'reviewed_by_user_id', 'approved_by_user_id']);
    FOR parent_id, parent_status IN
        SELECT revision.revision_id, revision.lifecycle_status
        FROM public.knowledge_source_revisions revision
        JOIN public.knowledge_source_revision_documents manifest USING (revision_id)
        WHERE manifest.document_version_id = OLD.document_version_id
        ORDER BY revision.revision_id FOR UPDATE OF revision
    LOOP
        IF content_changed AND parent_status <> 'draft' THEN
            RAISE EXCEPTION 'Reviewed file versions are immutable' USING ERRCODE = '23514';
        END IF;
        IF content_changed THEN
            UPDATE public.knowledge_source_revisions SET updated_at = clock_timestamp()
                WHERE revision_id = parent_id;
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE FUNCTION public.check_knowledge_manifest_version() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE parent_id uuid;
BEGIN
    FOR parent_id IN SELECT revision_id FROM public.knowledge_source_revision_documents
        WHERE document_version_id = NEW.document_version_id LOOP
        PERFORM public.assert_knowledge_revision_integrity(parent_id);
    END LOOP;
    RETURN NULL;
END;
$$;

CREATE TRIGGER knowledge_source_policy_guard
BEFORE INSERT OR UPDATE ON public.knowledge_sources
FOR EACH ROW EXECUTE FUNCTION public.guard_knowledge_source_policy();
CREATE CONSTRAINT TRIGGER knowledge_source_revision_integrity
AFTER INSERT OR UPDATE ON public.knowledge_sources
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.check_knowledge_source_revision();
CREATE TRIGGER knowledge_manifest_version_guard
BEFORE UPDATE ON public.document_versions
FOR EACH ROW EXECUTE FUNCTION public.guard_knowledge_manifest_version();
CREATE CONSTRAINT TRIGGER knowledge_manifest_version_integrity
AFTER UPDATE ON public.document_versions
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.check_knowledge_manifest_version();

CREATE FUNCTION public.guard_knowledge_manifest_run() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE version_id uuid; parent_id uuid; parent_status text;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.document_version_id IS DISTINCT FROM OLD.document_version_id THEN
        RAISE EXCEPTION 'Processing run version identity is immutable' USING ERRCODE = '23514';
    END IF;
    version_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.document_version_id ELSE NEW.document_version_id END;
    FOR parent_id, parent_status IN
        SELECT revision.revision_id, revision.lifecycle_status FROM public.knowledge_source_revisions revision
        JOIN public.knowledge_source_revision_documents manifest USING (revision_id)
        WHERE manifest.document_version_id = version_id
        ORDER BY revision.revision_id FOR UPDATE OF revision
    LOOP
        IF parent_status <> 'draft' THEN
            RAISE EXCEPTION 'Reviewed indexing runs are immutable' USING ERRCODE = '23514';
        END IF;
        UPDATE public.knowledge_source_revisions SET updated_at = clock_timestamp() WHERE revision_id = parent_id;
    END LOOP;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION public.check_knowledge_manifest_run() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE version_id uuid; parent_id uuid;
BEGIN
    version_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.document_version_id ELSE NEW.document_version_id END;
    FOR parent_id IN SELECT revision_id FROM public.knowledge_source_revision_documents
        WHERE document_version_id = version_id LOOP
        PERFORM public.assert_knowledge_revision_integrity(parent_id);
    END LOOP;
    RETURN NULL;
END;
$$;

CREATE TRIGGER knowledge_manifest_run_guard
BEFORE INSERT OR UPDATE OR DELETE ON public.document_processing_runs
FOR EACH ROW EXECUTE FUNCTION public.guard_knowledge_manifest_run();
CREATE CONSTRAINT TRIGGER knowledge_manifest_run_integrity
AFTER INSERT OR UPDATE OR DELETE ON public.document_processing_runs
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.check_knowledge_manifest_run();
