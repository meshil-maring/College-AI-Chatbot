-- Return an active, tenant-verified parent and verify its full ancestry.
CREATE FUNCTION public.academic_structure_parent(p_entity text, p_id uuid, p_institution uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result jsonb; id_column text;
BEGIN
    CASE p_entity
    WHEN 'departments' THEN id_column:='department_id';
    WHEN 'programs' THEN id_column:='program_id';
    WHEN 'academic_years' THEN id_column:='academic_year_id';
    WHEN 'semesters' THEN id_column:='semester_id';
    WHEN 'courses' THEN id_column:='course_id';
    WHEN 'program_semesters' THEN id_column:='program_semester_id';
    WHEN 'curriculum_versions' THEN id_column:='curriculum_version_id';
    WHEN 'curriculum_subjects' THEN id_column:='curriculum_subject_id';
    WHEN 'admission_cohorts' THEN id_column:='admission_cohort_id';
    WHEN 'academic_sections' THEN id_column:='academic_section_id';
    ELSE RAISE EXCEPTION 'Unsupported parent' USING ERRCODE='22023';
    END CASE;
    IF p_entity IN ('departments','programs','academic_years','semesters','courses') THEN
        IF public.academic_master_tenant(p_entity,p_id) IS DISTINCT FROM p_institution THEN
            RAISE EXCEPTION 'Academic parent not found' USING ERRCODE='P0002';
        END IF;
        EXECUTE format('SELECT to_jsonb(t) FROM public.%I t WHERE %I=$1',p_entity,id_column) INTO result USING p_id;
    ELSE
        EXECUTE format('SELECT to_jsonb(t) FROM public.%I t WHERE %I=$1 AND institution_id=$2',p_entity,id_column)
            INTO result USING p_id,p_institution;
    END IF;
    IF result IS NULL THEN RAISE EXCEPTION 'Academic parent not found' USING ERRCODE='P0002'; END IF;
    IF NOT (result->>'is_active')::boolean THEN
        RAISE EXCEPTION 'Active academic ancestry required' USING ERRCODE='23514';
    END IF;
    CASE p_entity
    WHEN 'programs','courses' THEN
        PERFORM public.academic_structure_parent('departments',(result->>'department_id')::uuid,p_institution);
    WHEN 'semesters' THEN
        PERFORM public.academic_structure_parent('academic_years',(result->>'academic_year_id')::uuid,p_institution);
    WHEN 'program_semesters','curriculum_versions','admission_cohorts' THEN
        PERFORM public.academic_structure_parent('programs',(result->>'program_id')::uuid,p_institution);
        IF p_entity<>'program_semesters' THEN
            PERFORM public.academic_structure_parent('academic_years',(result->>'academic_year_id')::uuid,p_institution);
        END IF;
        IF p_entity='admission_cohorts' THEN
            PERFORM public.academic_structure_parent('curriculum_versions',(result->>'curriculum_version_id')::uuid,p_institution);
        END IF;
    WHEN 'curriculum_subjects' THEN
        PERFORM public.academic_structure_parent('curriculum_versions',(result->>'curriculum_version_id')::uuid,p_institution);
        PERFORM public.academic_structure_parent('program_semesters',(result->>'program_semester_id')::uuid,p_institution);
        PERFORM public.academic_structure_parent('courses',(result->>'course_id')::uuid,p_institution);
    WHEN 'academic_sections' THEN
        PERFORM public.academic_structure_parent('admission_cohorts',(result->>'admission_cohort_id')::uuid,p_institution);
        PERFORM public.academic_structure_parent('program_semesters',(result->>'program_semester_id')::uuid,p_institution);
        PERFORM public.academic_structure_parent('semesters',(result->>'semester_id')::uuid,p_institution);
    ELSE NULL;
    END CASE;
    RETURN result;
END;
$$;
