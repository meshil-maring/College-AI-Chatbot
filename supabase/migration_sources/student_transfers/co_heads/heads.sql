-- Several current Heads of Department per department, and one faculty member
-- may head several departments (any active department in their institution).
-- All current heads of a department are equal: each may review its transfers,
-- and the first decision counts. Ended appointments stay as history.
DROP INDEX public.department_heads_one_current;
CREATE UNIQUE INDEX department_heads_one_per_member
    ON public.department_heads (department_id, faculty_user_id) WHERE ended_at IS NULL;

COMMENT ON TABLE public.department_heads IS
    'Head of Department appointments. A department may have several current heads and a faculty '
    'member may head several departments; one current row per (department, faculty). Ended rows are history.';

-- Current heads, ordered by department and appointment time.
CREATE OR REPLACE FUNCTION public.read_department_heads(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.assert_transfer_backend();
    IF NOT public.transfer_admin_allowed(p_actor, p_tenant, 'departments.read') THEN
        RAISE EXCEPTION 'Administrator permission required' USING ERRCODE = '42501';
    END IF;
    RETURN jsonb_build_object(
        'institution_id', p_tenant,
        'heads', (
            SELECT COALESCE(jsonb_agg(jsonb_build_object(
                'department_id', h.department_id, 'faculty_user_id', h.faculty_user_id,
                'name', COALESCE(NULLIF(btrim(u.display_name), ''),
                    NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email),
                'email', u.email, 'assigned_at', h.assigned_at,
                'is_active_faculty', public.transfer_is_active_faculty(h.faculty_user_id, p_tenant)
            ) ORDER BY h.department_id, h.assigned_at, h.faculty_user_id), '[]'::jsonb)
            FROM public.department_heads h
            JOIN public.users u ON u.id = h.faculty_user_id
            WHERE h.institution_id = p_tenant AND h.ended_at IS NULL
        ),
        'faculty', (
            SELECT COALESCE(jsonb_agg(member ORDER BY member->>'name', member->>'user_id'), '[]'::jsonb)
            FROM (
                SELECT DISTINCT jsonb_build_object(
                    'user_id', u.id,
                    'name', COALESCE(NULLIF(btrim(u.display_name), ''),
                        NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email),
                    'email', u.email
                ) AS member
                FROM public.users u
                JOIN public.user_roles ur ON ur.user_id = u.id
                JOIN public.roles r ON r.id = ur.role_id
                WHERE r.name = 'faculty' AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
                  AND public.transfer_is_active_faculty(u.id, p_tenant)
            ) faculty_members
        )
    );
END;
$$;

-- Locks and returns the department after checking the administrator's grant.
-- Every appointment change for one department runs one at a time.
CREATE FUNCTION public.department_head_lock(p_actor uuid, p_tenant uuid, p_department uuid)
RETURNS public.departments LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_department public.departments;
BEGIN
    PERFORM public.assert_transfer_backend();
    IF NOT public.transfer_admin_allowed(p_actor, p_tenant, 'departments.manage') THEN
        RAISE EXCEPTION 'Administrator permission required' USING ERRCODE = '42501';
    END IF;
    SELECT * INTO v_department FROM public.departments
    WHERE department_id = p_department AND institution_id = p_tenant
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Department not found' USING ERRCODE = 'P0002';
    END IF;
    RETURN v_department;
END;
$$;

CREATE FUNCTION public.department_head_ids(p_tenant uuid, p_department uuid)
RETURNS uuid[] LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(array_agg(h.faculty_user_id ORDER BY h.assigned_at, h.faculty_user_id), '{}'::uuid[])
    FROM public.department_heads h
    WHERE h.institution_id = p_tenant AND h.department_id = p_department AND h.ended_at IS NULL;
$$;

-- Add one Head of Department without ending the others. Idempotent.
CREATE FUNCTION public.add_department_head(
    p_actor uuid, p_tenant uuid, p_department uuid, p_faculty uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_department public.departments; v_before uuid[];
BEGIN
    v_department := public.department_head_lock(p_actor, p_tenant, p_department);
    IF p_faculty IS NULL OR NOT v_department.is_active
       OR NOT public.transfer_is_active_faculty(p_faculty, p_tenant) THEN
        RAISE EXCEPTION 'Choose an active faculty member for an active department'
            USING ERRCODE = 'P1110';
    END IF;
    v_before := public.department_head_ids(p_tenant, p_department);
    IF p_faculty = ANY (v_before) THEN
        RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
            'institution_id', p_tenant, 'already_applied', true, 'head_ids', to_jsonb(v_before));
    END IF;
    INSERT INTO public.department_heads (institution_id, department_id, faculty_user_id, assigned_by)
    VALUES (p_tenant, p_department, p_faculty, p_actor);
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.department.head.add', 'department_heads', p_department::text,
        jsonb_build_object('faculty_user_id', p_faculty, 'before', to_jsonb(v_before),
            'after', to_jsonb(public.department_head_ids(p_tenant, p_department))));
    RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
        'institution_id', p_tenant, 'already_applied', false,
        'head_ids', to_jsonb(public.department_head_ids(p_tenant, p_department)));
