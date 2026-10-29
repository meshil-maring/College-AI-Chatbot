BEGIN;
SET LOCAL request.jwt.claim.role = 'service_role';
INSERT INTO knowledge_fixture.ids VALUES('expired_turn', gen_random_uuid()), ('expired_conversation', gen_random_uuid());
SELECT knowledge_fixture.id('wf_staff') AS stale_actor, knowledge_fixture.id('tenant') AS stale_tenant,
    knowledge_fixture.id('expired_turn') AS stale_turn, knowledge_fixture.id('expired_conversation') AS stale_conversation \gset
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.turn_probes VALUES('expired_first', public.claim_chat_turn(:'stale_actor', :'stale_tenant', :'stale_turn',
    :'stale_conversation', :'stale_conversation', 'Hello'));
RESET ROLE;
SELECT knowledge_fixture.reject('A missing worker token cannot complete another execution', $q$
    SELECT public.complete_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('expired_turn'),
        NULL, '{}', '{}', '{}')
$q$, ARRAY['PT410']);
UPDATE public.chat_turns SET lease_until = clock_timestamp() - interval '1 second' WHERE client_turn_id = :'stale_turn';
SELECT knowledge_fixture.assert_true('An expired worker lease enables explicit retry',
    (public.read_chat_turn(:'stale_actor', :'stale_tenant', :'stale_turn')->>'retryable')::boolean);
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.turn_probes VALUES('expired_retry', public.claim_chat_turn(:'stale_actor', :'stale_tenant', :'stale_turn',
    :'stale_conversation', :'stale_conversation', 'Hello'));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Expired-lease retry changes the fence without duplicating the question',
    (SELECT receipt->>'worker_token' FROM knowledge_fixture.turn_probes WHERE label = 'expired_first') <>
    (SELECT receipt->>'worker_token' FROM knowledge_fixture.turn_probes WHERE label = 'expired_retry')
    AND (SELECT count(*) = 1 FROM public.messages WHERE conversation_id = :'stale_conversation'));
SELECT knowledge_fixture.reject('The expired worker cannot overwrite its replacement', $q$
    SELECT public.complete_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('expired_turn'),
        (SELECT (receipt->>'worker_token')::uuid FROM knowledge_fixture.turn_probes WHERE label = 'expired_first'), '{}', '{}', '{}')
$q$, ARRAY['PT410']);
SELECT knowledge_fixture.reject('Invalid receipt status rolls back the complete operation', $q$
    SELECT public.complete_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('expired_turn'),
        (SELECT (receipt->>'worker_token')::uuid FROM knowledge_fixture.turn_probes WHERE label = 'expired_retry'),
        jsonb_build_object('session_id', knowledge_fixture.id('expired_conversation'), 'conversation_id', knowledge_fixture.id('expired_conversation')),
        public.snapshot_knowledge_policy(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), '{}'::uuid[]), '{"chunks":[]}')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.reject('An invalid citation rolls back answer and response records', $q$
    SELECT public.complete_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('expired_turn'),
        (SELECT (receipt->>'worker_token')::uuid FROM knowledge_fixture.turn_probes WHERE label = 'expired_retry'),
        jsonb_build_object('session_id', knowledge_fixture.id('expired_conversation'), 'conversation_id', knowledge_fixture.id('expired_conversation'),
            'status', 'success', 'answer', 'Hello', 'source_references', jsonb_build_array(jsonb_build_object('chunk_id', gen_random_uuid()))),
        public.snapshot_knowledge_policy(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), '{}'::uuid[]), '{"chunks":[]}')
$q$, ARRAY['23514']);
SELECT knowledge_fixture.assert_true('A failed completion leaves only its original user message',
    (SELECT count(*) = 1 FROM public.messages WHERE conversation_id = :'stale_conversation')
    AND (SELECT count(*) = 0 FROM public.ai_responses a JOIN public.messages m USING(message_id) WHERE m.conversation_id = :'stale_conversation')
    AND (SELECT state = 'processing' AND response IS NULL FROM public.chat_turns WHERE client_turn_id = :'stale_turn'));
SET LOCAL ROLE service_role;
DO $$ BEGIN
    BEGIN
        INSERT INTO public.messages(conversation_id, message_sequence, message_type, content_text)
        SELECT conversation_id, 2, 'user', 'Unmanaged write' FROM public.chat_turns WHERE request_query = 'Hello';
        RAISE EXCEPTION 'Expected managed message denial';
    EXCEPTION WHEN serialization_failure THEN NULL;
    END;
END; $$;
RESET ROLE;
SELECT knowledge_fixture.assert_true('Direct service inserts cannot interleave in a managed turn',
    (SELECT count(*) = 1 FROM public.messages WHERE conversation_id = :'stale_conversation'));
SET LOCAL ROLE service_role;
INSERT INTO knowledge_fixture.turn_probes VALUES('insufficient_complete', public.complete_chat_turn(:'stale_actor', :'stale_tenant', :'stale_turn',
    (SELECT (receipt->>'worker_token')::uuid FROM knowledge_fixture.turn_probes WHERE label = 'expired_retry'),
    jsonb_build_object('session_id', :'stale_conversation', 'conversation_id', :'stale_conversation',
        'status', 'insufficient_context', 'answer', NULL, 'source_references', '[]'::jsonb),
    public.snapshot_knowledge_policy(:'stale_actor', :'stale_tenant', '{}'::uuid[]), '{"chunks":[]}'));
RESET ROLE;
SELECT knowledge_fixture.assert_true('Insufficient context is a completed, replayable turn with a history marker',
    (SELECT receipt->'response'->>'status' = 'insufficient_context' AND receipt->'response'->'answer' = 'null'::jsonb
        FROM knowledge_fixture.turn_probes WHERE label = 'insufficient_complete')
    AND (SELECT count(*) = 2 FROM public.messages WHERE conversation_id = :'stale_conversation'));
UPDATE public.users SET status = 'inactive' WHERE id = :'stale_actor';
SELECT knowledge_fixture.reject('An inactive actor cannot replay an otherwise completed turn', $q$
    SELECT public.read_chat_turn(knowledge_fixture.id('wf_staff'), knowledge_fixture.id('tenant'), knowledge_fixture.id('expired_turn'))
$q$, ARRAY['42501']);
UPDATE public.users SET status = 'active' WHERE id = :'stale_actor';
COMMIT;
