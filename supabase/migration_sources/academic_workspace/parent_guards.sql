-- Extend the existing guard without replacing it or weakening its old checks.
CREATE FUNCTION public.guard_academic_workspace_parent() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE blocked boolean:=false; item jsonb:=to_jsonb(NEW); tenant uuid;
BEGIN
    IF TG_TABLE_NAME='admission_cohorts' THEN
        IF NEW.status='active' OR OLD.status<>'active' THEN RETURN NEW; END IF;
    ELSIF NEW.is_active OR NOT OLD.is_active THEN RETURN NEW;
    END IF;
    IF TG_TABLE_NAME IN ('programs','courses','academic_years','semesters') THEN
        tenant:=public.academic_master_tenant(TG_TABLE_NAME,(to_jsonb(OLD)->>TG_ARGV[0])::uuid);
    ELSE tenant:=(item->>'institution_id')::uuid;
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||tenant::text,0));
    CASE TG_TABLE_NAME
    WHEN 'programs' THEN
        blocked:=EXISTS(SELECT 1 FROM public.program_semesters WHERE program_id=OLD.program_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.curriculum_versions WHERE program_id=OLD.program_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.admission_cohorts WHERE program_id=OLD.program_id AND is_active);
    WHEN 'courses' THEN
        blocked:=EXISTS(SELECT 1 FROM public.curriculum_subjects WHERE course_id=OLD.course_id AND is_active);
    WHEN 'academic_years' THEN
        blocked:=EXISTS(SELECT 1 FROM public.curriculum_versions WHERE academic_year_id=OLD.academic_year_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.admission_cohorts WHERE academic_year_id=OLD.academic_year_id AND is_active);
    WHEN 'semesters' THEN
        blocked:=EXISTS(SELECT 1 FROM public.academic_sections WHERE semester_id=OLD.semester_id AND is_active);
    WHEN 'program_semesters' THEN
        blocked:=EXISTS(SELECT 1 FROM public.curriculum_subjects WHERE program_semester_id=OLD.program_semester_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.academic_sections WHERE program_semester_id=OLD.program_semester_id AND is_active);
    WHEN 'curriculum_versions' THEN
        blocked:=EXISTS(SELECT 1 FROM public.admission_cohorts WHERE curriculum_version_id=OLD.curriculum_version_id AND is_active)
            OR EXISTS(SELECT 1 FROM public.curriculum_subjects WHERE curriculum_version_id=OLD.curriculum_version_id AND is_active);
    WHEN 'curriculum_subjects' THEN
        blocked:=EXISTS(SELECT 1 FROM public.academic_offerings WHERE curriculum_subject_id=OLD.curriculum_subject_id AND is_active);
    WHEN 'admission_cohorts' THEN
        blocked:=EXISTS(SELECT 1 FROM public.academic_sections WHERE admission_cohort_id=OLD.admission_cohort_id AND is_active);
    WHEN 'academic_sections' THEN
        blocked:=EXISTS(SELECT 1 FROM public.academic_offerings WHERE academic_section_id=OLD.academic_section_id AND is_active);
    ELSE NULL;
    END CASE;
    IF blocked THEN RAISE EXCEPTION 'Deactivate dependent academic records first' USING ERRCODE='23514'; END IF;
    RETURN NEW;
END;
$$;
