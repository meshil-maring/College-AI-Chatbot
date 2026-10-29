CREATE FUNCTION public.snapshot_public_knowledge_policy(institution_code text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE tenant uuid; fingerprint text; enabled boolean;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE = '42501';
    END IF;
    SELECT i.institution_id, i.is_active AND i.status = 'active' AND o.status = 'active' INTO tenant, enabled
        FROM public.institutions i
        JOIN public.organizations o USING(organization_id)
        WHERE i.code = upper(btrim(institution_code));
    IF tenant IS NULL THEN RAISE EXCEPTION 'Institution unavailable' USING ERRCODE = 'P0002'; END IF;
    SELECT md5(COALESCE(string_agg(s.knowledge_source_id::text || ':' || s.policy_version::text || ':' ||
        v.document_version_id::text, ',' ORDER BY s.knowledge_source_id, v.document_version_id), '')) INTO fingerprint
    FROM public.knowledge_sources s JOIN public.documents d USING(knowledge_source_id)
    JOIN public.document_versions v USING(document_id)
    WHERE s.institution_id = tenant AND public.knowledge_source_allowed(NULL, tenant, s.knowledge_source_id)
        AND public.knowledge_version_allowed(s.knowledge_source_id, v.document_version_id);
    RETURN jsonb_build_object('institution_id', tenant, 'enabled', enabled, 'fingerprint', fingerprint);
END;
$$;

CREATE FUNCTION public.assert_legacy_knowledge_delete(actor uuid, tenant uuid, source_id uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.assert_knowledge_actor(actor, tenant, 'documents.delete', true);
    IF NOT EXISTS(SELECT 1 FROM public.knowledge_sources s WHERE s.knowledge_source_id = source_id AND s.institution_id = tenant) THEN
        RAISE EXCEPTION 'Resource not found' USING ERRCODE = 'P0002';
    END IF;
    IF EXISTS(SELECT 1 FROM public.knowledge_source_revisions r WHERE r.knowledge_source_id = source_id) THEN
        RAISE EXCEPTION 'Revision-managed documents must be removed through a reviewed manifest' USING ERRCODE = '40001';
    END IF;
END;
$$;
