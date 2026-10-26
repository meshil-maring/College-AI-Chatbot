DO $$
DECLARE entity text;
BEGIN
    FOREACH entity IN ARRAY ARRAY['departments', 'programs', 'academic_years'] LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres', entity);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', entity);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role', entity);
        -- Reads are tenant-filtered by the backend repository. All mutations
        -- require the actor-checked, audited SECURITY DEFINER entry point.
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', entity);
        EXECUTE format('CREATE TRIGGER academic_foundation_validate BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.validate_academic_foundation()', entity);
    END LOOP;
END;
$$;
ALTER FUNCTION public.assert_academic_foundation_actor(uuid, uuid, text) OWNER TO postgres;
ALTER FUNCTION public.validate_academic_foundation() OWNER TO postgres;
ALTER FUNCTION public.manage_academic_foundation(uuid, uuid, text, uuid, jsonb) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.assert_academic_foundation_actor(uuid, uuid, text),
    public.validate_academic_foundation(),
    public.manage_academic_foundation(uuid, uuid, text, uuid, jsonb)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.manage_academic_foundation(uuid, uuid, text, uuid, jsonb) TO service_role;
NOTIFY pgrst, 'reload schema';
