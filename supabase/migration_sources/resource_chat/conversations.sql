ALTER TABLE public.conversations
    ADD COLUMN knowledge_source_id uuid,
    ADD COLUMN resource_institution_id uuid,
    ADD CONSTRAINT conversation_resource_pair CHECK (
        (knowledge_source_id IS NULL) = (resource_institution_id IS NULL)),
    ADD CONSTRAINT conversation_resource_scope FOREIGN KEY (knowledge_source_id, resource_institution_id)
        REFERENCES public.knowledge_sources(knowledge_source_id, institution_id);

CREATE FUNCTION public.guard_conversation_resource_scope() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND ROW(NEW.knowledge_source_id, NEW.resource_institution_id, NEW.user_id)
        IS DISTINCT FROM ROW(OLD.knowledge_source_id, OLD.resource_institution_id, OLD.user_id) THEN
        RAISE EXCEPTION 'Conversation scope and owner are immutable' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'INSERT' AND NEW.knowledge_source_id IS NOT NULL THEN
        PERFORM public.read_resource_chat_context(NEW.user_id, NEW.resource_institution_id, NEW.knowledge_source_id);
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.guard_conversation_resource_scope() FROM PUBLIC, anon, authenticated, service_role;
CREATE TRIGGER conversation_resource_scope_guard BEFORE INSERT OR UPDATE ON public.conversations
    FOR EACH ROW EXECUTE FUNCTION public.guard_conversation_resource_scope();
CREATE INDEX conversations_resource_source_idx ON public.conversations(knowledge_source_id)
    WHERE knowledge_source_id IS NOT NULL;
COMMENT ON COLUMN public.conversations.knowledge_source_id IS
    'Immutable resource context; NULL retains ordinary institution chat. Access is rechecked each turn and history read.';
