ALTER TABLE public.conversations ADD COLUMN chat_institution_id uuid
    REFERENCES public.institutions(institution_id);
ALTER TABLE public.conversations ADD CONSTRAINT conversations_owner_pair
    UNIQUE (conversation_id, user_id);
ALTER TABLE public.messages ADD CONSTRAINT messages_conversation_pair
    UNIQUE (message_id, conversation_id);

CREATE TABLE public.chat_turns (
    actor_id uuid NOT NULL REFERENCES public.users(id),
    client_turn_id uuid NOT NULL,
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    conversation_id uuid NOT NULL,
    session_id uuid NOT NULL,
    knowledge_source_id uuid REFERENCES public.knowledge_sources(knowledge_source_id),
    request_query text NOT NULL CHECK (length(btrim(request_query)) BETWEEN 1 AND 4000),
    user_message_id uuid NOT NULL,
    user_sequence integer NOT NULL CHECK (user_sequence > 0),
    assistant_message_id uuid,
    state text NOT NULL CHECK (state IN ('processing', 'failed', 'completed')),
    worker_token uuid NOT NULL,
    lease_until timestamptz NOT NULL,
    attempts integer NOT NULL DEFAULT 1 CHECK (attempts > 0),
    response jsonb,
    knowledge_policy jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (actor_id, client_turn_id),
    FOREIGN KEY (conversation_id, actor_id) REFERENCES public.conversations(conversation_id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (user_message_id, conversation_id) REFERENCES public.messages(message_id, conversation_id)
        DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (assistant_message_id, conversation_id) REFERENCES public.messages(message_id, conversation_id),
    CHECK ((state = 'completed') = (response IS NOT NULL AND assistant_message_id IS NOT NULL AND knowledge_policy IS NOT NULL))
);
CREATE UNIQUE INDEX chat_turns_one_unfinished ON public.chat_turns(conversation_id) WHERE state <> 'completed';
ALTER TABLE public.chat_turns ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.chat_turns FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON public.chat_turns TO service_role;

CREATE FUNCTION public.guard_managed_chat() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF TG_TABLE_NAME = 'conversations' THEN
        IF (TG_OP = 'UPDATE' AND NEW.chat_institution_id IS DISTINCT FROM OLD.chat_institution_id
            AND (OLD.chat_institution_id IS NOT NULL OR current_user <> 'postgres'))
            OR (TG_OP = 'INSERT' AND NEW.chat_institution_id IS NOT NULL AND current_user <> 'postgres') THEN
            RAISE EXCEPTION 'Chat institution is backend-owned and immutable' USING ERRCODE = '42501';
        END IF;
    ELSE
        PERFORM 1 FROM public.conversations c WHERE c.conversation_id = NEW.conversation_id FOR UPDATE;
        IF current_user <> 'postgres' AND EXISTS (
            SELECT 1 FROM public.chat_turns t WHERE t.conversation_id = NEW.conversation_id) THEN
            RAISE EXCEPTION 'Managed conversations require a chat turn' USING ERRCODE = '40001';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER managed_chat_scope BEFORE INSERT OR UPDATE ON public.conversations
    FOR EACH ROW EXECUTE FUNCTION public.guard_managed_chat();
CREATE TRIGGER managed_chat_messages BEFORE INSERT ON public.messages
    FOR EACH ROW EXECUTE FUNCTION public.guard_managed_chat();
