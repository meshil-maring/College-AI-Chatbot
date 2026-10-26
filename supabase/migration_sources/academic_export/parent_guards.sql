-- Serialize deactivation with the same lock used by the exported writer.
CREATE FUNCTION public.guard_export_academic_parent() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE owner uuid; blocked boolean := false;
BEGIN
    IF NEW.is_active OR NOT OLD.is_active THEN RETURN NEW; END IF;
    owner := public.academic_master_tenant(TG_TABLE_NAME,
        (to_jsonb(OLD)->>TG_ARGV[0])::uuid);
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:' || owner::text, 0));
    CASE TG_TABLE_NAME
    WHEN 'departments' THEN
        blocked := EXISTS(SELECT 1 FROM public.programs WHERE department_id=OLD.department_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.courses WHERE department_id=OLD.department_id AND is_active);
    WHEN 'programs' THEN
        blocked := EXISTS(SELECT 1 FROM public.program_courses WHERE program_id=OLD.program_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.course_offerings WHERE program_id=OLD.program_id AND is_active);
    WHEN 'courses' THEN
        blocked := EXISTS(SELECT 1 FROM public.program_courses WHERE course_id=OLD.course_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.course_offerings WHERE course_id=OLD.course_id AND is_active);
    WHEN 'academic_years' THEN
        blocked := EXISTS(SELECT 1 FROM public.semesters WHERE academic_year_id=OLD.academic_year_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.course_offerings WHERE academic_year_id=OLD.academic_year_id AND is_active);
    WHEN 'semesters' THEN
        blocked := EXISTS(SELECT 1 FROM public.program_courses WHERE semester_id=OLD.semester_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.course_offerings WHERE semester_id=OLD.semester_id AND is_active);
    WHEN 'program_courses' THEN
        blocked := EXISTS(SELECT 1 FROM public.course_offerings
            WHERE program_id=OLD.program_id AND course_id=OLD.course_id AND is_active);
    WHEN 'course_offerings' THEN
        blocked := EXISTS(SELECT 1 FROM public.sections WHERE course_offering_id=OLD.course_offering_id AND is_active);
    ELSE NULL;
    END CASE;
    IF blocked THEN
        RAISE EXCEPTION 'Deactivate dependent academic records first' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
