REVOKE ALL ON FUNCTION public.guard_managed_chat(), public.require_chat_actor(uuid,uuid),
    public.chat_turn_view(public.chat_turns), public.read_chat_turn(uuid,uuid,uuid),
    public.claim_chat_turn(uuid,uuid,uuid,uuid,uuid,text,uuid),
    public.complete_chat_turn(uuid,uuid,uuid,uuid,jsonb,jsonb,jsonb), public.fail_chat_turn(uuid,uuid,uuid,uuid)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.read_chat_turn(uuid,uuid,uuid),
    public.claim_chat_turn(uuid,uuid,uuid,uuid,uuid,text,uuid),
    public.complete_chat_turn(uuid,uuid,uuid,uuid,jsonb,jsonb,jsonb), public.fail_chat_turn(uuid,uuid,uuid,uuid)
    TO service_role;
COMMENT ON TABLE public.chat_turns IS
    'Owned durable turn receipts and fenced worker leases; checked against current tenant, role and knowledge access on every recovery.';
