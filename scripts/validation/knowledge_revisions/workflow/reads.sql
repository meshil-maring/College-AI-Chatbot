BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
DO $$
DECLARE audience text; role_name text; actor uuid; expected boolean; actual boolean;
BEGIN
    FOREACH audience IN ARRAY ARRAY['wf_public', 'wf_members', 'wf_students', 'wf_staff_only',
        'wf_faculty_only', 'wf_combined', 'wf_admins'] LOOP
        FOREACH role_name IN ARRAY ARRAY['visitor', 'student', 'staff', 'faculty', 'admin'] LOOP
            actor := CASE role_name WHEN 'visitor' THEN NULL WHEN 'admin' THEN knowledge_fixture.id('tenant_actor')
                ELSE knowledge_fixture.id('wf_' || role_name) END;
            expected := audience = 'wf_public' OR (audience = 'wf_members' AND role_name <> 'visitor')
                OR (audience = 'wf_students' AND role_name = 'student')
                OR (audience = 'wf_staff_only' AND role_name = 'staff')
                OR (audience = 'wf_faculty_only' AND role_name = 'faculty')
                OR (audience = 'wf_combined' AND role_name IN ('student', 'faculty'))
                OR (audience = 'wf_admins' AND role_name = 'admin');
            actual := public.knowledge_source_allowed(actor, knowledge_fixture.id('tenant'), knowledge_fixture.id(audience));
            PERFORM knowledge_fixture.assert_true(audience || ' audience for ' || role_name, actual = expected);
        END LOOP;
    END LOOP;
END;
$$;
SELECT knowledge_fixture.assert_true('Forbidden resource metadata is absent from reader lists',
    NOT EXISTS(SELECT 1 FROM jsonb_array_elements(public.read_knowledge_resources(
        knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'))->'items') item
        WHERE item->>'title' IN ('wf_staff_only', 'wf_faculty_only', 'wf_admins', 'wf_indexing')));
SELECT knowledge_fixture.reject('Forbidden resource detail hides existence', $q$
    SELECT public.read_knowledge_resources(knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'), knowledge_fixture.id('wf_staff_only'))
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.reject('Non-admin cannot load institution review queue', $q$
    SELECT public.read_knowledge_revisions(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('tenant'), 'review')
$q$, ARRAY['42501']);
SELECT knowledge_fixture.assert_true('Another uploader cannot read private drafts',
    (public.read_knowledge_revisions(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('tenant'))->>'total')::integer = 0);
SELECT knowledge_fixture.assert_true('Student retrieval excludes staff content before ranking',
    NOT EXISTS(SELECT 1 FROM public.search_audience_knowledge_chunks(knowledge_fixture.id('wf_student'),
        ('[1,' || repeat('0,', 1534) || '0]')::extensions.vector, 20, knowledge_fixture.id('tenant'),
        NULL, NULL, NULL, NULL, 'fictional-model') WHERE source_title IN ('wf_staff_only', 'wf_faculty_only', 'wf_admins')));
SELECT knowledge_fixture.assert_true('Top-k remains usable after audience filtering',
    (SELECT count(*) = 1 FROM public.search_audience_knowledge_chunks(knowledge_fixture.id('wf_student'),
        ('[1,' || repeat('0,', 1534) || '0]')::extensions.vector, 1, knowledge_fixture.id('tenant'),
        NULL, NULL, NULL, NULL, 'fictional-model')));
SELECT knowledge_fixture.assert_true('Anonymous retrieval contains only public content',
    (SELECT count(*) = 1 AND bool_and(source_title = 'wf_public') FROM public.search_public_knowledge_chunks(
        ('[1,' || repeat('0,', 1534) || '0]')::extensions.vector, 20, knowledge_fixture.id('tenant'), NULL, 'fictional-model')));
UPDATE public.students SET approval_status = 'pending' WHERE user_id = knowledge_fixture.id('wf_student');
SELECT knowledge_fixture.assert_true('Pending student loses institutional resource access',
    NOT public.knowledge_source_allowed(knowledge_fixture.id('wf_student'), knowledge_fixture.id('tenant'), knowledge_fixture.id('wf_students')));
UPDATE public.students SET approval_status = 'approved' WHERE user_id = knowledge_fixture.id('wf_student');
COMMIT;
