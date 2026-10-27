CREATE FUNCTION public.validate_academic_structure_relationships() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE item jsonb:=to_jsonb(NEW); parent jsonb; stage jsonb; cohort jsonb; section jsonb; active boolean;
BEGIN
    active:=CASE WHEN TG_TABLE_NAME='admission_cohorts' THEN item->>'status'='active' ELSE (item->>'is_active')::boolean END;
    -- Metadata edits and deactivation remain possible after parent deactivation.
    IF TG_OP='UPDATE' AND (NOT active OR (OLD.is_active AND NOT
        (TG_TABLE_NAME='curriculum_versions' AND item->>'status'='published' AND to_jsonb(OLD)->>'status'='draft')))
    THEN RETURN NEW; END IF;
    CASE TG_TABLE_NAME
    WHEN 'program_semesters' THEN
        PERFORM public.academic_structure_parent('programs',NEW.program_id,NEW.institution_id);
    WHEN 'curriculum_versions' THEN
        PERFORM public.academic_structure_parent('programs',NEW.program_id,NEW.institution_id);
        PERFORM public.academic_structure_parent('academic_years',NEW.academic_year_id,NEW.institution_id);
    WHEN 'curriculum_subjects' THEN
        parent:=public.academic_structure_parent('curriculum_versions',NEW.curriculum_version_id,NEW.institution_id);
        stage:=public.academic_structure_parent('program_semesters',NEW.program_semester_id,NEW.institution_id);
        PERFORM public.academic_structure_parent('courses',NEW.course_id,NEW.institution_id);
        IF parent->>'program_id' IS DISTINCT FROM stage->>'program_id'
           OR (stage->>'semester_number')::integer>(parent->>'total_semesters')::integer THEN
            RAISE EXCEPTION 'Curriculum and program semester must match' USING ERRCODE='23514';
        END IF;
    WHEN 'admission_cohorts' THEN
        PERFORM public.academic_structure_parent('programs',NEW.program_id,NEW.institution_id);
        PERFORM public.academic_structure_parent('academic_years',NEW.academic_year_id,NEW.institution_id);
        parent:=public.academic_structure_parent('curriculum_versions',NEW.curriculum_version_id,NEW.institution_id);
        IF parent->>'program_id' IS DISTINCT FROM NEW.program_id::text
           OR (TG_OP='INSERT' AND parent->>'status'<>'published') THEN
            RAISE EXCEPTION 'Matching published curriculum required' USING ERRCODE='23514';
        END IF;
    WHEN 'academic_sections' THEN
        cohort:=public.academic_structure_parent('admission_cohorts',NEW.admission_cohort_id,NEW.institution_id);
        stage:=public.academic_structure_parent('program_semesters',NEW.program_semester_id,NEW.institution_id);
        parent:=public.academic_structure_parent('curriculum_versions',(cohort->>'curriculum_version_id')::uuid,NEW.institution_id);
        PERFORM public.academic_structure_parent('semesters',NEW.semester_id,NEW.institution_id);
        IF cohort->>'program_id' IS DISTINCT FROM stage->>'program_id'
           OR (stage->>'semester_number')::integer>(parent->>'total_semesters')::integer THEN
            RAISE EXCEPTION 'Section must use its cohort program' USING ERRCODE='23514';
        END IF;
    WHEN 'academic_offerings' THEN
        section:=public.academic_structure_parent('academic_sections',NEW.academic_section_id,NEW.institution_id);
        parent:=public.academic_structure_parent('curriculum_subjects',NEW.curriculum_subject_id,NEW.institution_id);
        cohort:=public.academic_structure_parent('admission_cohorts',(section->>'admission_cohort_id')::uuid,NEW.institution_id);
        IF parent->>'curriculum_version_id' IS DISTINCT FROM cohort->>'curriculum_version_id'
           OR parent->>'program_semester_id' IS DISTINCT FROM section->>'program_semester_id' THEN
            RAISE EXCEPTION 'Offering must match section semester and assigned curriculum' USING ERRCODE='23514';
        END IF;
    END CASE;
    RETURN NEW;
END;
$$;
