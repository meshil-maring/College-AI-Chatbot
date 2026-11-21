-- Approval re-checks the semester rule unless an administrator overrode it.
CREATE OR REPLACE FUNCTION public.transfer_apply(
    p_actor uuid, p_tenant uuid, p_request uuid, p_role text, p_comment text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_request public.student_transfer_requests; v_registration public.student_semester_registrations;
    v_enrollments jsonb;
BEGIN
    SELECT * INTO v_request FROM public.student_transfer_requests
    WHERE transfer_request_id = p_request AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transfer request not found' USING ERRCODE = 'P0002';
    END IF;
    SELECT * INTO v_registration FROM public.student_semester_registrations
    WHERE semester_registration_id = v_request.semester_registration_id AND institution_id = p_tenant
    FOR UPDATE;
    IF NOT FOUND OR v_registration.student_id <> v_request.student_id
       OR v_registration.academic_section_id <> v_request.from_section_id
       OR v_registration.semester_registration_id IS DISTINCT FROM
          public.transfer_current_registration(v_request.student_id, p_tenant) THEN
        RAISE EXCEPTION 'The student''s section changed after this request was submitted'
            USING ERRCODE = 'P1102';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.semesters WHERE semester_id = v_registration.semester_id
                   AND is_active AND end_date >= current_date) THEN
        RAISE EXCEPTION 'The current term is closed' USING ERRCODE = 'P1103';
    END IF;
    IF public.transfer_target_type(v_request.from_section_id, v_request.to_section_id, p_tenant)
       IS DISTINCT FROM v_request.transfer_type THEN
        RAISE EXCEPTION 'The requested section is unavailable' USING ERRCODE = 'P1104';
    END IF;
    -- Only an administrator's recorded override may change the semester number.
    IF NOT v_request.semester_override
       AND NOT public.transfer_stage_matches(v_request.from_section_id, v_request.to_section_id) THEN
        RAISE EXCEPTION 'Transfers must keep the same semester number' USING ERRCODE = 'P1113';
    END IF;
    IF NOT public.transfer_section_has_seat(v_request.to_section_id) THEN
        RAISE EXCEPTION 'The requested section is full' USING ERRCODE = 'P1105';
    END IF;
    SELECT COALESCE(jsonb_agg(soe.subject_snapshot || jsonb_build_object(
            'academic_offering_id', soe.academic_offering_id, 'enrolled_at', soe.enrolled_at)
        ORDER BY soe.enrolled_at, soe.offering_enrollment_id), '[]'::jsonb)
    INTO v_enrollments
    FROM public.student_offering_enrollments soe
    WHERE soe.semester_registration_id = v_registration.semester_registration_id;
    -- Offerings belong to the old section, so they cannot follow the student.
    DELETE FROM public.student_offering_enrollments
    WHERE semester_registration_id = v_registration.semester_registration_id;
    UPDATE public.student_semester_registrations
    SET academic_section_id = v_request.to_section_id, status = 'assigned',
        selected_option_ids = '{}'::uuid[], registered_at = NULL, assigned_at = now()
    WHERE semester_registration_id = v_registration.semester_registration_id;
    UPDATE public.student_transfer_requests
    SET status = 'approved', decided_by = p_actor, decided_at = now(), decided_as = p_role,
        decision_comment = p_comment, previous_registration = to_jsonb(v_registration),
        previous_enrollments = v_enrollments, updated_at = now()
    WHERE transfer_request_id = p_request;
END;
$$;
