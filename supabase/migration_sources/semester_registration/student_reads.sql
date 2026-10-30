CREATE FUNCTION public.curriculum_choices_json(p_tenant uuid,p_version uuid DEFAULT NULL,p_stage uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path='' AS $$
    SELECT COALESCE(jsonb_agg(to_jsonb(g)||jsonb_build_object('options',(
        SELECT COALESCE(jsonb_agg(to_jsonb(co)||jsonb_build_object('curriculum_subject_ids',(
            SELECT COALESCE(jsonb_agg(cs.curriculum_subject_id ORDER BY cs.curriculum_subject_id),'[]'::jsonb)
            FROM public.curriculum_choice_subjects cs WHERE cs.choice_option_id=co.choice_option_id
        )) ORDER BY co.name,co.choice_option_id),'[]'::jsonb)
        FROM public.curriculum_choice_options co WHERE co.choice_group_id=g.choice_group_id
    )) ORDER BY g.name,g.choice_group_id),'[]'::jsonb)
    FROM public.curriculum_choice_groups g WHERE g.institution_id=p_tenant
      AND (p_version IS NULL OR g.curriculum_version_id=p_version)
      AND (p_stage IS NULL OR g.program_semester_id=p_stage);
$$;

CREATE FUNCTION public.read_curriculum_choices(p_actor uuid,p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'courses.read');
    RETURN public.curriculum_choices_json(p_tenant);
END;
$$;

CREATE FUNCTION public.read_student_semesters(p_actor uuid,p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE resolved_student uuid; result jsonb;
BEGIN
    resolved_student:=public.assert_semester_registration_student(p_actor,p_tenant,'read');
    SELECT COALESCE(jsonb_agg(to_jsonb(reg)||jsonb_build_object(
        'section_name',sec.name,'batch_name',cohort.name,'program_name',program.name,
        'program_semester_name',stage.name,'term_name',term.name,
        'start_date',term.start_date,'end_date',term.end_date,
        'groups',public.curriculum_choices_json(p_tenant,cohort.curriculum_version_id,sec.program_semester_id),
        'subjects',(
            SELECT COALESCE(jsonb_agg(jsonb_build_object(
                'curriculum_subject_id',cs.curriculum_subject_id,'name',c.name,'code',c.code,
                'credits',c.credits,'is_required',cs.is_required,
                'academic_offering_id',ao.academic_offering_id,
                'available',COALESCE(ao.is_active AND c.is_active AND sec.is_active AND cohort.is_active
                    AND term.is_active AND term.end_date>=current_date AND (
                        ao.capacity IS NULL OR (SELECT count(*) FROM public.student_offering_enrollments soe
                        WHERE soe.academic_offering_id=ao.academic_offering_id)<ao.capacity
                    ),false)
            ) ORDER BY c.name,cs.curriculum_subject_id),'[]'::jsonb)
            FROM public.curriculum_subjects cs JOIN public.courses c USING(course_id)
            LEFT JOIN public.academic_offerings ao ON ao.curriculum_subject_id=cs.curriculum_subject_id
                AND ao.academic_section_id=sec.academic_section_id
            WHERE cs.curriculum_version_id=cohort.curriculum_version_id
                AND cs.program_semester_id=sec.program_semester_id AND cs.is_active
        ),
        'enrolled_subjects',(
            SELECT COALESCE(jsonb_agg(soe.subject_snapshot ORDER BY soe.subject_snapshot->>'name'),'[]'::jsonb)
            FROM public.student_offering_enrollments soe WHERE soe.semester_registration_id=reg.semester_registration_id
        )
    ) ORDER BY term.start_date DESC,reg.semester_registration_id),'[]'::jsonb) INTO result
    FROM public.student_semester_registrations reg
    JOIN public.academic_sections sec USING(academic_section_id)
    JOIN public.admission_cohorts cohort USING(admission_cohort_id)
    JOIN public.programs program ON program.program_id=cohort.program_id
    JOIN public.program_semesters stage ON stage.program_semester_id=sec.program_semester_id
    JOIN public.semesters term ON term.semester_id=reg.semester_id
    WHERE reg.student_id=resolved_student AND reg.institution_id=p_tenant;
    RETURN jsonb_build_object('institution_id',p_tenant,'items',result);
END;
$$;
