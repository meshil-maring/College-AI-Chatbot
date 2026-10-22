CREATE FUNCTION public.academic_package_offering_eligibility(p_actor_user_id uuid, p_institution_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result jsonb;
BEGIN
    PERFORM public.academic_package_require(p_actor_user_id, p_institution_id, 'courses.read');
    SELECT COALESCE(jsonb_agg(row), '[]'::jsonb) INTO result FROM (
        SELECT DISTINCT batch.program_id, subject.course_id, cl.semester_id, 'named_curriculum'::text AS source
        FROM public.academic_classes cl
        JOIN public.academic_batches batch ON batch.batch_id = cl.batch_id
        JOIN public.programs program ON program.program_id = batch.program_id
        JOIN public.departments program_department ON program_department.department_id = program.department_id
        JOIN public.academic_curricula curriculum ON curriculum.curriculum_id = cl.curriculum_id
        JOIN public.academic_curriculum_subjects subject ON subject.curriculum_id = curriculum.curriculum_id
            AND subject.study_semester = cl.study_semester
        JOIN public.courses course ON course.course_id = subject.course_id
        JOIN public.departments subject_department ON subject_department.department_id = course.department_id
        JOIN public.semesters term ON term.semester_id = cl.semester_id
        JOIN public.academic_years year ON year.academic_year_id = term.academic_year_id
        WHERE cl.institution_id = p_institution_id AND batch.institution_id = p_institution_id
          AND curriculum.institution_id = p_institution_id AND program_department.institution_id = p_institution_id
          AND subject_department.institution_id = p_institution_id AND year.institution_id = p_institution_id
          AND curriculum.program_id = batch.program_id AND batch.is_active AND program.is_active
          AND program_department.is_active AND course.is_active AND subject_department.is_active
          AND term.is_active AND year.is_active
    ) row;
    IF jsonb_array_length(result) > 5000 THEN
        RAISE EXCEPTION 'Offering eligibility exceeds 5000 active triples; archive inactive academic periods'
            USING ERRCODE = '22023';
    END IF;
    RETURN result;
END;
$$;
