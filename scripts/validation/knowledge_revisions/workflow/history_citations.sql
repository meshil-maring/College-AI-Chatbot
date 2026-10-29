BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
SELECT knowledge_fixture.workflow_resource('history_first', 'public');
SELECT knowledge_fixture.workflow_resource('history_second', 'public');
SELECT knowledge_fixture.workflow_resource('history_extra', 'public');
INSERT INTO public.knowledge_chunks(processing_run_id, chunk_sequence, content_text, section_title)
    VALUES(knowledge_fixture.id('history_first_run'), 2, 'Uncited evidence in the same document.', 'Uncited')
    RETURNING chunk_id AS uncited_chunk \gset
INSERT INTO knowledge_fixture.ids VALUES('history_uncited', :'uncited_chunk');
INSERT INTO public.chunk_embeddings(chunk_id, model_name, embedding_dimensions, embedding)
    SELECT :'uncited_chunk', model_name, embedding_dimensions, embedding FROM public.chunk_embeddings
    WHERE chunk_id = knowledge_fixture.id('history_first_chunk');
UPDATE public.knowledge_chunks SET section_title = 'Library rules'
    WHERE chunk_id = knowledge_fixture.id('history_first_chunk');
DO $$ DECLARE key text; command text;
BEGIN
    FOREACH key IN ARRAY ARRAY['history_first','history_second','history_extra'] LOOP
        FOREACH command IN ARRAY ARRAY['submit','approve','publish'] LOOP
            PERFORM knowledge_fixture.workflow_decide(key, command);
        END LOOP;
    END LOOP;
END $$;
INSERT INTO knowledge_fixture.ids VALUES('history_turn', gen_random_uuid()), ('history_conversation', gen_random_uuid()),
    ('history_legacy_conversation', gen_random_uuid()), ('history_legacy_message', gen_random_uuid());
CREATE TABLE knowledge_fixture.history_probes(label text PRIMARY KEY, data jsonb);
GRANT USAGE ON SCHEMA knowledge_fixture TO service_role;
GRANT SELECT, INSERT ON knowledge_fixture.history_probes TO service_role;
SELECT knowledge_fixture.id('wf_staff') AS history_actor, knowledge_fixture.id('tenant') AS history_tenant,
    knowledge_fixture.id('history_turn') AS history_turn, knowledge_fixture.id('history_conversation') AS history_conversation,
    knowledge_fixture.id('history_first_chunk') AS history_first, knowledge_fixture.id('history_second_chunk') AS history_second,
    knowledge_fixture.id('history_extra_chunk') AS history_extra, knowledge_fixture.id('history_legacy_message') AS legacy_message \gset
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes VALUES('claim', public.claim_chat_turn(:'history_actor', :'history_tenant',
    :'history_turn', :'history_conversation', :'history_conversation', 'Compare these resources'));
COMMIT;

BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes VALUES('complete', public.complete_chat_turn(:'history_actor', :'history_tenant', :'history_turn',
    (SELECT (data->>'worker_token')::uuid FROM knowledge_fixture.history_probes WHERE label = 'claim'),
    jsonb_build_object('session_id', :'history_conversation', 'conversation_id', :'history_conversation',
        'answer', 'An answer with two cited sources.', 'status', 'success',
        'source_references', jsonb_build_array(jsonb_build_object('chunk_id', :'history_second'), jsonb_build_object('chunk_id', :'history_first'))),
    public.snapshot_knowledge_policy(:'history_actor', :'history_tenant', ARRAY[:'history_first'::uuid, :'history_second'::uuid, :'uncited_chunk'::uuid]),
    jsonb_build_object('chunks', jsonb_build_array(jsonb_build_object('chunk_id', :'history_first', 'score', 0.91),
        jsonb_build_object('chunk_id', :'history_second', 'score', 0.72), jsonb_build_object('chunk_id', :'uncited_chunk', 'score', 0.4)))));
COMMIT;

BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
SELECT (data->'response'->>'message_id')::uuid AS history_message
    FROM knowledge_fixture.history_probes WHERE label = 'complete' \gset
INSERT INTO knowledge_fixture.ids VALUES('history_message', :'history_message');
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes VALUES('read', public.read_conversation_citations(:'history_actor', :'history_conversation', ARRAY[:'history_message'::uuid]));
RESET ROLE;
SELECT knowledge_fixture.assert_true('History citations retain citation order, original quote, title, section and score',
    (SELECT jsonb_array_length(data->:'history_message'->'sources') = 2
        AND data->:'history_message'->>'available' = 'true'
        AND data->:'history_message'->'sources'->0->>'chunk_id' = :'history_second'
        AND data->:'history_message'->'sources'->1->>'quote' = 'Fictional evidence for history_first'
        AND data->:'history_message'->'sources'->1->>'source_title' = 'history_first'
        AND data->:'history_message'->'sources'->1->>'section' = 'Library rules'
        AND (data->:'history_message'->'sources'->1->>'relevance_score')::numeric = 0.91
    FROM knowledge_fixture.history_probes WHERE label = 'read'));
