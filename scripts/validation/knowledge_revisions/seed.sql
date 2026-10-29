-- Fictional metadata only; no real files, accounts or external database access.
CREATE SCHEMA knowledge_fixture;
CREATE TABLE knowledge_fixture.ids (name text PRIMARY KEY, value uuid NOT NULL);
CREATE TABLE knowledge_fixture.results (name text PRIMARY KEY, passed boolean NOT NULL CHECK (passed));
CREATE FUNCTION knowledge_fixture.id(key text) RETURNS uuid LANGUAGE sql STABLE
AS $$ SELECT value FROM knowledge_fixture.ids WHERE name = key $$;

DO $$
DECLARE org uuid; tenant uuid; actor uuid; auth_id uuid; label text;
BEGIN
    SELECT organization_id INTO STRICT org FROM public.organizations
        WHERE organization_code = 'COLLEGE-AI-PLATFORM';
    FOREACH label IN ARRAY ARRAY['tenant', 'foreign_tenant'] LOOP
        tenant := gen_random_uuid(); actor := gen_random_uuid(); auth_id := gen_random_uuid();
        INSERT INTO public.institutions(institution_id, organization_id, name, code, status)
            VALUES (tenant, org, 'Fictional Knowledge College', label || '-KNOWLEDGE-TEST', 'active');
        INSERT INTO auth.users(id, email) VALUES (auth_id, label || '@example.invalid');
        INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
            VALUES (actor, auth_id, label || '@example.invalid', 'Fictional', 'Administrator');
        INSERT INTO public.user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
            SELECT actor, id, 'institution', tenant, org FROM public.roles WHERE name = 'admin';
        INSERT INTO knowledge_fixture.ids VALUES (label, tenant), (label || '_actor', actor);
    END LOOP;
END;
$$;

CREATE FUNCTION knowledge_fixture.resource(
    key text, audience text DEFAULT 'public', state text DEFAULT 'published',
    variant text DEFAULT 'ready', tenant_key text DEFAULT 'tenant'
) RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE source_id uuid := gen_random_uuid(); doc_id uuid := gen_random_uuid();
    version_id uuid := gen_random_uuid(); actor uuid := knowledge_fixture.id(tenant_key || '_actor');
BEGIN
    INSERT INTO public.knowledge_sources (
        knowledge_source_id, institution_id, title, source_type, visibility,
        lifecycle_status, created_by_user_id, effective_from, effective_until
    ) VALUES (source_id, knowledge_fixture.id(tenant_key), key, 'handbook', audience,
        state, actor, CASE WHEN variant = 'future' THEN CURRENT_DATE + 30 END,
        CASE WHEN variant = 'expired' THEN CURRENT_DATE - 1 END);
    INSERT INTO public.documents(document_id, knowledge_source_id) VALUES (doc_id, source_id);
    INSERT INTO public.document_versions (
        document_version_id, document_id, version_number, original_filename, file_type,
        storage_provider, storage_bucket, storage_object_key, lifecycle_status, created_by_user_id
    ) VALUES (version_id, doc_id, 1, key || '.pdf', 'pdf', 'r2', 'fictional', key,
        CASE WHEN variant = 'draft_file' THEN 'draft' ELSE 'published' END, actor);
    INSERT INTO public.document_processing_runs (
        document_version_id, status, embedding_status, completed_at, error_message
    ) VALUES (version_id, CASE WHEN variant = 'failed' THEN 'failed' ELSE 'ready' END,
        CASE WHEN variant = 'incomplete' THEN 'processing' ELSE 'embedded' END,
        CASE WHEN variant <> 'unfinished' THEN now() END,
        CASE WHEN variant = 'failed' THEN 'Fictional extraction failure' END);
    INSERT INTO knowledge_fixture.ids VALUES
        (key, source_id), (key || '_document', doc_id), (key || '_version', version_id);
    RETURN source_id;
END;
$$;

SELECT knowledge_fixture.resource('public');
SELECT knowledge_fixture.resource('institution', 'authenticated');
SELECT knowledge_fixture.resource('restricted', 'restricted');
SELECT knowledge_fixture.resource('draft', 'public', 'draft');
SELECT knowledge_fixture.resource('expired', 'public', 'published', 'expired');
SELECT knowledge_fixture.resource('future', 'public', 'published', 'future');
SELECT knowledge_fixture.resource('failed', 'public', 'published', 'failed');
SELECT knowledge_fixture.resource('incomplete', 'public', 'published', 'incomplete');
SELECT knowledge_fixture.resource('unfinished', 'public', 'published', 'unfinished');
SELECT knowledge_fixture.resource('draft_file', 'public', 'published', 'draft_file');
SELECT knowledge_fixture.resource('foreign', 'public', 'published', 'ready', 'foreign_tenant');

INSERT INTO public.document_versions (
    document_version_id, document_id, version_number, original_filename, file_type,
    storage_provider, storage_bucket, storage_object_key, lifecycle_status, created_by_user_id
) SELECT gen_random_uuid(), knowledge_fixture.id('public_document'), 2, 'latest.pdf',
    'pdf', 'r2', 'fictional', 'latest', 'published', knowledge_fixture.id('tenant_actor')
RETURNING document_version_id AS latest_version \gset
INSERT INTO knowledge_fixture.ids VALUES ('public_latest', :'latest_version');
INSERT INTO public.document_processing_runs(document_version_id, status, embedding_status, completed_at)
    VALUES (:'latest_version', 'ready', 'embedded', now());

CREATE TABLE knowledge_fixture.original_sources AS
    SELECT knowledge_source_id, to_jsonb(source) AS data FROM public.knowledge_sources source;
CREATE TABLE knowledge_fixture.original_versions AS
    SELECT document_version_id, to_jsonb(version) AS data FROM public.document_versions version;
