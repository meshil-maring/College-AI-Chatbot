-- Teaching assignments (User Management U8): which Faculty member teaches which
-- subject offering (one curriculum subject for one class section and term).
--
-- Department membership and teaching are separate. The receiving department is
-- the department that owns the subject's catalogue course. An assignment is
-- cross-department when that department is neither the teacher's primary nor an
-- additional department; it then waits for a current Head of Department of the
-- receiving department to approve it. When that department has no other current
-- head, an administrator may approve instead.
--
-- Administrators manage every assignment. A current HOD assigns within the
-- departments they head and may request teaching for their own department's
-- Faculty elsewhere. Rows are never deleted: rejected, cancelled and ended
-- assignments stay as history, and an offering with history cannot be deleted.
-- These records grant no access yet; attendance and marks were removed on
-- 2026-10-23. Codes: P1501 offering, P1502 faculty, P1503 not your department,
-- P1504 already decided, P1505 dates, P1506 rejection reason.
BEGIN;

CREATE TABLE public.teaching_assignments (
    assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    academic_offering_id uuid NOT NULL
        REFERENCES public.academic_offerings(academic_offering_id) ON DELETE RESTRICT,
    faculty_user_id uuid NOT NULL REFERENCES public.users(id),
    department_id uuid NOT NULL REFERENCES public.departments(department_id),
    status text NOT NULL CHECK (status IN ('pending', 'active', 'rejected', 'cancelled', 'ended')),
    needs_approval boolean NOT NULL,
    starts_on date NOT NULL,
    planned_end_on date,
    requested_by uuid NOT NULL REFERENCES public.users(id),
    requested_at timestamptz NOT NULL DEFAULT now(),
    decided_by uuid REFERENCES public.users(id),
    decided_at timestamptz,
    decision_note text CHECK (decision_note IS NULL OR char_length(decision_note) BETWEEN 1 AND 500),
    ended_by uuid REFERENCES public.users(id),
    ended_at timestamptz,
    CONSTRAINT teaching_assignments_term_order CHECK (planned_end_on IS NULL OR planned_end_on >= starts_on),
    CONSTRAINT teaching_assignments_decision_pair CHECK ((decided_at IS NULL) = (decided_by IS NULL)),
    CONSTRAINT teaching_assignments_end_pair CHECK ((ended_at IS NULL) = (ended_by IS NULL)),
    CONSTRAINT teaching_assignments_closed CHECK ((status IN ('cancelled', 'ended')) = (ended_at IS NOT NULL)),
    CONSTRAINT teaching_assignments_rejected CHECK (status <> 'rejected' OR decided_at IS NOT NULL)
);

-- One open (pending or active) assignment per teacher and offering; co-teaching
-- by different Faculty members is allowed.
CREATE UNIQUE INDEX teaching_assignments_one_open
    ON public.teaching_assignments (academic_offering_id, faculty_user_id)
    WHERE status IN ('pending', 'active');
CREATE INDEX teaching_assignments_department
    ON public.teaching_assignments (institution_id, department_id) WHERE status IN ('pending', 'active');
CREATE INDEX teaching_assignments_faculty ON public.teaching_assignments (institution_id, faculty_user_id);

ALTER TABLE public.teaching_assignments ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.teaching_assignments FROM PUBLIC, anon, authenticated, service_role;

-- The member's primary and additional departments.
CREATE FUNCTION public.teaching_home_departments(p_user uuid, p_tenant uuid)
RETURNS uuid[] LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(array_agg(DISTINCT d.department_id), '{}'::uuid[]) FROM (
        SELECT department_id FROM public.institution_member_departments
        WHERE institution_id = p_tenant AND user_id = p_user
        UNION
        SELECT department_id FROM public.institution_member_additional_departments
        WHERE institution_id = p_tenant AND user_id = p_user
    ) d;
$$;

-- Who is acting: an active administrator, a current HOD, or neither (refused).
CREATE FUNCTION public.teaching_actor(p_actor uuid, p_tenant uuid, OUT is_admin boolean, OUT heads uuid[])
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;
    is_admin := EXISTS (
        SELECT 1 FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.institutions i ON i.institution_id = p_tenant
        WHERE u.id = p_actor AND u.status = 'active' AND r.name = 'admin' AND r.is_active
          AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
          AND i.status = 'active' AND i.is_active);
    heads := public.transfer_hod_departments(p_actor, p_tenant);
    IF NOT is_admin AND cardinality(heads) = 0 THEN
        RAISE EXCEPTION 'Only administrators and Heads of Department manage teaching' USING ERRCODE = '42501';
    END IF;
END;
$$;

-- May this actor approve or reject a pending assignment? A head never approves
-- their own teaching; an administrator approves only when no other head exists.
CREATE FUNCTION public.teaching_can_decide(
    p_actor uuid, p_tenant uuid, p_is_admin boolean, p_heads uuid[], p_row public.teaching_assignments
) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT p_row.status = 'pending' AND (
        (p_row.department_id = ANY (p_heads) AND p_actor <> p_row.faculty_user_id)
        OR (p_is_admin AND cardinality(array_remove(
            public.department_head_ids(p_tenant, p_row.department_id), p_row.faculty_user_id)) = 0));