SELECT knowledge_fixture.assert_true('History citations omit storage, provider and policy diagnostics',
    (SELECT data::text NOT LIKE '%storage%' AND data::text NOT LIKE '%provider%' AND data::text NOT LIKE '%institution_id%'
        FROM knowledge_fixture.history_probes WHERE label = 'read'));
SELECT knowledge_fixture.reject('Another owner cannot read conversation citations', $q$
    SELECT public.read_conversation_citations(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('history_conversation'),
        ARRAY[knowledge_fixture.id('history_message')])
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.reject('A foreign institution actor cannot read conversation citations', $q$
    SELECT public.read_conversation_citations(knowledge_fixture.id('foreign_tenant_actor'), knowledge_fixture.id('history_conversation'),
        ARRAY[knowledge_fixture.id('history_message')])
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.reject('A missing actor cannot read conversation citations', $q$
    SELECT public.read_conversation_citations(NULL, knowledge_fixture.id('history_conversation'), ARRAY[knowledge_fixture.id('history_message')])
$q$, ARRAY['42501']);
SELECT knowledge_fixture.assert_true('Browser roles cannot invoke the history reader directly',
    NOT has_function_privilege('anon', 'public.read_conversation_citations(uuid,uuid,uuid[])', 'EXECUTE')
    AND NOT has_function_privilege('authenticated', 'public.read_conversation_citations(uuid,uuid,uuid[])', 'EXECUTE')
    AND has_function_privilege('service_role', 'public.read_conversation_citations(uuid,uuid,uuid[])', 'EXECUTE'));

-- Older answers with valid relational provenance restore without a durable receipt.
INSERT INTO public.conversations(conversation_id, user_id) VALUES(knowledge_fixture.id('history_legacy_conversation'), :'history_actor');
INSERT INTO public.messages(message_id, conversation_id, message_sequence, message_type, content_text, knowledge_policy)
    SELECT :'legacy_message', knowledge_fixture.id('history_legacy_conversation'), 1, 'assistant', content_text, knowledge_policy
    FROM public.messages WHERE message_id = :'history_message';
INSERT INTO public.ai_responses(message_id, provider_name, model_name, validation_status)
    VALUES(:'legacy_message', 'fictional', 'history-fixture', 'pending') RETURNING ai_response_id AS legacy_response \gset
INSERT INTO public.retrieval_operations(ai_response_id, query_text, status, completed_at)
    VALUES(:'legacy_response', 'Legacy question', 'completed', now()) RETURNING retrieval_operation_id AS legacy_operation \gset
INSERT INTO public.retrieved_chunks(retrieval_operation_id, chunk_id, retrieval_rank, relevance_score, selected_for_context)
    SELECT :'legacy_operation', chunk_id, retrieval_rank, relevance_score, selected_for_context
    FROM public.retrieved_chunks c JOIN public.retrieval_operations r USING(retrieval_operation_id)
    JOIN public.ai_responses a USING(ai_response_id) WHERE a.message_id = :'history_message';
INSERT INTO public.message_citations(message_id, retrieval_operation_id, chunk_id, display_order)
    SELECT :'legacy_message', :'legacy_operation', chunk_id, display_order FROM public.message_citations WHERE message_id = :'history_message';
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes VALUES('legacy', public.read_conversation_citations(:'history_actor',
    knowledge_fixture.id('history_legacy_conversation'), ARRAY[:'legacy_message'::uuid]));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Legacy citations restore from verified persisted evidence',
    (SELECT jsonb_array_length(data->:'legacy_message'->'sources') = 2 FROM knowledge_fixture.history_probes WHERE label = 'legacy'));

DO $$ DECLARE key text; conversation uuid; message uuid; answer uuid; operation uuid;
BEGIN
    FOREACH key IN ARRAY ARRAY['wf_student','wf_faculty','tenant_actor'] LOOP
        conversation := gen_random_uuid(); message := gen_random_uuid();
        INSERT INTO public.conversations(conversation_id, user_id) VALUES(conversation, knowledge_fixture.id(key));
        INSERT INTO public.messages(message_id, conversation_id, message_sequence, message_type, content_text, knowledge_policy)
            SELECT message, conversation, 1, 'assistant', content_text, knowledge_policy
            FROM public.messages WHERE message_id = knowledge_fixture.id('history_message');
        INSERT INTO public.ai_responses(message_id, provider_name, model_name, validation_status)
            VALUES(message, 'fictional', 'history-fixture', 'pending') RETURNING ai_response_id INTO answer;
        INSERT INTO public.retrieval_operations(ai_response_id, query_text, status, completed_at)
            VALUES(answer, 'Role question', 'completed', now()) RETURNING retrieval_operation_id INTO operation;
        INSERT INTO public.retrieved_chunks(retrieval_operation_id, chunk_id, retrieval_rank, selected_for_context)
            SELECT operation, chunk_id, display_order, true FROM public.message_citations
            WHERE message_id = knowledge_fixture.id('history_message');
        INSERT INTO public.message_citations(message_id, retrieval_operation_id, chunk_id, display_order)
            SELECT message, operation, chunk_id, display_order FROM public.message_citations
            WHERE message_id = knowledge_fixture.id('history_message');
        INSERT INTO knowledge_fixture.ids VALUES('history_' || key || '_conversation', conversation), ('history_' || key || '_message', message);
    END LOOP;
END $$;
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes
    SELECT key, public.read_conversation_citations(knowledge_fixture.id(key), knowledge_fixture.id('history_' || key || '_conversation'),
        ARRAY[knowledge_fixture.id('history_' || key || '_message')])
    FROM unnest(ARRAY['wf_student','wf_faculty','tenant_actor']) key;
RESET ROLE;
SELECT knowledge_fixture.assert_true('Student, faculty and admin owners restore authorized citation cards through the same service reader',
    (SELECT count(*) = 3 AND bool_and(jsonb_array_length(data->knowledge_fixture.id('history_' || label || '_message')::text->'sources') = 2)
        FROM knowledge_fixture.history_probes WHERE label IN ('wf_student','wf_faculty','tenant_actor')));

-- A citation borrowing another answer's operation must not claim its uncited evidence.
INSERT INTO public.message_citations(message_id, retrieval_operation_id, chunk_id, display_order)
    VALUES(:'history_message', :'legacy_operation', :'uncited_chunk', 3);
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes VALUES('corrupt_operation', public.read_conversation_citations(:'history_actor',
    :'history_conversation', ARRAY[:'history_message'::uuid, :'legacy_message'::uuid]));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Cross-message operation and foreign-conversation message IDs are excluded',
    (SELECT jsonb_array_length(data->:'history_message'->'sources') = 2 AND NOT data ? :'legacy_message'
        FROM knowledge_fixture.history_probes WHERE label = 'corrupt_operation'));
