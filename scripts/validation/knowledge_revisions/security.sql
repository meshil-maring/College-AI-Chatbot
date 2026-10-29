BEGIN;
SELECT knowledge_fixture.assert_true('All revision tables have RLS',
    (SELECT count(*) = 3 AND bool_and(relrowsecurity) FROM pg_class
     WHERE oid IN ('public.knowledge_source_revisions'::regclass,
                   'public.knowledge_source_revision_audiences'::regclass,
                   'public.knowledge_source_revision_documents'::regclass)));
SELECT knowledge_fixture.assert_true('Browser roles cannot read or write revision tables',
    NOT EXISTS (
        SELECT 1 FROM unnest(ARRAY['anon', 'authenticated']) actor
        CROSS JOIN unnest(ARRAY['knowledge_source_revisions', 'knowledge_source_revision_audiences',
                                'knowledge_source_revision_documents']) relation
        WHERE has_table_privilege(actor, 'public.' || relation, 'SELECT')
            OR has_table_privilege(actor, 'public.' || relation, 'INSERT,UPDATE,DELETE,TRUNCATE')
    ));
SELECT knowledge_fixture.assert_true('Trusted backend can read but cannot enable publication yet',
    NOT EXISTS (
        SELECT 1 FROM unnest(ARRAY['knowledge_source_revisions', 'knowledge_source_revision_audiences',
                                  'knowledge_source_revision_documents']) relation
        WHERE NOT has_table_privilege('service_role', 'public.' || relation, 'SELECT')
            OR has_table_privilege('service_role', 'public.' || relation, 'INSERT,UPDATE,DELETE,TRUNCATE')
    ));

-- Exercise real roles as well as catalogue grants. Constants avoid granting
-- fixture schema access to the browser roles just to run their probes.
SELECT knowledge_fixture.reject('Anonymous direct table read denied', $q$
    SET LOCAL ROLE anon;
    SELECT * FROM public.knowledge_source_revisions
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Authenticated direct table read denied', $q$
    SET LOCAL ROLE authenticated;
    SELECT * FROM public.knowledge_source_revision_audiences
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Service direct publication denied', $q$
    SET LOCAL ROLE service_role;
    UPDATE public.knowledge_source_revisions SET lifecycle_status = 'published'
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Service cannot rewrite a live policy through old table grants', $q$
    SET LOCAL ROLE service_role;
    UPDATE public.knowledge_sources SET visibility = 'public' WHERE title = 'candidate'
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Service cannot clear the live pointer', $q$
    SET LOCAL ROLE service_role;
    UPDATE public.knowledge_sources SET published_revision_id = NULL WHERE title = 'candidate'
$q$, ARRAY['42501']);
SELECT knowledge_fixture.assert_true('Helper execution is not a browser or service capability',
    NOT has_function_privilege('anon', 'public.assert_knowledge_revision_integrity(uuid)', 'EXECUTE')
    AND NOT has_function_privilege('authenticated', 'public.guard_knowledge_source_policy()', 'EXECUTE')
    AND NOT has_function_privilege('service_role', 'public.assert_knowledge_revision_integrity(uuid)', 'EXECUTE'));
SET LOCAL ROLE service_role;
SELECT count(*) FROM public.knowledge_source_revisions;
SELECT count(*) FROM public.knowledge_source_revision_audiences;
SELECT count(*) FROM public.knowledge_source_revision_documents;
RESET ROLE;
COMMIT;
