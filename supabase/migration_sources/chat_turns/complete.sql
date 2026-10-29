CREATE FUNCTION public.complete_chat_turn(actor uuid, tenant uuid, selected_turn uuid, token uuid,
    reply jsonb, policy jsonb, details jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE item public.chat_turns; assistant uuid := gen_random_uuid(); response_id uuid; operation_id uuid;
    chunk jsonb; citation jsonb; rank integer := 0; receipt jsonb;
BEGIN
    PERFORM public.require_chat_actor(actor, tenant);
    PERFORM pg_advisory_xact_lock(hashtextextended('chat-turn:' || actor::text || ':' || selected_turn::text, 0));
    SELECT * INTO item FROM public.chat_turns t
        WHERE t.actor_id = actor AND t.client_turn_id = selected_turn AND t.institution_id = tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Chat turn not found' USING ERRCODE = 'P0002'; END IF;
    IF item.state <> 'processing' OR token IS NULL OR item.worker_token IS DISTINCT FROM token THEN
        RAISE EXCEPTION 'Turn worker was replaced' USING ERRCODE = 'PT410';
    END IF;
    PERFORM 1 FROM public.conversations c WHERE c.conversation_id = item.conversation_id FOR UPDATE;
    IF NOT public.check_knowledge_policy(actor, policy) OR policy->>'institution_id' IS DISTINCT FROM tenant::text THEN
        RAISE EXCEPTION 'Source access changed' USING ERRCODE = '40001';
    END IF;
    IF item.knowledge_source_id IS NOT NULL THEN
        PERFORM public.read_resource_chat_context(actor, tenant, item.knowledge_source_id);
        IF (SELECT array_agg(key) FROM jsonb_object_keys(policy->'sources') key) IS DISTINCT FROM ARRAY[item.knowledge_source_id::text] THEN
            RAISE EXCEPTION 'Resource policy mismatch' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF reply->>'status' IS NULL OR reply->>'status' NOT IN ('success', 'insufficient_context')
        OR reply->>'conversation_id' IS DISTINCT FROM item.conversation_id::text
        OR reply->>'session_id' IS DISTINCT FROM item.session_id::text
        OR (reply->>'status' = 'success' AND NULLIF(btrim(reply->>'answer'), '') IS NULL)
        OR (reply->>'status' = 'insufficient_context' AND reply->>'answer' IS NOT NULL) THEN
        RAISE EXCEPTION 'Invalid answer receipt' USING ERRCODE = '23514';
    END IF;
    INSERT INTO public.messages(message_id, conversation_id, message_sequence, message_type, content_text, knowledge_policy)
    VALUES(assistant, item.conversation_id, item.user_sequence + 1, 'assistant',
        COALESCE(reply->>'answer', 'The available knowledge is insufficient to answer this question.'), policy);
    INSERT INTO public.ai_responses(message_id, provider_name, model_name, validation_status, input_token_count, output_token_count, latency_ms)
    VALUES(assistant, 'openrouter', COALESCE(NULLIF(details->>'model_name', ''), 'unspecified'), 'pending',
        (details->>'input_tokens')::integer, (details->>'output_tokens')::integer, (details->>'latency_ms')::integer)
    RETURNING ai_response_id INTO response_id;
    INSERT INTO public.retrieval_operations(ai_response_id, query_text, status, result_count, completed_at)
    VALUES(response_id, COALESCE(NULLIF(details->>'retrieval_query', ''), item.request_query), 'completed',
        jsonb_array_length(details->'chunks'), clock_timestamp()) RETURNING retrieval_operation_id INTO operation_id;
    FOR chunk IN SELECT * FROM jsonb_array_elements(details->'chunks') LOOP
        rank := rank + 1;
        IF NOT EXISTS (SELECT 1 FROM public.knowledge_chunks c
            JOIN public.document_processing_runs run USING(processing_run_id)
            JOIN public.document_versions v USING(document_version_id)
            JOIN public.documents d USING(document_id)
            WHERE c.chunk_id = (chunk->>'chunk_id')::uuid
                AND policy->'versions'->>v.document_version_id::text = d.knowledge_source_id::text) THEN
            RAISE EXCEPTION 'Chunk outside answer policy' USING ERRCODE = '23514';
        END IF;
        INSERT INTO public.retrieved_chunks(retrieval_operation_id, chunk_id, retrieval_rank, relevance_score, selected_for_context)
        VALUES(operation_id, (chunk->>'chunk_id')::uuid, rank, (chunk->>'score')::numeric, true);
    END LOOP;
    rank := 0;
    FOR citation IN SELECT * FROM jsonb_array_elements(reply->'source_references') LOOP
        rank := rank + 1;
        IF NOT EXISTS (SELECT 1 FROM public.retrieved_chunks c WHERE c.retrieval_operation_id = operation_id
            AND c.chunk_id = (citation->>'chunk_id')::uuid) THEN
            RAISE EXCEPTION 'Citation outside retrieved evidence' USING ERRCODE = '23514';
        END IF;
        INSERT INTO public.message_citations(message_id, retrieval_operation_id, chunk_id, display_order)
        VALUES(assistant, operation_id, (citation->>'chunk_id')::uuid, rank);
    END LOOP;
    receipt := reply || jsonb_build_object('message_id', assistant, 'model_used', NULL, 'metadata', '{}'::jsonb);
    UPDATE public.chat_turns SET state = 'completed', assistant_message_id = assistant, response = receipt,
        knowledge_policy = policy, updated_at = clock_timestamp() WHERE actor_id = actor AND client_turn_id = selected_turn;
    UPDATE public.conversations SET updated_at = clock_timestamp() WHERE conversation_id = item.conversation_id;
    RETURN public.read_chat_turn(actor, tenant, selected_turn);
END;
$$;

CREATE FUNCTION public.fail_chat_turn(actor uuid, tenant uuid, selected_turn uuid, token uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.require_chat_actor(actor, tenant);
    UPDATE public.chat_turns SET state = 'failed', updated_at = clock_timestamp()
        WHERE actor_id = actor AND client_turn_id = selected_turn AND institution_id = tenant
            AND worker_token = token AND state = 'processing';
END;
$$;