SELECT retrieval_operation_id AS history_operation FROM public.retrieval_operations r
    JOIN public.ai_responses a USING(ai_response_id) WHERE a.message_id = :'history_message' \gset
INSERT INTO public.retrieved_chunks(retrieval_operation_id, chunk_id, retrieval_rank, relevance_score, selected_for_context)
    VALUES(:'history_operation', :'history_extra', 4, 0.8, true);
INSERT INTO public.message_citations(message_id, retrieval_operation_id, chunk_id, display_order)
    VALUES(:'history_message', :'history_operation', :'history_extra', 4),
        (:'history_message', :'history_operation', :'history_first', 5);
UPDATE public.retrieved_chunks SET selected_for_context = false WHERE retrieval_operation_id = :'history_operation' AND chunk_id = :'history_second';
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes VALUES('filtered', public.read_conversation_citations(:'history_actor', :'history_conversation', ARRAY[:'history_message'::uuid]));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Unselected evidence, uncited context, duplicate chunks and outside-policy sources do not become cards',
    (SELECT jsonb_array_length(data->:'history_message'->'sources') = 1
        AND data->:'history_message'->'sources'->0->>'chunk_id' = :'history_first'
        FROM knowledge_fixture.history_probes WHERE label = 'filtered'));
UPDATE public.users SET status = 'inactive' WHERE id = :'history_actor';
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes VALUES('inactive', public.read_conversation_citations(:'history_actor', :'history_conversation', ARRAY[:'history_message'::uuid]));
RESET ROLE;
UPDATE public.users SET status = 'active' WHERE id = :'history_actor';
SELECT knowledge_fixture.assert_true('Inactive actors receive no source titles or quotes',
    (SELECT data->:'history_message'->>'available' = 'false' AND data->:'history_message'->'sources' = '[]'::jsonb
        FROM knowledge_fixture.history_probes WHERE label = 'inactive'));
SELECT knowledge_fixture.workflow_decide('history_first', 'unpublish');
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.history_probes VALUES('revoked', public.read_conversation_citations(:'history_actor', :'history_conversation', ARRAY[:'history_message'::uuid]));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Unpublication invalidates saved citation access',
    (SELECT data->:'history_message'->>'available' = 'false' AND data->:'history_message'->'sources' = '[]'::jsonb
        FROM knowledge_fixture.history_probes WHERE label = 'revoked'));
COMMIT;
