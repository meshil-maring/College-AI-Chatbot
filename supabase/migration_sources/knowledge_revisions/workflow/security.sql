-- Helpers are never exposed as separate actor-selectable browser capabilities.
-- Indexing writes use trigger-owned access only to advance/check revision
-- invariants; direct application table mutation remains denied.
-- Deferred checks run after the writer's SECURITY DEFINER context has ended.
-- Own their helper calls without granting direct helper execution to the caller.
ALTER FUNCTION public.check_knowledge_revision_integrity() SECURITY DEFINER;
ALTER FUNCTION public.check_knowledge_source_revision() SECURITY DEFINER;
ALTER FUNCTION public.guard_knowledge_manifest_version() SECURITY DEFINER;
ALTER FUNCTION public.check_knowledge_manifest_version() SECURITY DEFINER;
ALTER FUNCTION public.check_knowledge_manifest_run() SECURITY DEFINER;
ALTER FUNCTION public.guard_knowledge_manifest_run() SECURITY DEFINER;
REVOKE ALL ON FUNCTION
    public.knowledge_actor_roles(uuid,uuid,text), public.assert_knowledge_actor(uuid,uuid,text,boolean),
    public.audit_knowledge_revision(uuid,uuid,text,uuid,jsonb), public.knowledge_revision_view(uuid),
    public.read_knowledge_revisions(uuid,uuid,text,uuid,integer,integer),
    public.save_knowledge_draft(uuid,uuid,jsonb,uuid,uuid,bigint),
    public.register_knowledge_upload(uuid,uuid,uuid,bigint,jsonb,uuid),
    public.retry_knowledge_index(uuid,uuid,uuid,bigint,uuid),
    public.decide_knowledge_revision(uuid,uuid,uuid,text,bigint,bigint,text),
    public.knowledge_source_allowed(uuid,uuid,uuid,text), public.knowledge_version_allowed(uuid,uuid),
    public.read_knowledge_resources(uuid,uuid,uuid,integer,integer,text[]),
    public.search_audience_knowledge_chunks(uuid,extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text),
    public.search_public_knowledge_chunks(extensions.vector,integer,uuid,uuid,text),
    public.guard_message_knowledge_policy(), public.check_knowledge_policy(uuid,jsonb),
    public.snapshot_knowledge_policy(uuid,uuid,uuid[],jsonb), public.snapshot_public_knowledge_policy(text),
    public.assert_legacy_knowledge_delete(uuid,uuid,uuid), public.guard_knowledge_index_content()
FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION
    public.read_knowledge_revisions(uuid,uuid,text,uuid,integer,integer),
    public.save_knowledge_draft(uuid,uuid,jsonb,uuid,uuid,bigint),
    public.register_knowledge_upload(uuid,uuid,uuid,bigint,jsonb,uuid),
    public.retry_knowledge_index(uuid,uuid,uuid,bigint,uuid),
    public.decide_knowledge_revision(uuid,uuid,uuid,text,bigint,bigint,text),
    public.read_knowledge_resources(uuid,uuid,uuid,integer,integer,text[]),
    public.search_audience_knowledge_chunks(uuid,extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text),
    public.search_public_knowledge_chunks(extensions.vector,integer,uuid,uuid,text),
    public.check_knowledge_policy(uuid,jsonb), public.snapshot_knowledge_policy(uuid,uuid,uuid[],jsonb),
    public.snapshot_public_knowledge_policy(text), public.assert_legacy_knowledge_delete(uuid,uuid,uuid)
TO service_role;
