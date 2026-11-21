-- Current Heads of Department plus the faculty members who may be appointed.
CREATE FUNCTION public.read_department_heads(p_actor uuid, p_tenant uuid)
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
            ) ORDER BY h.department_id), '[]'::jsonb)
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

-- Appoint (p_faculty) or remove (NULL) the department's Head of Department.
-- The previous appointment is ended, never deleted.
CREATE FUNCTION public.assign_department_head(
    p_actor uuid, p_tenant uuid, p_department uuid, p_faculty uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_department public.departments; v_current public.department_heads;
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
    SELECT * INTO v_current FROM public.department_heads
    WHERE department_id = p_department AND institution_id = p_tenant AND ended_at IS NULL
    FOR UPDATE;
    IF p_faculty IS NOT NULL THEN
        IF NOT v_department.is_active OR NOT public.transfer_is_active_faculty(p_faculty, p_tenant) THEN
            RAISE EXCEPTION 'Choose an active faculty member for an active department'
                USING ERRCODE = 'P1110';
        END IF;
        IF v_current.faculty_user_id = p_faculty THEN
            RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
                'institution_id', p_tenant);
        END IF;
    ELSIF v_current.department_head_id IS NULL THEN
        RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', NULL,
            'institution_id', p_tenant);
    END IF;
    IF v_current.department_head_id IS NOT NULL THEN
        UPDATE public.department_heads SET ended_at = now(), ended_by = p_actor
        WHERE department_head_id = v_current.department_head_id;
    END IF;
    IF p_faculty IS NOT NULL THEN
        INSERT INTO public.department_heads (institution_id, department_id, faculty_user_id, assigned_by)
        VALUES (p_tenant, p_department, p_faculty, p_actor);
    END IF;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.department.head', 'department_heads', p_department::text,
        jsonb_build_object('before', v_current.faculty_user_id, 'after', p_faculty));
    RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
        'institution_id', p_tenant);
END;
$$;
