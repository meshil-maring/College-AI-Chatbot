DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY['study_semesters', 'subjects'] LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres', relation_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role', relation_name);
        -- Browser roles have no policies; trusted reads remain tenant-filtered.
        -- The service role cannot mutate tables directly or delete records.
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', relation_name);
        EXECUTE format('CREATE TRIGGER academic_structure_validate BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.validate_academic_structure()', relation_name);
    END LOOP;
END;
$$;
ALTER FUNCTION public.validate_academic_structure() OWNER TO postgres;
ALTER FUNCTION public.guard_academic_structure_parent() OWNER TO postgres;
ALTER FUNCTION public.manage_academic_structure(uuid, uuid, text, uuid, jsonb) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.validate_academic_structure(),
    public.guard_academic_structure_parent(),
    public.manage_academic_structure(uuid, uuid, text, uuid, jsonb)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.manage_academic_structure(uuid, uuid, text, uuid, jsonb) TO service_role;
NOTIFY pgrst, 'reload schema';
