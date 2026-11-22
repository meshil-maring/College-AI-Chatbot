-- Current heads respect planned end dates everywhere HOD authority is decided.

CREATE OR REPLACE FUNCTION public.transfer_hod_departments(p_actor uuid, p_tenant uuid)
RETURNS uuid[] LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(array_agg(h.department_id ORDER BY h.department_id), '{}'::uuid[])
    FROM public.department_heads h
    JOIN public.departments d
        ON d.department_id = h.department_id AND d.institution_id = p_tenant AND d.is_active
    WHERE h.institution_id = p_tenant AND h.faculty_user_id = p_actor
      AND public.department_head_in_effect(h.ended_at, h.planned_end_on)
      AND public.transfer_is_active_faculty(p_actor, p_tenant);
$$;

CREATE OR REPLACE FUNCTION public.department_head_ids(p_tenant uuid, p_department uuid)
RETURNS uuid[] LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(array_agg(h.faculty_user_id ORDER BY h.assigned_at, h.faculty_user_id), '{}'::uuid[])
    FROM public.department_heads h
    WHERE h.institution_id = p_tenant AND h.department_id = p_department
      AND public.department_head_in_effect(h.ended_at, h.planned_end_on);
$$;

-- Current heads with their terms, the faculty who may be appointed, and the
-- institution's multi-department policy.
CREATE OR REPLACE FUNCTION public.read_department_heads(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.assert_transfer_backend();
    IF NOT public.transfer_admin_allowed(p_actor, p_tenant, 'departments.read') THEN
        RAISE EXCEPTION 'Administrator permission required' USING ERRCODE = '42501';
    END IF;
    RETURN jsonb_build_object(
        'institution_id', p_tenant,
        'allow_multi_department_hod', (
            SELECT allow_multi_department_hod FROM public.institutions WHERE institution_id = p_tenant),
        'heads', (
            SELECT COALESCE(jsonb_agg(jsonb_build_object(
                'department_id', h.department_id, 'faculty_user_id', h.faculty_user_id,
                'name', COALESCE(NULLIF(btrim(u.display_name), ''),
                    NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email),
                'email', u.email, 'assigned_at', h.assigned_at,
                'starts_on', h.starts_on, 'planned_end_on', h.planned_end_on,
                'is_active_faculty', public.transfer_is_active_faculty(h.faculty_user_id, p_tenant)
            ) ORDER BY h.department_id, h.assigned_at, h.faculty_user_id), '[]'::jsonb)
            FROM public.department_heads h
            JOIN public.users u ON u.id = h.faculty_user_id
            WHERE h.institution_id = p_tenant
              AND public.department_head_in_effect(h.ended_at, h.planned_end_on)
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
