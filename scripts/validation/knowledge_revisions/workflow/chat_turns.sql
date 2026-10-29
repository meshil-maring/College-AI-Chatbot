BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
SELECT knowledge_fixture.workflow_resource('turn_public', 'public');
SELECT knowledge_fixture.workflow_decide('turn_public', 'submit');
SELECT knowledge_fixture.workflow_decide('turn_public', 'approve');
SELECT knowledge_fixture.workflow_decide('turn_public', 'publish');
INSERT INTO knowledge_fixture.ids VALUES('turn_id', gen_random_uuid()), ('turn_conversation', gen_random_uuid());
CREATE TABLE knowledge_fixture.turn_probes(label text PRIMARY KEY, receipt jsonb);
GRANT USAGE ON SCHEMA knowledge_fixture TO service_role;
GRANT SELECT, INSERT ON knowledge_fixture.turn_probes TO service_role;
SELECT knowledge_fixture.id('wf_staff') AS turn_actor, knowledge_fixture.id('tenant') AS turn_tenant,
    knowledge_fixture.id('turn_id') AS turn_id, knowledge_fixture.id('turn_conversation') AS turn_conversation,
    knowledge_fixture.id('turn_public') AS turn_source, knowledge_fixture.id('turn_public_chunk') AS turn_chunk \gset
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.turn_probes VALUES('first', public.claim_chat_turn(:'turn_actor', :'turn_tenant', :'turn_id',
    :'turn_conversation', :'turn_conversation', 'Explain the resource', :'turn_source'));
INSERT INTO knowledge_fixture.turn_probes VALUES('duplicate', public.claim_chat_turn(:'turn_actor', :'turn_tenant', :'turn_id',
    :'turn_conversation', :'turn_conversation', 'Explain the resource', :'turn_source'));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Claim creates one conversation and one user message',
    (SELECT count(*) = 1 FROM public.messages WHERE conversation_id = :'turn_conversation')
    AND (SELECT receipt->>'state' = 'claimed' FROM knowledge_fixture.turn_probes WHERE label = 'first'));
SELECT knowledge_fixture.assert_true('A concurrent duplicate is pending without another worker token',
    (SELECT receipt->>'state' = 'processing' AND NOT receipt ? 'worker_token' FROM knowledge_fixture.turn_probes WHERE label = 'duplicate'));
SELECT knowledge_fixture.reject('A turn cannot be reused for a different question', $q$
    SELECT public.claim_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('turn_id'),
        knowledge_fixture.id('turn_conversation'), knowledge_fixture.id('turn_conversation'), 'Different question', knowledge_fixture.id('turn_public'))
$q$, ARRAY['22023']);
SELECT knowledge_fixture.reject('Another turn cannot interleave in an unfinished conversation', $q$
    SELECT public.claim_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), gen_random_uuid(),
        knowledge_fixture.id('turn_conversation'), knowledge_fixture.id('turn_conversation'), 'Another question', knowledge_fixture.id('turn_public'))
$q$, ARRAY['PT409']);
SELECT knowledge_fixture.reject('Another owner cannot recover a receipt', $q$
    SELECT public.read_chat_turn(knowledge_fixture.id('wf_faculty'), knowledge_fixture.id('tenant'), knowledge_fixture.id('turn_id'))
$q$, ARRAY['P0002']);
SELECT knowledge_fixture.reject('A different institution cannot recover a receipt', $q$
    SELECT public.read_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('foreign_tenant'), knowledge_fixture.id('turn_id'))
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('A missing actor cannot claim a chat turn', $q$
    SELECT public.claim_chat_turn(NULL, knowledge_fixture.id('tenant'), gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 'Question')
$q$, ARRAY['42501']);
SELECT knowledge_fixture.reject('Conversation institution cannot be reassigned', $q$
    UPDATE public.conversations SET chat_institution_id = knowledge_fixture.id('foreign_tenant')
        WHERE conversation_id = knowledge_fixture.id('turn_conversation')
$q$, ARRAY['42501']);
SET LOCAL ROLE service_role;
SELECT public.fail_chat_turn(:'turn_actor', :'turn_tenant', :'turn_id',
    (SELECT (receipt->>'worker_token')::uuid FROM knowledge_fixture.turn_probes WHERE label = 'first'));
INSERT INTO knowledge_fixture.turn_probes VALUES('failed', public.read_chat_turn(:'turn_actor', :'turn_tenant', :'turn_id'));
INSERT INTO knowledge_fixture.turn_probes VALUES('retry', public.claim_chat_turn(:'turn_actor', :'turn_tenant', :'turn_id',
    :'turn_conversation', :'turn_conversation', 'Explain the resource', :'turn_source'));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Failure is recoverable and retry reuses the saved user message',
    (SELECT receipt->>'state' = 'failed' AND (receipt->>'retryable')::boolean FROM knowledge_fixture.turn_probes WHERE label = 'failed')
    AND (SELECT count(*) = 1 FROM public.messages WHERE conversation_id = :'turn_conversation')
    AND (SELECT attempts = 2 FROM public.chat_turns WHERE client_turn_id = :'turn_id'));
