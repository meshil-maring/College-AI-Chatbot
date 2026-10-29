BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
SELECT knowledge_fixture.workflow_resource('scope_public', 'public');
SELECT knowledge_fixture.workflow_decide('scope_public', 'submit');
SELECT knowledge_fixture.workflow_decide('scope_public', 'approve');
SELECT knowledge_fixture.workflow_decide('scope_public', 'publish');
SELECT knowledge_fixture.workflow_resource('scope_staff', 'restricted', '["staff"]');
SELECT knowledge_fixture.workflow_decide('scope_staff', 'submit');
SELECT knowledge_fixture.workflow_decide('scope_staff', 'approve');
SELECT knowledge_fixture.workflow_decide('scope_staff', 'publish');
SELECT knowledge_fixture.workflow_resource('scope_draft', 'public');

SELECT knowledge_fixture.assert_true('Resource chat returns only an authorized indexed live source',
    public.read_resource_chat_context(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('scope_public'))->>'available' = 'true'
    AND public.read_resource_chat_context(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('scope_staff'))->>'title' = 'scope_staff');
SELECT knowledge_fixture.reject('Resource chat cannot reveal another role audience', $q$
    SELECT public.read_resource_chat_context(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('scope_staff'))
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.reject('Resource conversation context always requires an authenticated actor', $q$
    SELECT public.read_resource_chat_context(NULL, knowledge_fixture.id('tenant'), knowledge_fixture.id('scope_public'))
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Resource chat cannot reveal another institution', $q$
    SELECT public.read_resource_chat_context(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('foreign_tenant'),
        knowledge_fixture.id('scope_public'))
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.reject('Admin management does not make a draft eligible for chat', $q$
    SELECT public.read_resource_chat_context(knowledge_fixture.id('tenant_actor'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('scope_draft'))
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.reject('Metadata without embedded chunks is unavailable to resource chat', $q$
    SELECT public.read_resource_chat_context(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('public'))
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.assert_true('Resource context is a service-only capability',
    NOT has_function_privilege('anon', 'public.read_resource_chat_context(uuid,uuid,uuid)', 'EXECUTE')
    AND NOT has_function_privilege('authenticated', 'public.read_resource_chat_context(uuid,uuid,uuid)', 'EXECUTE')
    AND has_function_privilege('service_role', 'public.read_resource_chat_context(uuid,uuid,uuid)', 'EXECUTE')
    AND NOT has_function_privilege('service_role', 'public.guard_conversation_resource_scope()', 'EXECUTE'));

SELECT knowledge_fixture.id('wf_staff') AS scope_actor, knowledge_fixture.id('tenant') AS scope_tenant,
    knowledge_fixture.id('scope_public') AS scope_source \gset
SET LOCAL ROLE service_role;
INSERT INTO public.conversations(user_id, title, knowledge_source_id, resource_institution_id)
    VALUES(:'scope_actor', 'Fictional selected resource conversation', :'scope_source', :'scope_tenant')
    RETURNING conversation_id AS scope_conversation \gset
RESET ROLE;
INSERT INTO knowledge_fixture.ids VALUES('scope_conversation', :'scope_conversation');
SELECT knowledge_fixture.assert_true('Service can persist an authorized resource context',
    (SELECT knowledge_source_id = knowledge_fixture.id('scope_public')
        AND resource_institution_id = knowledge_fixture.id('tenant') FROM public.conversations
        WHERE conversation_id = knowledge_fixture.id('scope_conversation')));
SELECT knowledge_fixture.reject('Resource scope cannot be broadened to institution chat', $q$
    UPDATE public.conversations SET knowledge_source_id = NULL, resource_institution_id = NULL
        WHERE conversation_id = knowledge_fixture.id('scope_conversation')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Resource scope cannot switch sources', $q$
    UPDATE public.conversations SET knowledge_source_id = knowledge_fixture.id('scope_staff')
        WHERE conversation_id = knowledge_fixture.id('scope_conversation')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Resource conversation owner cannot be reassigned', $q$
    UPDATE public.conversations SET user_id = knowledge_fixture.id('wf_faculty')
        WHERE conversation_id = knowledge_fixture.id('scope_conversation')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('Denied actors cannot create a resource conversation', $q$
    INSERT INTO public.conversations(user_id, knowledge_source_id, resource_institution_id)
        VALUES(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('scope_staff'), knowledge_fixture.id('tenant'))
$q$, ARRAY['P0002']);
INSERT INTO public.conversations(user_id, title) VALUES(:'scope_actor', 'Fictional ordinary chat')
    RETURNING conversation_id AS ordinary_conversation \gset
INSERT INTO knowledge_fixture.ids VALUES('ordinary_conversation', :'ordinary_conversation');
SELECT knowledge_fixture.reject('An existing ordinary conversation cannot acquire resource context', $q$
    UPDATE public.conversations SET knowledge_source_id = knowledge_fixture.id('scope_public'),
        resource_institution_id = knowledge_fixture.id('tenant')
        WHERE conversation_id = knowledge_fixture.id('ordinary_conversation')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.workflow_decide('scope_public', 'unpublish');
SELECT knowledge_fixture.reject('Unpublication revokes an existing conversation resource context', $q$
    SELECT public.read_resource_chat_context(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'),
        knowledge_fixture.id('scope_public'))
$q$, ARRAY['P0002']);
COMMIT;
