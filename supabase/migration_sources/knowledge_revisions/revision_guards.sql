CREATE FUNCTION public.guard_knowledge_revision() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE mutable_state text[] := ARRAY[
    'lifecycle_status', 'revision_version', 'updated_at', 'reviewed_by_user_id',
    'approved_by_user_id', 'review_notes', 'submitted_at', 'reviewed_at',
    'approved_at', 'published_at'
];
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.lifecycle_status <> 'draft' OR NEW.is_legacy_snapshot
            OR NEW.revision_version <> 1 THEN
            RAISE EXCEPTION 'New revisions start as private drafts' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF OLD.lifecycle_status IN ('published', 'archived', 'superseded') THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Published revision history cannot be deleted' USING ERRCODE = '23514';
        END IF;
        IF (to_jsonb(NEW) - ARRAY['lifecycle_status', 'revision_version', 'updated_at'])
            IS DISTINCT FROM
            (to_jsonb(OLD) - ARRAY['lifecycle_status', 'revision_version', 'updated_at']) THEN
            RAISE EXCEPTION 'Published revision content is immutable' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.lifecycle_status <> 'draft' THEN
            RAISE EXCEPTION 'Only draft revisions can be deleted' USING ERRCODE = '23514';
        END IF;
        RETURN OLD;
    END IF;
    IF ROW(NEW.revision_id, NEW.knowledge_source_id, NEW.institution_id,
           NEW.revision_number, NEW.created_by_user_id, NEW.created_at, NEW.is_legacy_snapshot)
        IS DISTINCT FROM ROW(OLD.revision_id, OLD.knowledge_source_id, OLD.institution_id,
           OLD.revision_number, OLD.created_by_user_id, OLD.created_at, OLD.is_legacy_snapshot) THEN
        RAISE EXCEPTION 'Revision identity and provenance are immutable' USING ERRCODE = '23514';
    END IF;
    IF OLD.lifecycle_status <> 'draft'
        AND (to_jsonb(NEW) - mutable_state) IS DISTINCT FROM (to_jsonb(OLD) - mutable_state) THEN
        RAISE EXCEPTION 'Return a revision to draft before editing content' USING ERRCODE = '23514';
    END IF;
    IF NEW.lifecycle_status <> OLD.lifecycle_status AND NOT (
        (OLD.lifecycle_status = 'draft' AND NEW.lifecycle_status = 'under_review')
        OR (OLD.lifecycle_status = 'under_review' AND NEW.lifecycle_status IN ('draft', 'approved'))
        OR (OLD.lifecycle_status = 'approved' AND NEW.lifecycle_status IN ('draft', 'published'))
        OR (OLD.lifecycle_status = 'published' AND NEW.lifecycle_status IN ('archived', 'superseded'))
    ) THEN
        RAISE EXCEPTION 'Invalid revision lifecycle transition' USING ERRCODE = '23514';
    END IF;
    IF NEW.lifecycle_status = 'draft' THEN
        NEW.reviewed_by_user_id := NULL;
        NEW.approved_by_user_id := NULL;
        NEW.reviewed_at := NULL;
        NEW.approved_at := NULL;
        NEW.published_at := NULL;
        NEW.submitted_at := NULL;
    END IF;
    NEW.revision_version := OLD.revision_version + 1;
    NEW.updated_at := clock_timestamp();
    RETURN NEW;
END;
$$;

CREATE TRIGGER knowledge_revision_guard
BEFORE INSERT OR UPDATE OR DELETE ON public.knowledge_source_revisions
FOR EACH ROW EXECUTE FUNCTION public.guard_knowledge_revision();