$$;

-- Assignments the actor may see, newest first, with labels and allowed actions.
CREATE FUNCTION public.read_teaching_assignments(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_admin boolean; v_heads uuid[];
BEGIN
    SELECT * INTO v_admin, v_heads FROM public.teaching_actor(p_actor, p_tenant);
    RETURN jsonb_build_object('institution_id', p_tenant, 'is_admin', v_admin,
        'head_department_ids', to_jsonb(v_heads), 'assignments', COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'assignment_id', t.assignment_id, 'status', t.status, 'needs_approval', t.needs_approval,
            'is_current', t.status = 'active' AND public.department_head_in_effect(NULL, t.planned_end_on),
            'academic_offering_id', t.academic_offering_id, 'subject_code', cs.subject_code,
            'subject_name', cs.subject_name, 'section_code', s.code, 'section_name', s.name,
            'semester_name', sem.name, 'department_id', t.department_id, 'department_name', d.name,
            'faculty_user_id', t.faculty_user_id, 'faculty_name', public.teaching_person(t.faculty_user_id),
            'starts_on', t.starts_on, 'planned_end_on', t.planned_end_on,
            'requested_by_name', public.teaching_person(t.requested_by), 'requested_at', t.requested_at,
            'decided_by_name', public.teaching_person(t.decided_by), 'decided_at', t.decided_at,
            'decision_note', t.decision_note, 'ended_at', t.ended_at,
            'can_decide', public.teaching_can_decide(p_actor, p_tenant, v_admin, v_heads, t),
            'can_end', t.status IN ('pending', 'active') AND (v_admin OR t.department_id = ANY (v_heads)
                OR (t.status = 'pending' AND t.requested_by = p_actor))
        ) ORDER BY (t.status = 'pending') DESC, t.requested_at DESC)
        FROM public.teaching_assignments t
        JOIN public.academic_offerings o ON o.academic_offering_id = t.academic_offering_id
        JOIN public.academic_sections s ON s.academic_section_id = o.academic_section_id
        JOIN public.curriculum_subjects cs ON cs.curriculum_subject_id = o.curriculum_subject_id
        LEFT JOIN public.semesters sem ON sem.semester_id = s.semester_id
        JOIN public.departments d ON d.department_id = t.department_id
        WHERE t.institution_id = p_tenant AND (v_admin OR t.department_id = ANY (v_heads)
            OR t.requested_by = p_actor
            OR public.teaching_home_departments(t.faculty_user_id, p_tenant) && v_heads)
    ), '[]'::jsonb));
END;
$$;

-- A person's display name, or their email when no name is set.
CREATE FUNCTION public.teaching_person(p_user uuid)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(NULLIF(btrim(concat_ws(' ', first_name, last_name)), ''), email)
    FROM public.users WHERE id = p_user;
$$;

-- Active offerings and active Faculty to choose from when assigning.
CREATE FUNCTION public.read_teaching_options(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    -- Refuses anyone who is neither an administrator nor a current HOD.
    PERFORM public.teaching_actor(p_actor, p_tenant);
    RETURN jsonb_build_object('institution_id', p_tenant,
        'offerings', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'academic_offering_id', o.academic_offering_id, 'subject_code', cs.subject_code,
                'subject_name', cs.subject_name, 'section_code', s.code, 'section_name', s.name,
                'semester_name', sem.name, 'department_id', d.department_id, 'department_name', d.name
            ) ORDER BY d.name, cs.subject_code, s.code)
            FROM public.academic_offerings o
            JOIN public.academic_sections s ON s.academic_section_id = o.academic_section_id AND s.is_active
            JOIN public.curriculum_subjects cs ON cs.curriculum_subject_id = o.curriculum_subject_id AND cs.is_active
            JOIN public.courses c ON c.course_id = cs.course_id
            JOIN public.departments d ON d.department_id = c.department_id AND d.institution_id = p_tenant AND d.is_active
            LEFT JOIN public.semesters sem ON sem.semester_id = s.semester_id
            WHERE o.institution_id = p_tenant AND o.is_active), '[]'::jsonb),
        'faculty', COALESCE((
            SELECT jsonb_agg(jsonb_build_object('user_id', u.id, 'name', public.teaching_person(u.id),
                'department_ids', to_jsonb(public.teaching_home_departments(u.id, p_tenant)))
                ORDER BY public.teaching_person(u.id))
            FROM public.users u
            WHERE public.transfer_is_active_faculty(u.id, p_tenant)), '[]'::jsonb));
END;
$$;

REVOKE ALL ON FUNCTION public.teaching_home_departments(uuid, uuid), public.teaching_actor(uuid, uuid),
    public.teaching_can_decide(uuid, uuid, boolean, uuid[], public.teaching_assignments),
    public.teaching_person(uuid), public.read_teaching_assignments(uuid, uuid),
    public.read_teaching_options(uuid, uuid)
    FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.read_teaching_assignments(uuid, uuid), public.read_teaching_options(uuid, uuid)
    TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
