-- Administrators see and may choose other semesters with explicit consent;
-- Heads of Department keep the strict same-semester rule.
CREATE OR REPLACE FUNCTION public.read_direct_transfer_options(p_actor uuid, p_tenant uuid, p_student uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_role text; v_departments uuid[]; v_registration public.student_semester_registrations;
    v_current jsonb;
BEGIN
    PERFORM public.assert_transfer_backend();
    v_role := public.transfer_direct_role(p_actor, p_tenant);
    IF v_role IS NULL THEN
        RAISE EXCEPTION 'Administrator or Head of Department required' USING ERRCODE = '42501';
    END IF;
    IF v_role = 'hod' THEN
        v_departments := public.transfer_hod_departments(p_actor, p_tenant);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.students WHERE student_id = p_student AND institution_id = p_tenant
                   AND is_active AND status = 'active' AND approval_status = 'approved') THEN
        RAISE EXCEPTION 'Student not found' USING ERRCODE = 'P0002';
    END IF;
    SELECT * INTO v_registration FROM public.student_semester_registrations
    WHERE semester_registration_id = public.transfer_current_registration(p_student, p_tenant);
    IF v_registration.semester_registration_id IS NULL THEN
        RAISE EXCEPTION 'The student has no current section' USING ERRCODE = 'P1112';
    END IF;
    v_current := public.transfer_section_json(v_registration.academic_section_id, p_tenant);
    IF v_departments IS NOT NULL AND NOT (v_current->>'department_id')::uuid = ANY (v_departments) THEN
        RAISE EXCEPTION 'This student is outside your department' USING ERRCODE = '42501';
    END IF;
    RETURN jsonb_build_object(
        'institution_id', p_tenant, 'student_id', p_student, 'actor_role', v_role,
        'can_override_semester', v_role = 'admin',
        'current', v_current || jsonb_build_object(
            'semester_registration_id', v_registration.semester_registration_id,
            'registration_status', v_registration.status),
        'has_open_request', EXISTS (
            SELECT 1 FROM public.student_transfer_requests
            WHERE student_id = p_student AND status IN ('submitted', 'under_review')),
        'options', (
            SELECT COALESCE(jsonb_agg(option_row ORDER BY option_row->>'program_name',
                option_row->>'section_name', option_row->>'academic_section_id'), '[]'::jsonb)
            FROM (
                SELECT public.transfer_section_json(target.academic_section_id, p_tenant)
                    || jsonb_build_object(
                        'transfer_type', public.transfer_target_type(
                            v_registration.academic_section_id, target.academic_section_id, p_tenant),
                        'has_seat', public.transfer_section_has_seat(target.academic_section_id),
                        'same_semester', public.transfer_stage_matches(
                            v_registration.academic_section_id, target.academic_section_id)
                    ) AS option_row
                FROM public.academic_sections target
                WHERE target.institution_id = p_tenant
                  AND target.semester_id = v_registration.semester_id
                  AND public.transfer_target_type(
                      v_registration.academic_section_id, target.academic_section_id, p_tenant) IS NOT NULL
            ) option_rows
            WHERE (v_departments IS NULL OR (option_row->>'department_id')::uuid = ANY (v_departments))
              -- Other semesters are listed only for an administrator to override.
              AND (v_role = 'admin' OR (option_row->>'same_semester')::boolean)
        )
    );
END;
$$;

-- The direct command gains an explicit override flag; the old signature is removed.
DROP FUNCTION public.direct_transfer_student(uuid, uuid, uuid, uuid, text);

