BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
UPDATE public.institutions SET code = upper(code) WHERE institution_id = knowledge_fixture.id('tenant');
DO $$
DECLARE fixture_role text; actor uuid; auth_id uuid; org uuid;
BEGIN
    SELECT organization_id INTO org FROM public.institutions WHERE institution_id = knowledge_fixture.id('tenant');
    FOREACH fixture_role IN ARRAY ARRAY['student', 'staff', 'faculty'] LOOP
        actor := gen_random_uuid(); auth_id := gen_random_uuid();
        INSERT INTO auth.users(id, email) VALUES(auth_id, 'workflow-' || fixture_role || '@example.invalid');
        INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
            VALUES(actor, auth_id, 'workflow-' || fixture_role || '@example.invalid', 'Fictional', fixture_role);
        INSERT INTO public.user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
            SELECT actor, id, 'institution', knowledge_fixture.id('tenant'), org FROM public.roles WHERE roles.name = fixture_role;
        INSERT INTO knowledge_fixture.ids VALUES('wf_' || fixture_role, actor);
        IF fixture_role = 'student' THEN
            INSERT INTO public.students(user_id, institution_id, student_number, register_number,
                email, enrollment_date, approval_status)
            VALUES(actor, knowledge_fixture.id('tenant'), 'WF-STUDENT', 'WF-STUDENT',
                'workflow-student@example.invalid', CURRENT_DATE, 'approved');
        END IF;
    END LOOP;
END;
$$;

CREATE FUNCTION knowledge_fixture.workflow_resource(key text, visibility text, targets jsonb DEFAULT '[]')
RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE revision jsonb; receipt jsonb; run_id uuid; chunk uuid;
BEGIN
    revision := public.save_knowledge_draft(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        jsonb_build_object('title', key, 'source_type', 'handbook', 'visibility', visibility, 'audience_roles', targets));
    INSERT INTO knowledge_fixture.ids VALUES(key, (revision->>'knowledge_source_id')::uuid),
        (key || '_revision', (revision->>'revision_id')::uuid);
    receipt := public.register_knowledge_upload(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        (revision->>'revision_id')::uuid, (revision->>'revision_version')::bigint,
        jsonb_build_object('original_filename', key || '.pdf', 'file_type', 'pdf', 'mime_type', 'application/pdf',
            'file_size_bytes', 10, 'storage_bucket', 'fictional', 'storage_object_key', key));
    run_id := (receipt->>'processing_run_id')::uuid;
    INSERT INTO knowledge_fixture.ids VALUES(key || '_version', (receipt->>'document_version_id')::uuid),
        (key || '_run', run_id), (key || '_document', (receipt->>'document_id')::uuid);
    UPDATE public.document_processing_runs SET status = 'ready', embedding_status = 'embedded', completed_at = now()
        WHERE processing_run_id = run_id;
    INSERT INTO public.knowledge_chunks(processing_run_id, chunk_sequence, content_text)
        VALUES(run_id, 1, 'Fictional evidence for ' || key) RETURNING chunk_id INTO chunk;
    INSERT INTO knowledge_fixture.ids VALUES(key || '_chunk', chunk);
    INSERT INTO public.chunk_embeddings(chunk_id, model_name, embedding_dimensions, embedding)
        VALUES(chunk, 'fictional-model', 1536, ('[1,' || repeat('0,', 1534) || '0]')::extensions.vector);
    RETURN (revision->>'revision_id')::uuid;
END;
$$;

CREATE FUNCTION knowledge_fixture.workflow_decide(key text, command text) RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE revision public.knowledge_source_revisions; policy bigint;
BEGIN
    SELECT * INTO STRICT revision FROM public.knowledge_source_revisions WHERE revision_id = knowledge_fixture.id(key || '_revision');
    SELECT policy_version INTO policy FROM public.knowledge_sources WHERE knowledge_source_id = revision.knowledge_source_id;
    RETURN public.decide_knowledge_revision(
        CASE WHEN command = 'submit' THEN knowledge_fixture.id('wf_staff') ELSE knowledge_fixture.id('tenant_actor') END,
        knowledge_fixture.id('tenant'), revision.revision_id, command, revision.revision_version, policy, 'Fictional review');
END;
$$;

SELECT knowledge_fixture.workflow_resource('wf_public', 'public');
SELECT knowledge_fixture.workflow_resource('wf_members', 'authenticated');
SELECT knowledge_fixture.workflow_resource('wf_students', 'restricted', '["student"]');
SELECT knowledge_fixture.workflow_resource('wf_staff_only', 'restricted', '["staff"]');
SELECT knowledge_fixture.workflow_resource('wf_faculty_only', 'restricted', '["faculty"]');
SELECT knowledge_fixture.workflow_resource('wf_combined', 'restricted', '["student", "faculty"]');
SELECT knowledge_fixture.workflow_resource('wf_admins', 'restricted', '["admin"]');
COMMIT;
