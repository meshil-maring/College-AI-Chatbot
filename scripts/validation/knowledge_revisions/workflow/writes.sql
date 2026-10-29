BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
GRANT USAGE ON SCHEMA knowledge_fixture TO service_role;
GRANT SELECT ON knowledge_fixture.ids TO service_role;
SELECT knowledge_fixture.assert_true('Shared uploads stay unpublished until review',
    NOT EXISTS(SELECT 1 FROM public.knowledge_sources WHERE title LIKE 'wf_%' AND published_revision_id IS NOT NULL)
    AND NOT EXISTS(SELECT 1 FROM public.document_versions v JOIN public.documents d USING(document_id)
        JOIN public.knowledge_sources s USING(knowledge_source_id) WHERE s.title LIKE 'wf_%' AND v.lifecycle_status <> 'draft'));
SELECT knowledge_fixture.reject('Staff cannot approve a revision', $q$
    SELECT public.decide_knowledge_revision(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('wf_public_revision'), 'approve', 1)
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Faculty cannot publish a revision', $q$
    SELECT public.decide_knowledge_revision(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('wf_public_revision'), 'publish', 1, 0)
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Other creators cannot edit a draft', $q$
    SELECT public.save_knowledge_draft(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('tenant'),
        '{"title":"Stolen"}', knowledge_fixture.id('wf_public'), knowledge_fixture.id('wf_public_revision'), 1)
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Stale draft save rejected', $q$
    SELECT public.save_knowledge_draft(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        '{"title":"Stale"}', knowledge_fixture.id('wf_public'), knowledge_fixture.id('wf_public_revision'), 1)
$q$, ARRAY['40001']);
SELECT knowledge_fixture.reject('Foreign institution cannot select a resource', $q$
    SELECT public.save_knowledge_draft(knowledge_fixture.id('tenant_actor'), knowledge_fixture.id('tenant'),
        '{}', knowledge_fixture.id('foreign'))
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.reject('Canonical FAQ cannot be used as a file-upload type', $q$
    SELECT public.save_knowledge_draft(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        '{"title":"Canonical bypass", "source_type":"faq", "visibility":"public"}')
$q$, ARRAY['22023']);

DO $$
DECLARE key text;
BEGIN
    FOREACH key IN ARRAY ARRAY['wf_public', 'wf_members', 'wf_students', 'wf_staff_only',
        'wf_faculty_only', 'wf_combined', 'wf_admins'] LOOP
        PERFORM knowledge_fixture.workflow_decide(key, 'submit');
        PERFORM knowledge_fixture.workflow_decide(key, 'approve');
        PERFORM knowledge_fixture.workflow_decide(key, 'publish');
    END LOOP;
END;
$$;
SET CONSTRAINTS ALL IMMEDIATE;
SET CONSTRAINTS ALL DEFERRED;
SELECT knowledge_fixture.assert_true('Admin publication atomically exposes exact reviewed versions',
    (SELECT count(*) = 7 FROM public.knowledge_sources WHERE title LIKE 'wf_%' AND published_revision_id IS NOT NULL)
    AND (SELECT count(*) = 7 FROM public.admin_audit_log WHERE action = 'knowledge.revision.publish'));
SELECT knowledge_fixture.assert_true('Publication records exact administrator provenance',
    NOT EXISTS(SELECT 1 FROM public.knowledge_source_revisions r JOIN public.knowledge_sources s USING(knowledge_source_id)
        WHERE s.title LIKE 'wf_%' AND (r.approved_by_user_id <> knowledge_fixture.id('tenant_actor') OR r.approved_at IS NULL)));
SELECT knowledge_fixture.reject('Legacy deletion is rejected before touching storage', $q$
    SELECT public.assert_legacy_knowledge_delete(knowledge_fixture.id('tenant_actor'), knowledge_fixture.id('tenant'), knowledge_fixture.id('wf_public'))
$q$, ARRAY['40001']);
SELECT knowledge_fixture.reject('Legacy chunking cannot purge reviewed evidence', $q$
    SET LOCAL ROLE service_role;
    DELETE FROM public.knowledge_chunks WHERE chunk_id = knowledge_fixture.id('wf_public_chunk')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Reviewed chunk text cannot be rewritten', $q$
    UPDATE public.knowledge_chunks SET content_text = 'Tampered evidence'
        WHERE chunk_id = knowledge_fixture.id('wf_public_chunk')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Reviewed embeddings cannot be removed', $q$
    DELETE FROM public.chunk_embeddings WHERE chunk_id = knowledge_fixture.id('wf_public_chunk')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.assert_true('Index-content guard is not a browser RPC',
    NOT has_function_privilege('anon', 'public.guard_knowledge_index_content()', 'EXECUTE')
    AND NOT has_function_privilege('service_role', 'public.guard_knowledge_index_content()', 'EXECUTE'));

-- Exercise trigger-owned indexing access under the real service role.
SELECT knowledge_fixture.workflow_resource('wf_indexing', 'restricted', '["student"]');
SET LOCAL ROLE service_role;
UPDATE public.document_versions SET extracted_text = 'Fictional draft text'
    WHERE document_version_id = knowledge_fixture.id('wf_indexing_version');
RESET ROLE;
SELECT knowledge_fixture.assert_true('Service can index draft content without table-write authority',
    (SELECT extracted_text = 'Fictional draft text' FROM public.document_versions
     WHERE document_version_id = knowledge_fixture.id('wf_indexing_version')));
SELECT knowledge_fixture.reject('An indexed draft is not indexed a second time', $q$
    SELECT public.retry_knowledge_index(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('wf_indexing_revision'),
        (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('wf_indexing_revision')),
        knowledge_fixture.id('wf_indexing_version'))
$q$, ARRAY['23514']);
UPDATE public.document_processing_runs SET embedding_status = 'failed', embedding_error = 'Fictional provider failure'
    WHERE processing_run_id = knowledge_fixture.id('wf_indexing_run');
SELECT knowledge_fixture.reject('Failed indexing cannot be submitted for review', $q$
    SELECT knowledge_fixture.workflow_decide('wf_indexing', 'submit')
$q$, ARRAY['23514']);
SELECT public.retry_knowledge_index(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
    knowledge_fixture.id('wf_indexing_revision'),
    (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('wf_indexing_revision')),
    knowledge_fixture.id('wf_indexing_version'));
SELECT knowledge_fixture.assert_true('Failed embedding can queue a draft retry',
    (SELECT count(*) = 2 FROM public.document_processing_runs WHERE document_version_id = knowledge_fixture.id('wf_indexing_version'))
    AND public.knowledge_revision_view(knowledge_fixture.id('wf_indexing_revision')) #>> '{documents,0,indexing_status}' = 'queued');
SELECT knowledge_fixture.reject('A queued retry cannot be duplicated', $q$
    SELECT public.retry_knowledge_index(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('wf_indexing_revision'),
        (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id('wf_indexing_revision')),
        knowledge_fixture.id('wf_indexing_version'))
$q$, ARRAY['23514']);

INSERT INTO public.knowledge_sources(institution_id, title, source_type, created_by_user_id)
    VALUES(knowledge_fixture.id('tenant'), 'Fictional legacy resource', 'handbook', knowledge_fixture.id('tenant_actor'));
SELECT knowledge_fixture.reject('Legacy resources still require creator ownership', $q$
    SELECT public.save_knowledge_draft(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), '{}',
        (SELECT knowledge_source_id FROM public.knowledge_sources WHERE title = 'Fictional legacy resource'))
$q$, ARRAY['42501']);

CREATE FUNCTION knowledge_fixture.fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.record_data #>> '{after,title}' = 'Fictional audit rollback' THEN RAISE EXCEPTION 'Fictional audit failure'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER audit_failure BEFORE INSERT ON public.admin_audit_log
    FOR EACH ROW EXECUTE FUNCTION knowledge_fixture.fail_audit();
SELECT knowledge_fixture.reject('An audit failure aborts the resource transaction', $q$
    SELECT public.save_knowledge_draft(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        '{"title":"Fictional audit rollback","source_type":"handbook"}')
$q$, ARRAY['P0001']);
SELECT knowledge_fixture.assert_true('Audit rollback leaves no partially saved source',
    NOT EXISTS(SELECT 1 FROM public.knowledge_sources WHERE title = 'Fictional audit rollback'));
DROP TRIGGER audit_failure ON public.admin_audit_log;
COMMIT;
