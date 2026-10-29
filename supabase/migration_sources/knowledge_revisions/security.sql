DO $$
DECLARE relation_name text; revision_id uuid;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'knowledge_source_revisions', 'knowledge_source_revision_audiences',
        'knowledge_source_revision_documents'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres', relation_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role', relation_name);
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', relation_name);
    END LOOP;
    -- Bootstrap rows predate the triggers: verify them before committing.
    FOR revision_id IN SELECT r.revision_id FROM public.knowledge_source_revisions r LOOP
        PERFORM public.assert_knowledge_revision_integrity(revision_id);
    END LOOP;
END;
$$;

REVOKE ALL ON FUNCTION public.guard_knowledge_revision(),
    public.guard_knowledge_revision_member(), public.assert_knowledge_revision_integrity(uuid),
    public.check_knowledge_revision_integrity(), public.guard_knowledge_source_policy(),
    public.check_knowledge_source_revision(), public.guard_knowledge_manifest_version(),
    public.check_knowledge_manifest_version(), public.guard_knowledge_manifest_run(),
    public.check_knowledge_manifest_run()
    FROM PUBLIC, anon, authenticated, service_role;

COMMENT ON TABLE public.knowledge_source_revisions IS
    'Reviewed audience and exact file manifest; mutations use authorized, audited backend RPCs.';