SELECT knowledge_fixture.reject('A replaced worker cannot finish the answer', $q$
    SELECT public.complete_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('turn_id'),
        (SELECT (receipt->>'worker_token')::uuid FROM knowledge_fixture.turn_probes WHERE label = 'first'), '{}', '{}', '{}')
$q$, ARRAY['PT410']);
COMMIT;

-- Commit the answer as the actual service role, including all deferred checks.
BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.turn_probes VALUES('complete', public.complete_chat_turn(:'turn_actor', :'turn_tenant', :'turn_id',
    (SELECT (receipt->>'worker_token')::uuid FROM knowledge_fixture.turn_probes WHERE label = 'retry'),
    jsonb_build_object('session_id', :'turn_conversation', 'conversation_id', :'turn_conversation', 'message_id', NULL,
        'answer', E'### Resource\n\nA supported answer.', 'status', 'success', 'model_used', 'internal-model', 'metadata', '{"private":true}'::jsonb,
        'source_references', jsonb_build_array(jsonb_build_object('chunk_id', :'turn_chunk', 'quote', 'Fictional evidence for turn_public')),
        'sources', jsonb_build_array(jsonb_build_object('chunk_id', :'turn_chunk', 'quote', 'Fictional evidence for turn_public'))),
    public.snapshot_knowledge_policy(:'turn_actor', :'turn_tenant', ARRAY[:'turn_chunk'::uuid]),
    jsonb_build_object('retrieval_query', 'Explain the resource', 'model_name', 'fictional', 'latency_ms', 10,
        'chunks', jsonb_build_array(jsonb_build_object('chunk_id', :'turn_chunk', 'score', 0.9)))));
COMMIT;

BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.turn_probes VALUES('replay', public.claim_chat_turn(:'turn_actor', :'turn_tenant', :'turn_id',
    :'turn_conversation', :'turn_conversation', 'Explain the resource', :'turn_source'));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Completion stores one answer and replays its exact receipt',
    (SELECT receipt->'response' FROM knowledge_fixture.turn_probes WHERE label = 'complete') =
    (SELECT receipt->'response' FROM knowledge_fixture.turn_probes WHERE label = 'replay')
    AND (SELECT count(*) = 2 FROM public.messages WHERE conversation_id = :'turn_conversation'));
SELECT knowledge_fixture.assert_true('Receipts omit provider diagnostics and preserve Markdown',
    (SELECT receipt->'response'->'model_used' = 'null'::jsonb AND receipt->'response'->'metadata' = '{}'::jsonb
        AND receipt->'response'->>'answer' = E'### Resource\n\nA supported answer.' FROM knowledge_fixture.turn_probes WHERE label = 'complete'));
SELECT knowledge_fixture.assert_true('Answer, retrieval and citation records commit together',
    (SELECT count(*) = 1 FROM public.ai_responses a JOIN public.messages m USING(message_id) WHERE m.conversation_id = :'turn_conversation')
    AND (SELECT count(*) = 1 FROM public.message_citations c JOIN public.messages m USING(message_id) WHERE m.conversation_id = :'turn_conversation')
    AND (SELECT count(*) = 1 FROM public.retrieved_chunks c JOIN public.retrieval_operations r USING(retrieval_operation_id)
        JOIN public.ai_responses a USING(ai_response_id) JOIN public.messages m USING(message_id) WHERE m.conversation_id = :'turn_conversation'));
SELECT knowledge_fixture.assert_true('Browser roles cannot invoke turn writers or read the ledger',
    NOT has_function_privilege('authenticated', 'public.claim_chat_turn(uuid,uuid,uuid,uuid,uuid,text,uuid)', 'EXECUTE')
    AND NOT has_function_privilege('anon', 'public.read_chat_turn(uuid,uuid,uuid)', 'EXECUTE')
    AND NOT has_table_privilege('authenticated', 'public.chat_turns', 'SELECT')
    AND NOT has_table_privilege('service_role', 'public.chat_turns', 'INSERT'));
SELECT knowledge_fixture.workflow_decide('turn_public', 'unpublish');
SELECT knowledge_fixture.reject('A saved answer cannot be replayed after source revocation', $q$
    SELECT public.read_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('turn_id'))
$q$, ARRAY['P0002','40001']);
COMMIT;
