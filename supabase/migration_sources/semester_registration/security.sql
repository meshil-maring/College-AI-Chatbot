DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY['curriculum_choice_groups','curriculum_choice_options',
        'curriculum_choice_subjects','student_semester_registrations','student_offering_enrollments'] LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO postgres',relation_name);
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',relation_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC,anon,authenticated,service_role',relation_name);
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role',relation_name);
    END LOOP;
    FOREACH relation_name IN ARRAY ARRAY['curriculum_versions','curriculum_subjects','academic_sections','academic_offerings'] LOOP
        EXECUTE format('CREATE TRIGGER registration_structure_guard BEFORE UPDATE ON public.%I
            FOR EACH ROW EXECUTE FUNCTION public.guard_semester_registration_structure()',relation_name);
    END LOOP;
END;
$$;
REVOKE ALL ON FUNCTION public.assert_semester_registration_admin(uuid,uuid,text),
    public.assert_semester_registration_student(uuid,uuid,text),
    public.curriculum_choices_json(uuid,uuid,uuid),public.guard_semester_registration_structure(),
    public.read_curriculum_choices(uuid,uuid),public.read_student_semesters(uuid,uuid),
    public.manage_curriculum_choice_group(uuid,uuid,uuid,jsonb,boolean),
    public.assign_student_semester(uuid,uuid,uuid,uuid),
    public.complete_student_semester(uuid,uuid,uuid,uuid[])
    FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.read_curriculum_choices(uuid,uuid),public.read_student_semesters(uuid,uuid),
    public.manage_curriculum_choice_group(uuid,uuid,uuid,jsonb,boolean),
    public.assign_student_semester(uuid,uuid,uuid,uuid),
    public.complete_student_semester(uuid,uuid,uuid,uuid[]) TO service_role;
NOTIFY pgrst,'reload schema';
