-- Teaching assignment commands (User Management U8). See 20261201000000 for the
-- rules. Every command re-derives the actor's authority and is audited; the
-- audit row carries faculty_user_id so it appears in the member's history.
BEGIN;

-- Assign a Faculty member to an offering. Active at once unless the subject's
-- department is outside the teacher's departments and the actor does not head it.
CREATE FUNCTION public.request_teaching_assignment(
    p_actor uuid, p_tenant uuid, p_offering uuid, p_faculty uuid,
    p_starts_on date DEFAULT NULL, p_planned_end_on date DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_admin boolean; v_heads uuid[]; v_home uuid[]; v_department uuid; v_needs boolean;
    v_today date := public.department_head_today();
    v_starts date := COALESCE(p_starts_on, public.department_head_today());
    v_row public.teaching_assignments;
BEGIN
    SELECT * INTO v_admin, v_heads FROM public.teaching_actor(p_actor, p_tenant);
    SELECT c.department_id INTO v_department
    FROM public.academic_offerings o
    JOIN public.academic_sections s ON s.academic_section_id = o.academic_section_id AND s.is_active
    JOIN public.curriculum_subjects cs ON cs.curriculum_subject_id = o.curriculum_subject_id AND cs.is_active
    JOIN public.courses c ON c.course_id = cs.course_id
    JOIN public.departments d ON d.department_id = c.department_id AND d.institution_id = p_tenant AND d.is_active
    WHERE o.academic_offering_id = p_offering AND o.institution_id = p_tenant AND o.is_active
    FOR UPDATE OF o;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Choose an active subject offering of this institution' USING ERRCODE = 'P1501';
    END IF;
    IF p_faculty IS NULL OR NOT public.transfer_is_active_faculty(p_faculty, p_tenant) THEN
        RAISE EXCEPTION 'Choose an active faculty member' USING ERRCODE = 'P1502';
    END IF;
    IF p_planned_end_on IS NOT NULL AND (p_planned_end_on < v_today OR p_planned_end_on < v_starts) THEN
        RAISE EXCEPTION 'The planned end must be on or after today and the start date' USING ERRCODE = 'P1505';
    END IF;
    v_home := public.teaching_home_departments(p_faculty, p_tenant);
    IF NOT (v_admin OR v_department = ANY (v_heads) OR v_home && v_heads) THEN
        RAISE EXCEPTION 'You can assign teaching only for departments you head' USING ERRCODE = 'P1503';
    END IF;
    v_needs := NOT (v_department = ANY (v_home)) AND NOT (v_department = ANY (v_heads));
    -- Record the end of an assignment whose planned end date has passed.
    UPDATE public.teaching_assignments SET status = 'ended', ended_at = now(), ended_by = p_actor
    WHERE academic_offering_id = p_offering AND faculty_user_id = p_faculty AND status = 'active'
      AND NOT public.department_head_in_effect(NULL, planned_end_on);
    SELECT * INTO v_row FROM public.teaching_assignments
    WHERE academic_offering_id = p_offering AND faculty_user_id = p_faculty AND status IN ('pending', 'active');
    IF FOUND THEN
        RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', true);
    END IF;
    INSERT INTO public.teaching_assignments (institution_id, academic_offering_id, faculty_user_id,
        department_id, status, needs_approval, starts_on, planned_end_on, requested_by)
    VALUES (p_tenant, p_offering, p_faculty, v_department,
        CASE WHEN v_needs THEN 'pending' ELSE 'active' END, v_needs, v_starts, p_planned_end_on, p_actor)
    RETURNING * INTO v_row;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'teaching.assignment.request', 'teaching_assignments',
        v_row.assignment_id::text, jsonb_build_object('faculty_user_id', p_faculty,
            'academic_offering_id', p_offering, 'department_id', v_department, 'status', v_row.status,
            'starts_on', v_starts, 'planned_end_on', p_planned_end_on));
    RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', false);
END;
$$;