CREATE FUNCTION public.direct_transfer_student(
    p_actor uuid, p_tenant uuid, p_student uuid, p_to_section uuid, p_reason text,
    p_allow_other_semester boolean
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_role text; v_departments uuid[]; v_registration public.student_semester_registrations;
    v_kind text; v_source jsonb; v_target jsonb; v_request public.student_transfer_requests;
    v_same_semester boolean;
BEGIN
    PERFORM public.assert_transfer_backend();
    v_role := public.transfer_direct_role(p_actor, p_tenant);
    IF v_role IS NULL THEN
        RAISE EXCEPTION 'Administrator or Head of Department required' USING ERRCODE = '42501';
    END IF;
    IF v_role = 'hod' THEN
        v_departments := public.transfer_hod_departments(p_actor, p_tenant);
    END IF;
    IF length(btrim(COALESCE(p_reason, ''))) NOT BETWEEN 10 AND 2000 THEN
        RAISE EXCEPTION 'Explain the transfer in 10 to 2000 characters' USING ERRCODE = 'P1108';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:' || p_tenant::text, 0));
    PERFORM 1 FROM public.students
    WHERE student_id = p_student AND institution_id = p_tenant
      AND is_active AND status = 'active' AND approval_status = 'approved'
    FOR SHARE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Student not found' USING ERRCODE = 'P0002';
    END IF;
    -- A student's own open request is decided first, never silently replaced.
    IF EXISTS (SELECT 1 FROM public.student_transfer_requests
               WHERE student_id = p_student AND status IN ('submitted', 'under_review')) THEN
        RAISE EXCEPTION 'The student has an open transfer request' USING ERRCODE = 'P1111';
    END IF;
    SELECT * INTO v_registration FROM public.student_semester_registrations
    WHERE semester_registration_id = public.transfer_current_registration(p_student, p_tenant)
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'The student has no current section' USING ERRCODE = 'P1112';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.semesters WHERE semester_id = v_registration.semester_id
                   AND is_active AND end_date >= current_date) THEN
        RAISE EXCEPTION 'The current term is closed' USING ERRCODE = 'P1103';
    END IF;
    v_kind := public.transfer_target_type(v_registration.academic_section_id, p_to_section, p_tenant);
    IF v_kind IS NULL THEN
        RAISE EXCEPTION 'The requested section is unavailable' USING ERRCODE = 'P1104';
    END IF;
    v_same_semester := public.transfer_stage_matches(v_registration.academic_section_id, p_to_section);
    IF NOT v_same_semester AND NOT (v_role = 'admin' AND COALESCE(p_allow_other_semester, false)) THEN
        RAISE EXCEPTION 'Transfers must keep the same semester number' USING ERRCODE = 'P1113';
    END IF;
    v_source := public.transfer_section_json(v_registration.academic_section_id, p_tenant);
    v_target := public.transfer_section_json(p_to_section, p_tenant);
    IF v_departments IS NOT NULL AND (
        NOT (v_source->>'department_id')::uuid = ANY (v_departments)
        OR NOT (v_target->>'department_id')::uuid = ANY (v_departments)) THEN
        RAISE EXCEPTION 'A Head of Department can transfer only within their department'
            USING ERRCODE = '42501';
    END IF;
    INSERT INTO public.student_transfer_requests (
        institution_id, student_id, transfer_type, semester_registration_id, semester_id,
        from_section_id, to_section_id, from_program_id, to_program_id, to_department_id,
        reason, submitted_by, initiated_by, semester_override)
    VALUES (p_tenant, p_student, v_kind, v_registration.semester_registration_id,
        v_registration.semester_id, v_registration.academic_section_id, p_to_section,
        (v_source->>'program_id')::uuid, (v_target->>'program_id')::uuid,
        (v_target->>'department_id')::uuid, btrim(p_reason), p_actor, v_role, NOT v_same_semester)
    RETURNING * INTO v_request;
    -- Re-validates the seat and placement, records the previous registration
    -- and subjects, and marks the row approved by this actor.
    PERFORM public.transfer_apply(p_actor, p_tenant, v_request.transfer_request_id, v_role, NULL);
    INSERT INTO public.student_transfer_events
        (institution_id, transfer_request_id, actor_user_id, action, comment)
    VALUES (p_tenant, v_request.transfer_request_id, p_actor, 'transferred', btrim(p_reason));
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.transfer.direct', 'student_transfer_requests',
        v_request.transfer_request_id::text, jsonb_build_object(
            'transferred_as', v_role, 'student_id', p_student,
            'from_section_id', v_registration.academic_section_id, 'to_section_id', p_to_section,
            'reason', btrim(p_reason), 'semester_override', NOT v_same_semester));
    RETURN jsonb_build_object('transfer_request_id', v_request.transfer_request_id,
        'institution_id', p_tenant, 'student_id', p_student, 'status', 'approved');
END;
$$;
