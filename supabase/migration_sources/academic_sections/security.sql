DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY['class_sections', 'section_subject_assignments'] LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres', relation_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role', relation_name);
        -- Browser roles have no policies; trusted reads are tenant-filtered.
        -- All mutation requires the authorized RPC; hard deletes have no grant.
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', relation_name);
        EXECUTE format('CREATE TRIGGER academic_sections_validate BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.validate_academic_sections()', relation_name);
    END LOOP;
END;
$$;
ALTER FUNCTION public.validate_academic_sections() OWNER TO postgres;
ALTER FUNCTION public.guard_academic_sections_parent() OWNER TO postgres;
ALTER FUNCTION public.manage_academic_sections(uuid, uuid, text, uuid, jsonb) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.validate_academic_sections(),
    public.guard_academic_sections_parent(),
    public.manage_academic_sections(uuid, uuid, text, uuid, jsonb)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.manage_academic_sections(uuid, uuid, text, uuid, jsonb) TO service_role;
NOTIFY pgrst, 'reload schema';
