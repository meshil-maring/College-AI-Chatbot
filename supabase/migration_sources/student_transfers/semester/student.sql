-- Students may only request sections with their current semester number.
CREATE OR REPLACE FUNCTION public.read_student_transfers(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_student uuid; v_registration public.student_semester_registrations;
    v_term public.semesters; v_open boolean;
BEGIN
    v_student := public.assert_transfer_student(p_actor, p_tenant, 'transfers.read');
    SELECT * INTO v_registration FROM public.student_semester_registrations
    WHERE semester_registration_id = public.transfer_current_registration(v_student, p_tenant);
    IF v_registration.semester_registration_id IS NULL THEN
        RETURN jsonb_build_object('institution_id', p_tenant, 'current', NULL,
            'options', '[]'::jsonb,
            'requests', public.transfer_requests_json(p_tenant, v_student, NULL, false));
    END IF;
    SELECT * INTO v_term FROM public.semesters WHERE semester_id = v_registration.semester_id;
    v_open := v_term.is_active AND v_term.end_date >= current_date;
    RETURN jsonb_build_object(
        'institution_id', p_tenant,
        'current', public.transfer_section_json(v_registration.academic_section_id, p_tenant)
            || jsonb_build_object(
                'semester_registration_id', v_registration.semester_registration_id,
                'registration_status', v_registration.status,
                'term_end_date', v_term.end_date, 'term_open', v_open),
        'options', CASE WHEN NOT v_open THEN '[]'::jsonb ELSE (
            SELECT COALESCE(jsonb_agg(option_row ORDER BY option_row->>'program_name',
                option_row->>'section_name', option_row->>'academic_section_id'), '[]'::jsonb)
            FROM (
                SELECT public.transfer_section_json(target.academic_section_id, p_tenant)
                    || jsonb_build_object(
                        'transfer_type', public.transfer_target_type(
                            v_registration.academic_section_id, target.academic_section_id, p_tenant),
                        'has_seat', public.transfer_section_has_seat(target.academic_section_id)
                    ) AS option_row
                FROM public.academic_sections target
                WHERE target.institution_id = p_tenant
                  AND target.semester_id = v_registration.semester_id
                  AND public.transfer_target_type(
                      v_registration.academic_section_id, target.academic_section_id, p_tenant) IS NOT NULL
                  AND public.transfer_stage_matches(v_registration.academic_section_id, target.academic_section_id)
            ) option_rows
        ) END,
        'requests', public.transfer_requests_json(p_tenant, v_student, NULL, false)
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.submit_student_transfer(
    p_actor uuid, p_tenant uuid, p_to_section uuid, p_reason text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_student uuid; v_registration public.student_semester_registrations; v_kind text;
    v_source jsonb; v_target jsonb; v_request public.student_transfer_requests;
BEGIN
    v_student := public.assert_transfer_student(p_actor, p_tenant, 'transfers.request');
    IF length(btrim(COALESCE(p_reason, ''))) NOT BETWEEN 10 AND 2000 THEN
        RAISE EXCEPTION 'Explain the transfer in 10 to 2000 characters' USING ERRCODE = 'P1108';
    END IF;
    -- Same tenant lock as section assignment, so seat counts cannot race.
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:' || p_tenant::text, 0));
    IF EXISTS (SELECT 1 FROM public.student_transfer_requests
               WHERE student_id = v_student AND status IN ('submitted', 'under_review')) THEN
        RAISE EXCEPTION 'An open transfer request already exists' USING ERRCODE = 'P1106';
    END IF;
    SELECT * INTO v_registration FROM public.student_semester_registrations
    WHERE semester_registration_id = public.transfer_current_registration(v_student, p_tenant)
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'The student has no current section' USING ERRCODE = 'P1107';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.semesters WHERE semester_id = v_registration.semester_id
                   AND is_active AND end_date >= current_date) THEN
        RAISE EXCEPTION 'The current term is closed' USING ERRCODE = 'P1103';
    END IF;
    v_kind := public.transfer_target_type(v_registration.academic_section_id, p_to_section, p_tenant);
    IF v_kind IS NULL THEN
        RAISE EXCEPTION 'The requested section is unavailable' USING ERRCODE = 'P1104';
    END IF;
    IF NOT public.transfer_stage_matches(v_registration.academic_section_id, p_to_section) THEN
        RAISE EXCEPTION 'Transfers must keep the same semester number' USING ERRCODE = 'P1113';
    END IF;
    IF NOT public.transfer_section_has_seat(p_to_section) THEN
        RAISE EXCEPTION 'The requested section is full' USING ERRCODE = 'P1105';
    END IF;
    v_source := public.transfer_section_json(v_registration.academic_section_id, p_tenant);
    v_target := public.transfer_section_json(p_to_section, p_tenant);
    INSERT INTO public.student_transfer_requests (
        institution_id, student_id, transfer_type, semester_registration_id, semester_id,
        from_section_id, to_section_id, from_program_id, to_program_id, to_department_id,
        reason, submitted_by)
    VALUES (p_tenant, v_student, v_kind, v_registration.semester_registration_id,
        v_registration.semester_id, v_registration.academic_section_id, p_to_section,
        (v_source->>'program_id')::uuid, (v_target->>'program_id')::uuid,
        (v_target->>'department_id')::uuid, btrim(p_reason), p_actor)
    RETURNING * INTO v_request;
    INSERT INTO public.student_transfer_events (institution_id, transfer_request_id, actor_user_id, action)
    VALUES (p_tenant, v_request.transfer_request_id, p_actor, 'submitted');
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.transfer.submit', 'student_transfer_requests',
        v_request.transfer_request_id::text, jsonb_build_object('after', to_jsonb(v_request)));
    RETURN jsonb_build_object('transfer_request_id', v_request.transfer_request_id,
        'institution_id', p_tenant, 'status', v_request.status);
END;
$$;