-- Approve or reject a pending cross-department assignment.
CREATE FUNCTION public.decide_teaching_assignment(
    p_actor uuid, p_tenant uuid, p_assignment uuid, p_approve boolean, p_note text DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_admin boolean; v_heads uuid[]; v_row public.teaching_assignments;
    v_note text := NULLIF(btrim(COALESCE(p_note, '')), '');
BEGIN
    SELECT * INTO v_admin, v_heads FROM public.teaching_actor(p_actor, p_tenant);
    SELECT * INTO v_row FROM public.teaching_assignments
    WHERE assignment_id = p_assignment AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Teaching assignment not found' USING ERRCODE = 'P0002';
    END IF;
    IF v_row.status <> 'pending' THEN
        IF (p_approve AND v_row.status = 'active' AND v_row.decided_by IS NOT NULL)
           OR (NOT p_approve AND v_row.status = 'rejected') THEN
            RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', true);
        END IF;
        RAISE EXCEPTION 'This request was already decided or withdrawn' USING ERRCODE = 'P1504';
    END IF;
    IF NOT public.teaching_can_decide(p_actor, p_tenant, v_admin, v_heads, v_row) THEN
        RAISE EXCEPTION 'Only the receiving Head of Department decides this request' USING ERRCODE = 'P1503';
    END IF;
    IF NOT p_approve AND (v_note IS NULL OR char_length(v_note) > 500) THEN
        RAISE EXCEPTION 'Give a reason of up to 500 characters' USING ERRCODE = 'P1506';
    END IF;
    IF p_approve AND NOT public.transfer_is_active_faculty(v_row.faculty_user_id, p_tenant) THEN
        RAISE EXCEPTION 'The faculty member is no longer active' USING ERRCODE = 'P1502';
    END IF;
    IF p_approve AND NOT public.department_head_in_effect(NULL, v_row.planned_end_on) THEN
        RAISE EXCEPTION 'The planned end date has passed' USING ERRCODE = 'P1505';
    END IF;
    UPDATE public.teaching_assignments
    SET status = CASE WHEN p_approve THEN 'active' ELSE 'rejected' END,
        decided_by = p_actor, decided_at = now(), decision_note = v_note
    WHERE assignment_id = p_assignment RETURNING * INTO v_row;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant,
        CASE WHEN p_approve THEN 'teaching.assignment.approve' ELSE 'teaching.assignment.reject' END,
        'teaching_assignments', p_assignment::text, jsonb_build_object('faculty_user_id', v_row.faculty_user_id,
            'academic_offering_id', v_row.academic_offering_id, 'department_id', v_row.department_id,
            'status', v_row.status, 'note', v_note));
    RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', false);
END;
$$;

-- End an active assignment or withdraw a pending one. The row is kept.
CREATE FUNCTION public.end_teaching_assignment(p_actor uuid, p_tenant uuid, p_assignment uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_admin boolean; v_heads uuid[]; v_row public.teaching_assignments;
BEGIN
    SELECT * INTO v_admin, v_heads FROM public.teaching_actor(p_actor, p_tenant);
    SELECT * INTO v_row FROM public.teaching_assignments
    WHERE assignment_id = p_assignment AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Teaching assignment not found' USING ERRCODE = 'P0002';
    END IF;
    IF v_row.status NOT IN ('pending', 'active') THEN
        RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', true);
    END IF;
    IF NOT (v_admin OR v_row.department_id = ANY (v_heads)
            OR (v_row.status = 'pending' AND v_row.requested_by = p_actor)) THEN
        RAISE EXCEPTION 'Only an administrator or the receiving Head of Department ends this'
            USING ERRCODE = 'P1503';
    END IF;
    UPDATE public.teaching_assignments
    SET status = CASE WHEN status = 'pending' THEN 'cancelled' ELSE 'ended' END,
        ended_by = p_actor, ended_at = now()
    WHERE assignment_id = p_assignment RETURNING * INTO v_row;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant,
        CASE WHEN v_row.status = 'cancelled' THEN 'teaching.assignment.cancel' ELSE 'teaching.assignment.end' END,
        'teaching_assignments', p_assignment::text, jsonb_build_object('faculty_user_id', v_row.faculty_user_id,
            'academic_offering_id', v_row.academic_offering_id, 'department_id', v_row.department_id,
            'status', v_row.status));
    RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', false);
END;
$$;

REVOKE ALL ON FUNCTION public.request_teaching_assignment(uuid, uuid, uuid, uuid, date, date),
    public.decide_teaching_assignment(uuid, uuid, uuid, boolean, text),
    public.end_teaching_assignment(uuid, uuid, uuid)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.request_teaching_assignment(uuid, uuid, uuid, uuid, date, date),
    public.decide_teaching_assignment(uuid, uuid, uuid, boolean, text),
    public.end_teaching_assignment(uuid, uuid, uuid)
    TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
