CREATE FUNCTION public.assign_student_semester(p_actor uuid,p_tenant uuid,p_student uuid,p_section uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE section_row jsonb; result public.student_semester_registrations; student_row record;
BEGIN
    PERFORM public.assert_academic_foundation_actor(p_actor,p_tenant,'courses');
    PERFORM public.assert_semester_registration_admin(p_actor,p_tenant,'students.update');
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||p_tenant::text,0));
    SELECT * INTO student_row FROM public.students
    WHERE student_id=p_student AND institution_id=p_tenant FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Student not found' USING ERRCODE='P0002'; END IF;
    IF student_row.approval_status<>'approved' OR NOT student_row.is_active OR student_row.status<>'active' THEN
        RAISE EXCEPTION 'Assign only approved active students' USING ERRCODE='23514';
    END IF;
    section_row:=public.academic_structure_parent('academic_sections',p_section,p_tenant);
    IF EXISTS(SELECT 1 FROM public.student_semester_registrations reg
        JOIN public.academic_sections sec USING(academic_section_id)
        WHERE reg.student_id=p_student AND sec.admission_cohort_id<>(section_row->>'admission_cohort_id')::uuid) THEN
        RAISE EXCEPTION 'Student already belongs to another batch; a transfer requires a separate workflow' USING ERRCODE='23514';
    END IF;
    SELECT * INTO result FROM public.student_semester_registrations
    WHERE student_id=p_student AND semester_id=(section_row->>'semester_id')::uuid FOR UPDATE;
    IF FOUND THEN
        IF result.academic_section_id=p_section THEN RETURN to_jsonb(result); END IF;
        IF result.status='registered' THEN
            RAISE EXCEPTION 'Completed registration cannot be reassigned' USING ERRCODE='P1004';
        END IF;
    END IF;
    IF (section_row->>'capacity') IS NOT NULL AND
       (SELECT count(*) FROM public.student_semester_registrations WHERE academic_section_id=p_section)
           >=(section_row->>'capacity')::integer THEN
        RAISE EXCEPTION 'Section capacity reached' USING ERRCODE='P1002';
    END IF;
    INSERT INTO public.student_semester_registrations(institution_id,student_id,academic_section_id,semester_id)
    VALUES(p_tenant,p_student,p_section,(section_row->>'semester_id')::uuid)
    ON CONFLICT(student_id,semester_id) DO UPDATE SET academic_section_id=EXCLUDED.academic_section_id,assigned_at=now()
    RETURNING * INTO result;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data)
    VALUES(p_actor,p_tenant,'academic.semester.assign','student_semester_registrations',result.semester_registration_id::text,
        jsonb_build_object('after',to_jsonb(result)));
    RETURN to_jsonb(result);
END;
$$;
