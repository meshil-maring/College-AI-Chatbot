CREATE OR REPLACE FUNCTION "public"."academic_master_tenant"("p_entity" "text", "p_id" "uuid") RETURNS "uuid"
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
DECLARE result uuid;
BEGIN
    CASE p_entity
    WHEN 'departments' THEN SELECT d.institution_id INTO result FROM public.departments d WHERE d.department_id=p_id;
    WHEN 'academic_years' THEN SELECT y.institution_id INTO result FROM public.academic_years y WHERE y.academic_year_id=p_id;
    WHEN 'programs' THEN SELECT d.institution_id INTO result FROM public.programs p JOIN public.departments d USING(department_id) WHERE p.program_id=p_id;
    WHEN 'courses' THEN SELECT d.institution_id INTO result FROM public.courses c JOIN public.departments d USING(department_id) WHERE c.course_id=p_id;
    WHEN 'semesters' THEN SELECT y.institution_id INTO result FROM public.semesters s JOIN public.academic_years y USING(academic_year_id) WHERE s.semester_id=p_id;
    WHEN 'program_courses' THEN SELECT public.academic_master_tenant('programs', pc.program_id) INTO result FROM public.program_courses pc WHERE pc.program_course_id=p_id;
    WHEN 'course_offerings' THEN SELECT public.academic_master_tenant('courses', o.course_id) INTO result FROM public.course_offerings o WHERE o.course_offering_id=p_id;
    WHEN 'sections' THEN SELECT public.academic_master_tenant('course_offerings', s.course_offering_id) INTO result FROM public.sections s WHERE s.section_id=p_id;
    ELSE RAISE EXCEPTION 'Unknown academic entity' USING ERRCODE='22023';
    END CASE;
    RETURN result;
END;
$$;
