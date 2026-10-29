CREATE FUNCTION public.claim_chat_turn(actor uuid, tenant uuid, selected_turn uuid,
    selected_conversation uuid, selected_session uuid, query text, resource_id uuid DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE item public.chat_turns; conversation public.conversations; source_id uuid;
    message_id uuid := gen_random_uuid(); sequence integer;
BEGIN
    PERFORM public.require_chat_actor(actor, tenant);
    IF selected_turn IS NULL OR selected_conversation IS NULL OR selected_session IS NULL
        OR query IS NULL OR length(btrim(query)) NOT BETWEEN 1 AND 4000 THEN
        RAISE EXCEPTION 'Invalid turn request' USING ERRCODE = '22023';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('chat-turn:' || actor::text || ':' || selected_turn::text, 0));
    SELECT * INTO item FROM public.chat_turns t WHERE t.actor_id = actor AND t.client_turn_id = selected_turn FOR UPDATE;
    IF FOUND AND (item.institution_id <> tenant OR item.conversation_id <> selected_conversation
        OR item.request_query <> query OR item.session_id <> selected_session) THEN
        RAISE EXCEPTION 'Turn identifier was used for another request' USING ERRCODE = '22023';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended('chat-conversation:' || selected_conversation::text, 0));
    SELECT * INTO conversation FROM public.conversations c WHERE c.conversation_id = selected_conversation FOR UPDATE;
    IF FOUND THEN
        IF conversation.user_id <> actor OR (conversation.chat_institution_id IS NOT NULL AND conversation.chat_institution_id <> tenant) THEN
            RAISE EXCEPTION 'Conversation not found' USING ERRCODE = 'P0002';
        END IF;
        IF conversation.status <> 'active' OR (resource_id IS NOT NULL AND resource_id IS DISTINCT FROM conversation.knowledge_source_id) THEN
            RAISE EXCEPTION 'Conversation scope changed' USING ERRCODE = '40001';
        END IF;
        source_id := conversation.knowledge_source_id;
    ELSE
        source_id := resource_id;
    END IF;
    IF source_id IS NOT NULL THEN PERFORM public.read_resource_chat_context(actor, tenant, source_id); END IF;
    IF item.client_turn_id IS NOT NULL THEN
        IF source_id IS DISTINCT FROM item.knowledge_source_id THEN
            RAISE EXCEPTION 'Turn resource changed' USING ERRCODE = '22023';
        END IF;
        IF item.state = 'completed' OR (item.state = 'processing' AND item.lease_until > clock_timestamp()) THEN
            RETURN public.read_chat_turn(actor, tenant, selected_turn);
        END IF;
        UPDATE public.chat_turns SET state = 'processing', worker_token = gen_random_uuid(),
            lease_until = clock_timestamp() + interval '5 minutes', attempts = attempts + 1, updated_at = clock_timestamp()
            WHERE actor_id = actor AND client_turn_id = selected_turn RETURNING * INTO item;
    ELSE
        IF EXISTS (SELECT 1 FROM public.chat_turns t WHERE t.conversation_id = selected_conversation AND t.state <> 'completed') THEN
            RAISE EXCEPTION 'Recover the unfinished turn first' USING ERRCODE = 'PT409';
        END IF;
        IF conversation.conversation_id IS NULL THEN
            INSERT INTO public.conversations(conversation_id, user_id, title, knowledge_source_id, resource_institution_id, chat_institution_id)
                VALUES(selected_conversation, actor, left(query, 60), source_id, CASE WHEN source_id IS NOT NULL THEN tenant END, tenant);
        ELSIF conversation.chat_institution_id IS NULL THEN
            UPDATE public.conversations SET chat_institution_id = tenant WHERE conversation_id = selected_conversation;
        END IF;
        SELECT COALESCE(max(m.message_sequence), 0) + 1 INTO sequence FROM public.messages m WHERE m.conversation_id = selected_conversation;
        INSERT INTO public.chat_turns(actor_id, client_turn_id, institution_id, conversation_id, session_id, knowledge_source_id,
            request_query, user_message_id, user_sequence, state, worker_token, lease_until)
        VALUES(actor, selected_turn, tenant, selected_conversation, selected_session, source_id, query, message_id, sequence,
            'processing', gen_random_uuid(), clock_timestamp() + interval '5 minutes') RETURNING * INTO item;
        INSERT INTO public.messages(message_id, conversation_id, message_sequence, message_type, content_text)
            VALUES(message_id, selected_conversation, sequence, 'user', query);
    END IF;
    UPDATE public.conversations SET updated_at = clock_timestamp() WHERE conversation_id = selected_conversation;
    RETURN public.chat_turn_view(item) || jsonb_build_object('state', 'claimed', 'worker_token', item.worker_token,
        'user_sequence', item.user_sequence);
END;
$$;
