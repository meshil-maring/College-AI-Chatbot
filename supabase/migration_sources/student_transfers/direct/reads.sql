-- Request history now states who started each transfer.
CREATE OR REPLACE FUNCTION public.transfer_requests_json(
    p_tenant uuid, p_student uuid, p_departments uuid[], p_open_only boolean
) RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'transfer_request_id', t.transfer_request_id, 'student_id', t.student_id,
        'student_name', COALESCE(NULLIF(btrim(u.display_name), ''),
            NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email),
        'register_number', COALESCE(s.register_number, s.student_number),
        'transfer_type', t.transfer_type, 'status', t.status, 'reason', t.reason,
        'initiated_by', t.initiated_by,
        'from_section', public.transfer_section_json(t.from_section_id, p_tenant),
        'to_section', public.transfer_section_json(t.to_section_id, p_tenant),
        'submitted_at', t.submitted_at, 'review_started_at', t.review_started_at,
        'decided_at', t.decided_at, 'decided_as', t.decided_as,
        'decision_comment', t.decision_comment, 'cancelled_at', t.cancelled_at,
        'previous_enrollments', t.previous_enrollments,
        'events', (
            SELECT COALESCE(jsonb_agg(jsonb_build_object(
                'action', e.action, 'comment', e.comment, 'created_at', e.created_at
            ) ORDER BY e.created_at, e.transfer_event_id), '[]'::jsonb)
            FROM public.student_transfer_events e
            WHERE e.transfer_request_id = t.transfer_request_id
        )
    ) ORDER BY t.submitted_at DESC, t.transfer_request_id), '[]'::jsonb)
    FROM public.student_transfer_requests t
    JOIN public.students s ON s.student_id = t.student_id
    LEFT JOIN public.users u ON u.id = s.user_id
    WHERE t.institution_id = p_tenant
      AND (p_student IS NULL OR t.student_id = p_student)
      AND (p_departments IS NULL OR t.to_department_id = ANY (p_departments))
      AND (NOT p_open_only OR t.status IN ('submitted', 'under_review'));
$$;

-- 'admin' with transfers.approve, 'hod' for a current Head of Department, else NULL.
CREATE FUNCTION public.transfer_direct_role(p_actor uuid, p_tenant uuid)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT CASE
        WHEN public.transfer_admin_allowed(p_actor, p_tenant, 'transfers.approve') THEN 'admin'
        WHEN cardinality(public.transfer_hod_departments(p_actor, p_tenant)) > 0 THEN 'hod'
    END;
$$;

-- Approved active students with a section in an open term. An HOD only sees
-- students whose current program belongs to a department they head.
CREATE FUNCTION public.read_direct_transfer_students(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_role text; v_departments uuid[];
BEGIN
    PERFORM public.assert_transfer_backend();
    v_role := public.transfer_direct_role(p_actor, p_tenant);
    IF v_role IS NULL THEN
        RETURN jsonb_build_object('institution_id', p_tenant, 'can_transfer', false,
            'actor_role', NULL, 'students', '[]'::jsonb);
    END IF;
    IF v_role = 'hod' THEN
        v_departments := public.transfer_hod_departments(p_actor, p_tenant);
    END IF;
    RETURN jsonb_build_object(
        'institution_id', p_tenant, 'can_transfer', true, 'actor_role', v_role,
        'students', (
            SELECT COALESCE(jsonb_agg(jsonb_build_object(
                'student_id', candidate.student_id, 'student_name', candidate.student_name,
                'register_number', candidate.register_number,
                'current_section', public.transfer_section_json(reg.academic_section_id, p_tenant),
                'registration_status', reg.status,
                'has_open_request', EXISTS (
                    SELECT 1 FROM public.student_transfer_requests open_request
                    WHERE open_request.student_id = candidate.student_id
                      AND open_request.status IN ('submitted', 'under_review'))
            ) ORDER BY candidate.student_name, candidate.student_id), '[]'::jsonb)
            FROM (
                SELECT s.student_id,
                    COALESCE(NULLIF(btrim(u.display_name), ''),
                        NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email) AS student_name,
                    COALESCE(s.register_number, s.student_number) AS register_number,
                    public.transfer_current_registration(s.student_id, p_tenant) AS registration_id
                FROM public.students s
                LEFT JOIN public.users u ON u.id = s.user_id
                WHERE s.institution_id = p_tenant AND s.is_active AND s.status = 'active'
                  AND s.approval_status = 'approved'
            ) candidate
            JOIN public.student_semester_registrations reg
                ON reg.semester_registration_id = candidate.registration_id
            JOIN public.academic_sections sec ON sec.academic_section_id = reg.academic_section_id
            JOIN public.admission_cohorts cohort ON cohort.admission_cohort_id = sec.admission_cohort_id
            JOIN public.programs program ON program.program_id = cohort.program_id
            JOIN public.semesters term ON term.semester_id = reg.semester_id
            WHERE term.is_active AND term.end_date >= current_date
              AND (v_departments IS NULL OR program.department_id = ANY (v_departments))
        )
    );
END;
$$;

-- One student's current section and the sections the actor may move them to.
CREATE FUNCTION public.read_direct_transfer_options(p_actor uuid, p_tenant uuid, p_student uuid)
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
                        'has_seat', public.transfer_section_has_seat(target.academic_section_id)
                    ) AS option_row
                FROM public.academic_sections target
                WHERE target.institution_id = p_tenant
                  AND target.semester_id = v_registration.semester_id
                  AND public.transfer_target_type(
                      v_registration.academic_section_id, target.academic_section_id, p_tenant) IS NOT NULL
            ) option_rows
            WHERE v_departments IS NULL OR (option_row->>'department_id')::uuid = ANY (v_departments)
        )
    );
END;
$$;
