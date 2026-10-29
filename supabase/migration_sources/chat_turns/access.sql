CREATE FUNCTION public.require_chat_actor(actor uuid, tenant uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' OR actor IS NULL OR tenant IS NULL
        OR cardinality(public.knowledge_actor_roles(actor, tenant, 'ai.chat')) = 0 THEN
        RAISE EXCEPTION 'Chat permission required' USING ERRCODE = '42501';
    END IF;
END;
$$;

CREATE FUNCTION public.chat_turn_view(item public.chat_turns) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    RETURN jsonb_build_object('turn_id', item.client_turn_id, 'conversation_id', item.conversation_id,
        'state', item.state, 'retryable', item.state = 'failed' OR
            (item.state = 'processing' AND item.lease_until <= clock_timestamp()),
        'retry_after_seconds', CASE WHEN item.state = 'processing'
            THEN greatest(0, ceil(extract(epoch FROM item.lease_until - clock_timestamp()))::integer) ELSE 0 END,
        'request', jsonb_build_object('turn_id', item.client_turn_id, 'user_query', item.request_query,
            'institution_id', item.institution_id, 'conversation_id', item.conversation_id,
            'session_id', item.session_id, 'resource_id', item.knowledge_source_id),
        'response', item.response);
END;
$$;
