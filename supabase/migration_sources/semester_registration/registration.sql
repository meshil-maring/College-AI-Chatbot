CREATE FUNCTION public.complete_student_semester(
    p_actor uuid,p_tenant uuid,p_registration uuid,p_options uuid[]
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE resolved_student uuid; registration public.student_semester_registrations;
    section_row jsonb; cohort_row jsonb; offering record; required_ids uuid[];
    chosen_ids uuid[]; group_count integer; enrolled_count integer:=0; canonical_options uuid[];
BEGIN
    resolved_student:=public.assert_semester_registration_student(p_actor,p_tenant,'manage');
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    SELECT * INTO registration FROM public.student_semester_registrations reg
    WHERE reg.semester_registration_id=p_registration AND reg.student_id=resolved_student AND reg.institution_id=p_tenant
    FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Assigned semester not found' USING ERRCODE='P0002'; END IF;
    SELECT COALESCE(array_agg(item ORDER BY item),'{}'::uuid[]) INTO canonical_options FROM unnest(p_options) item;
    IF registration.status='registered' THEN
        IF registration.selected_option_ids=canonical_options THEN RETURN to_jsonb(registration); END IF;
        RAISE EXCEPTION 'Registration is already complete' USING ERRCODE='P1004';
    END IF;
    section_row:=public.academic_structure_parent('academic_sections',registration.academic_section_id,p_tenant);
    cohort_row:=public.academic_structure_parent('admission_cohorts',(section_row->>'admission_cohort_id')::uuid,p_tenant);
    IF EXISTS(SELECT 1 FROM public.semesters WHERE semester_id=registration.semester_id AND end_date<current_date) THEN
        RAISE EXCEPTION 'The teaching term has ended' USING ERRCODE='P1001';
    END IF;
    SELECT count(*) INTO group_count FROM public.curriculum_choice_groups
    WHERE curriculum_version_id=(cohort_row->>'curriculum_version_id')::uuid
      AND program_semester_id=(section_row->>'program_semester_id')::uuid;
    IF cardinality(p_options) IS DISTINCT FROM group_count OR EXISTS(
        SELECT 1 FROM public.curriculum_choice_groups g
        WHERE g.curriculum_version_id=(cohort_row->>'curriculum_version_id')::uuid
          AND g.program_semester_id=(section_row->>'program_semester_id')::uuid
          AND (SELECT count(*) FROM public.curriculum_choice_options co
               WHERE co.choice_group_id=g.choice_group_id AND co.choice_option_id=ANY(p_options))<>1
    ) OR (SELECT count(DISTINCT item) FROM unnest(p_options) item)<>group_count THEN
        RAISE EXCEPTION 'Choose exactly one complete option per group' USING ERRCODE='P1003';
    END IF;
    SELECT COALESCE(array_agg(curriculum_subject_id),'{}'::uuid[]) INTO required_ids
    FROM public.curriculum_subjects WHERE curriculum_version_id=(cohort_row->>'curriculum_version_id')::uuid
      AND program_semester_id=(section_row->>'program_semester_id')::uuid AND is_active AND is_required;
    SELECT ARRAY(SELECT DISTINCT item FROM unnest(required_ids||ARRAY(
        SELECT curriculum_subject_id FROM public.curriculum_choice_subjects WHERE choice_option_id=ANY(p_options)
    )) item) INTO chosen_ids;
    IF cardinality(chosen_ids)=0 THEN
        RAISE EXCEPTION 'No subjects are configured for registration' USING ERRCODE='P1001';
    END IF;
    FOR offering IN SELECT ao.*,to_jsonb(c) AS snapshot FROM public.academic_offerings ao
        JOIN public.curriculum_subjects cs USING(curriculum_subject_id)
        JOIN public.courses c USING(course_id)
        WHERE ao.academic_section_id=registration.academic_section_id AND ao.institution_id=p_tenant
          AND ao.is_active AND cs.curriculum_subject_id=ANY(chosen_ids)
        ORDER BY ao.academic_offering_id LOOP
        PERFORM public.academic_structure_parent('curriculum_subjects',offering.curriculum_subject_id,p_tenant);
        IF offering.capacity IS NOT NULL AND
           (SELECT count(*) FROM public.student_offering_enrollments WHERE academic_offering_id=offering.academic_offering_id)>=offering.capacity THEN
            RAISE EXCEPTION 'A selected subject has reached capacity' USING ERRCODE='P1002';
        END IF;
        INSERT INTO public.student_offering_enrollments(institution_id,semester_registration_id,academic_offering_id,subject_snapshot)
        VALUES(p_tenant,p_registration,offering.academic_offering_id,
            jsonb_build_object('course_id',offering.snapshot->'course_id','name',offering.snapshot->'name',
                'code',offering.snapshot->'code','credits',offering.snapshot->'credits'));
        enrolled_count:=enrolled_count+1;
    END LOOP;
    IF enrolled_count<>cardinality(chosen_ids) THEN
        RAISE EXCEPTION 'All subjects in the selection must have active offerings' USING ERRCODE='P1001';
    END IF;
    UPDATE public.student_semester_registrations SET status='registered',selected_option_ids=canonical_options,registered_at=now()
    WHERE semester_registration_id=p_registration RETURNING * INTO registration;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data)
    VALUES(p_actor,p_tenant,'academic.semester.register','student_semester_registrations',p_registration::text,
        jsonb_build_object('after',to_jsonb(registration),'subject_count',enrolled_count));
    RETURN to_jsonb(registration);
END;
$$;
