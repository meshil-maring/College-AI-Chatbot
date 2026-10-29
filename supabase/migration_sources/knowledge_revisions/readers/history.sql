ALTER TABLE public.messages ADD COLUMN knowledge_policy jsonb;

CREATE FUNCTION public.guard_message_knowledge_policy() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF NEW.knowledge_policy IS NOT NULL AND current_user NOT IN ('postgres', 'service_role') THEN
        RAISE EXCEPTION 'Knowledge provenance is backend-owned' USING ERRCODE = '42501';
    END IF;
    IF TG_OP = 'UPDATE' AND NEW.content_text IS DISTINCT FROM OLD.content_text THEN NEW.knowledge_policy := NULL; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER message_knowledge_policy_guard BEFORE INSERT OR UPDATE ON public.messages
FOR EACH ROW EXECUTE FUNCTION public.guard_message_knowledge_policy();

CREATE FUNCTION public.check_knowledge_policy(actor uuid, policy jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE tenant uuid; source_id text; version text; version_id text;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE = '42501';
    END IF;
    IF policy IS NULL OR jsonb_typeof(policy) <> 'object'
        OR jsonb_typeof(policy->'sources') IS DISTINCT FROM 'object'
        OR jsonb_typeof(policy->'versions') IS DISTINCT FROM 'object' THEN RETURN false; END IF;
    tenant := (policy->>'institution_id')::uuid;
    IF tenant IS NULL THEN RETURN false; END IF;
    IF actor IS NOT NULL AND cardinality(public.knowledge_actor_roles(actor, tenant, 'ai.chat')) = 0 THEN RETURN false; END IF;
    FOR source_id, version IN SELECT * FROM jsonb_each_text(policy->'sources') LOOP
        IF NOT EXISTS(SELECT 1 FROM public.knowledge_sources s
            WHERE s.knowledge_source_id = source_id::uuid AND s.policy_version::text = version
                AND public.knowledge_source_allowed(actor, tenant, s.knowledge_source_id)) THEN RETURN false; END IF;
    END LOOP;
    FOR version_id, source_id IN SELECT * FROM jsonb_each_text(policy->'versions') LOOP
        IF NOT policy->'sources' ? source_id
            OR NOT public.knowledge_version_allowed(source_id::uuid, version_id::uuid) THEN RETURN false; END IF;
    END LOOP;
    RETURN true;
EXCEPTION WHEN invalid_text_representation THEN RETURN false;
END;
$$;

CREATE FUNCTION public.snapshot_knowledge_policy(actor uuid, tenant uuid, chunks uuid[], inherited jsonb DEFAULT '{}')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE sources jsonb; versions jsonb; matched integer; result jsonb;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE = '42501';
    END IF;
    SELECT count(DISTINCT c.chunk_id), COALESCE(jsonb_object_agg(s.knowledge_source_id::text, s.policy_version), '{}'),
        COALESCE(jsonb_object_agg(v.document_version_id::text, s.knowledge_source_id::text), '{}')
    INTO matched, sources, versions FROM public.knowledge_chunks c
    JOIN public.document_processing_runs run USING(processing_run_id)
    JOIN public.document_versions v USING(document_version_id)
    JOIN public.documents d USING(document_id)
    JOIN public.knowledge_sources s USING(knowledge_source_id)
    WHERE c.chunk_id = ANY(chunks) AND s.institution_id = tenant
        AND run.status = 'ready' AND run.embedding_status = 'embedded' AND run.completed_at IS NOT NULL
        AND public.knowledge_source_allowed(actor, tenant, s.knowledge_source_id)
        AND public.knowledge_version_allowed(s.knowledge_source_id, v.document_version_id);
    IF matched <> (SELECT count(DISTINCT id) FROM unnest(chunks) id) THEN
        RAISE EXCEPTION 'Knowledge access changed' USING ERRCODE = '40001';
    END IF;
    result := jsonb_build_object('institution_id', tenant,
        'sources', COALESCE(inherited->'sources', '{}') || sources,
        'versions', COALESCE(inherited->'versions', '{}') || versions);
    IF NOT public.check_knowledge_policy(actor, result) THEN
        RAISE EXCEPTION 'Knowledge access changed' USING ERRCODE = '40001';
    END IF;
    RETURN result;
END;
$$;
