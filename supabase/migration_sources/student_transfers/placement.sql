-- Display and availability details for one tenant section.
CREATE FUNCTION public.transfer_section_json(p_section uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT jsonb_build_object(
        'academic_section_id', sec.academic_section_id,
        'section_name', sec.name, 'section_code', sec.code,
        'admission_cohort_id', cohort.admission_cohort_id, 'batch_name', cohort.name,
        'program_id', program.program_id, 'program_name', program.name, 'program_code', program.code,
        'department_id', department.department_id, 'department_name', department.name,
        'program_semester_name', stage.name,
        'semester_id', term.semester_id, 'term_name', term.name,
        'capacity', sec.capacity,
        'seats_taken', (
            SELECT count(*) FROM public.student_semester_registrations taken
            WHERE taken.academic_section_id = sec.academic_section_id
        )
    )
    FROM public.academic_sections sec
    JOIN public.admission_cohorts cohort ON cohort.admission_cohort_id = sec.admission_cohort_id
    JOIN public.programs program ON program.program_id = cohort.program_id
    JOIN public.departments department ON department.department_id = program.department_id
    JOIN public.program_semesters stage ON stage.program_semester_id = sec.program_semester_id
    JOIN public.semesters term ON term.semester_id = sec.semester_id
    WHERE sec.academic_section_id = p_section AND sec.institution_id = p_tenant;
$$;

-- Classifies a move between two sections of the same open term, or returns
-- NULL when the move is not allowed. A section transfer stays in the same
-- batch; a program transfer moves to a different program. Moving to another
-- batch of the same program is not a transfer handled by this workflow.
CREATE FUNCTION public.transfer_target_type(p_from uuid, p_to uuid, p_tenant uuid)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT CASE
        WHEN target.admission_cohort_id = source.admission_cohort_id THEN 'section_transfer'
        WHEN target_cohort.program_id <> source_cohort.program_id THEN 'program_transfer'
    END
    FROM public.academic_sections source
    JOIN public.admission_cohorts source_cohort
        ON source_cohort.admission_cohort_id = source.admission_cohort_id
    JOIN public.academic_sections target
        ON target.academic_section_id = p_to AND target.institution_id = p_tenant
    JOIN public.admission_cohorts target_cohort
        ON target_cohort.admission_cohort_id = target.admission_cohort_id
    JOIN public.programs program ON program.program_id = target_cohort.program_id
    JOIN public.departments department ON department.department_id = program.department_id
    JOIN public.program_semesters stage ON stage.program_semester_id = target.program_semester_id
    JOIN public.semesters term ON term.semester_id = target.semester_id
    WHERE source.academic_section_id = p_from AND source.institution_id = p_tenant
      AND target.academic_section_id <> source.academic_section_id
      AND target.semester_id = source.semester_id
      AND target.is_active AND target_cohort.is_active AND program.is_active
      AND department.is_active AND stage.is_active AND term.is_active
      AND term.end_date >= current_date;
$$;

-- True while the section has no capacity limit or still has a free seat.
CREATE FUNCTION public.transfer_section_has_seat(p_section uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT sec.capacity IS NULL OR (
        SELECT count(*) FROM public.student_semester_registrations taken
        WHERE taken.academic_section_id = sec.academic_section_id
    ) < sec.capacity
    FROM public.academic_sections sec
    WHERE sec.academic_section_id = p_section;
$$;

-- Requests visible to one student (p_student) or to reviewers limited to the
-- given departments (NULL means every department, used for administrators).
CREATE FUNCTION public.transfer_requests_json(
    p_tenant uuid, p_student uuid, p_departments uuid[], p_open_only boolean
) RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'transfer_request_id', t.transfer_request_id, 'student_id', t.student_id,
        'student_name', COALESCE(NULLIF(btrim(u.display_name), ''),
            NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email),
        'register_number', COALESCE(s.register_number, s.student_number),
        'transfer_type', t.transfer_type, 'status', t.status, 'reason', t.reason,
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
