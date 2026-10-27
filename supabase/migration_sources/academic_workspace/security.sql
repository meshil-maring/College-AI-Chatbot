DO $$
DECLARE relation_name text; id_column text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY[
        'program_semesters','curriculum_versions','curriculum_subjects',
        'admission_cohorts','academic_sections','academic_offerings'
    ] LOOP
        id_column:=regexp_replace(relation_name,'s$','')||'_id';
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres',relation_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role',relation_name);
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role',relation_name);
        EXECUTE format('CREATE TRIGGER structure_lifecycle BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.validate_academic_structure_lifecycle()',relation_name);
        EXECUTE format('CREATE TRIGGER structure_relationships BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.validate_academic_structure_relationships()',relation_name);
        EXECUTE format('CREATE TRIGGER structure_parent_guard BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.guard_academic_workspace_parent(%L)',relation_name,id_column);
    END LOOP;
    FOREACH relation_name IN ARRAY ARRAY['programs','courses','academic_years','semesters'] LOOP
        id_column:=CASE relation_name WHEN 'academic_years' THEN 'academic_year_id'
            ELSE regexp_replace(relation_name,'s$','')||'_id' END;
        EXECUTE format('CREATE TRIGGER structure_parent_guard BEFORE UPDATE OF is_active ON public.%I FOR EACH ROW EXECUTE FUNCTION public.guard_academic_workspace_parent(%L)',relation_name,id_column);
    END LOOP;
END;
$$;
REVOKE ALL ON FUNCTION public.academic_structure_parent(text,uuid,uuid),
    public.validate_academic_structure_relationships(), public.validate_academic_structure_lifecycle(),
    public.guard_academic_workspace_parent(),
    public.manage_academic_structure_record(uuid,uuid,text,uuid,jsonb)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.manage_academic_structure_record(uuid,uuid,text,uuid,jsonb) TO service_role;
NOTIFY pgrst,'reload schema';
