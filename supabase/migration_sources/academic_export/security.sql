DO $$
DECLARE relation_name text; id_column text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'departments','programs','academic_years','semesters',
        'courses','program_courses','course_offerings','sections'
    ] LOOP
        id_column := CASE relation_name WHEN 'academic_years' THEN 'academic_year_id'
            ELSE regexp_replace(relation_name, 's$', '') || '_id' END;
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres', relation_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role', relation_name);
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', relation_name);
        EXECUTE format('CREATE TRIGGER academic_master_validate BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.validate_academic_master_record()', relation_name);
        EXECUTE format('CREATE TRIGGER academic_parent_guard BEFORE UPDATE OF is_active ON public.%I FOR EACH ROW EXECUTE FUNCTION public.guard_export_academic_parent(%L)', relation_name, id_column);
    END LOOP;
END;
$$;
REVOKE ALL ON FUNCTION public.academic_master_tenant(text, uuid),
    public.validate_academic_master_record(), public.guard_export_academic_parent(),
    public.manage_academic_master_record(uuid, uuid, text, uuid, jsonb)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.manage_academic_master_record(uuid, uuid, text, uuid, jsonb) TO service_role;
NOTIFY pgrst, 'reload schema';
