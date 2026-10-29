-- Separate statements commit as the real PostgREST role. Deferred checks must
-- retain access to their private helpers after the writer's context ends.
SELECT knowledge_fixture.id('tenant_actor') AS service_actor,
    knowledge_fixture.id('tenant') AS service_tenant \gset
SET request.jwt.claim.role = 'service_role';
SET ROLE service_role;
WITH draft AS (
    SELECT public.save_knowledge_draft(:'service_actor', :'service_tenant',
        '{"title":"Fictional service commit","source_type":"handbook","visibility":"public"}') AS data
)
SELECT data->>'revision_id' AS service_revision,
    data->>'knowledge_source_id' AS service_source FROM draft \gset
WITH receipt AS (
    SELECT public.register_knowledge_upload(:'service_actor', :'service_tenant', :'service_revision',
        (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = :'service_revision'),
        '{"original_filename":"service.txt","file_type":"txt","mime_type":"text/plain", "file_size_bytes":42,
          "storage_bucket":"fictional","storage_object_key":"service-commit.txt"}') AS data
)
SELECT data->>'processing_run_id' AS service_run FROM receipt \gset
UPDATE public.document_processing_runs SET status = 'ready', embedding_status = 'embedded', completed_at = now()
    WHERE processing_run_id = :'service_run';
WITH chunk AS (
    INSERT INTO public.knowledge_chunks(processing_run_id, chunk_sequence, content_text)
        VALUES(:'service_run', 1, 'Fictional committed service content') RETURNING chunk_id
)
INSERT INTO public.chunk_embeddings(chunk_id, model_name, embedding_dimensions, embedding)
    SELECT chunk_id, 'fictional-model', 1536, ('[1,' || repeat('0,', 1534) || '0]')::extensions.vector FROM chunk;
SELECT public.decide_knowledge_revision(:'service_actor', :'service_tenant', :'service_revision', 'submit',
    (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = :'service_revision'));
SELECT public.decide_knowledge_revision(:'service_actor', :'service_tenant', :'service_revision', 'approve',
    (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = :'service_revision'));
SELECT public.decide_knowledge_revision(:'service_actor', :'service_tenant', :'service_revision', 'publish',
    (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = :'service_revision'),
    (SELECT policy_version FROM public.knowledge_sources WHERE knowledge_source_id = :'service_source'));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Service-role commits preserve private deferred integrity checks',
    (SELECT published_revision_id = :'service_revision' AND lifecycle_status = 'published'
     FROM public.knowledge_sources WHERE knowledge_source_id = :'service_source')
    AND NOT has_function_privilege('service_role', 'public.assert_knowledge_revision_integrity(uuid)', 'EXECUTE'));
SET ROLE service_role;
SELECT public.decide_knowledge_revision(:'service_actor', :'service_tenant', :'service_revision', 'unpublish',
    (SELECT revision_version FROM public.knowledge_source_revisions WHERE revision_id = :'service_revision'),
    (SELECT policy_version FROM public.knowledge_sources WHERE knowledge_source_id = :'service_source'));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Service-role unpublish commits with its deferred checks',
    (SELECT published_revision_id IS NULL FROM public.knowledge_sources WHERE knowledge_source_id = :'service_source'));
