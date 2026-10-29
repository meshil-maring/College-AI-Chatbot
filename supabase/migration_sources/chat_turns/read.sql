CREATE FUNCTION public.read_chat_turn(actor uuid, tenant uuid, selected_turn uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE item public.chat_turns; conversation public.conversations;
BEGIN
    PERFORM public.require_chat_actor(actor, tenant);
    SELECT * INTO item FROM public.chat_turns t
        WHERE t.actor_id = actor AND t.client_turn_id = selected_turn AND t.institution_id = tenant;
    IF NOT FOUND THEN RAISE EXCEPTION 'Chat turn not found' USING ERRCODE = 'P0002'; END IF;
    SELECT * INTO conversation FROM public.conversations c
        WHERE c.conversation_id = item.conversation_id AND c.user_id = actor AND c.chat_institution_id = tenant;
    IF NOT FOUND THEN RAISE EXCEPTION 'Chat turn not found' USING ERRCODE = 'P0002'; END IF;
    IF conversation.knowledge_source_id IS NOT NULL THEN
        BEGIN
            PERFORM public.read_resource_chat_context(actor, tenant, conversation.knowledge_source_id);
        EXCEPTION WHEN no_data_found THEN
            RAISE EXCEPTION 'Source access changed' USING ERRCODE = '40001';
        END;
    END IF;
    IF item.state = 'completed' AND NOT public.check_knowledge_policy(actor, item.knowledge_policy) THEN
        RAISE EXCEPTION 'Source access changed' USING ERRCODE = '40001';
    END IF;
    RETURN public.chat_turn_view(item);
END;
$$;