END;
$$;

-- End one Head of Department's appointment; other heads stay. Idempotent.
-- Works for an inactive department too, so stale appointments can be cleared.
CREATE FUNCTION public.end_department_head(
    p_actor uuid, p_tenant uuid, p_department uuid, p_faculty uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_before uuid[];
BEGIN
    PERFORM public.department_head_lock(p_actor, p_tenant, p_department);
    v_before := public.department_head_ids(p_tenant, p_department);
    IF p_faculty IS NULL OR NOT (p_faculty = ANY (v_before)) THEN
        RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
            'institution_id', p_tenant, 'already_applied', true, 'head_ids', to_jsonb(v_before));
    END IF;
    UPDATE public.department_heads SET ended_at = now(), ended_by = p_actor
    WHERE institution_id = p_tenant AND department_id = p_department
      AND faculty_user_id = p_faculty AND ended_at IS NULL;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.department.head.end', 'department_heads', p_department::text,
        jsonb_build_object('faculty_user_id', p_faculty, 'before', to_jsonb(v_before),
            'after', to_jsonb(public.department_head_ids(p_tenant, p_department))));
    RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
        'institution_id', p_tenant, 'already_applied', false,
        'head_ids', to_jsonb(public.department_head_ids(p_tenant, p_department)));
END;
$$;

-- The original single-head command keeps its contract: p_faculty becomes the
-- department's only head, and NULL ends every current appointment.
CREATE OR REPLACE FUNCTION public.assign_department_head(
    p_actor uuid, p_tenant uuid, p_department uuid, p_faculty uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_department public.departments; v_before uuid[];
BEGIN
    PERFORM public.assert_transfer_backend();
    v_department := public.department_head_lock(p_actor, p_tenant, p_department);
    v_before := public.department_head_ids(p_tenant, p_department);
    IF p_faculty IS NOT NULL THEN
        IF NOT v_department.is_active OR NOT public.transfer_is_active_faculty(p_faculty, p_tenant) THEN
            RAISE EXCEPTION 'Choose an active faculty member for an active department'
                USING ERRCODE = 'P1110';
        END IF;
        IF v_before = ARRAY[p_faculty] THEN
            RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
                'institution_id', p_tenant);
        END IF;
    ELSIF cardinality(v_before) = 0 THEN
        RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', NULL,
            'institution_id', p_tenant);
    END IF;
    UPDATE public.department_heads SET ended_at = now(), ended_by = p_actor
    WHERE institution_id = p_tenant AND department_id = p_department AND ended_at IS NULL
      AND faculty_user_id IS DISTINCT FROM p_faculty;
    IF p_faculty IS NOT NULL AND NOT (p_faculty = ANY (v_before)) THEN
        INSERT INTO public.department_heads (institution_id, department_id, faculty_user_id, assigned_by)
        VALUES (p_tenant, p_department, p_faculty, p_actor);
    END IF;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.department.head', 'department_heads', p_department::text,
        jsonb_build_object('before', to_jsonb(v_before), 'after', p_faculty));
    RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
        'institution_id', p_tenant);
END;
$$;
