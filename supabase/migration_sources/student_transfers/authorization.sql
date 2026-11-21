-- Every transfer command is called by the trusted backend with the
-- authenticated actor. Authority is re-derived here from current grants.
CREATE FUNCTION public.assert_transfer_backend()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE = '42501';
    END IF;
END;
$$;

-- Exact institution-scoped administrator grant with an active tenant.
CREATE FUNCTION public.transfer_admin_allowed(p_actor uuid, p_tenant uuid, p_permission text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id
        JOIN public.permissions p ON p.permission_id = rp.permission_id
        JOIN public.institutions i ON i.institution_id = p_tenant
        JOIN public.organizations org ON org.organization_id = i.organization_id
        WHERE u.id = p_actor AND u.status = 'active' AND r.name = 'admin' AND r.is_active
          AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
          AND ur.scope_organization_id = i.organization_id
          AND i.is_active AND i.status = 'active' AND org.status = 'active'
          AND p.is_active AND p.scope IN ('institution', 'global')
          AND p.code IN (p_permission, split_part(p_permission, '.', 1) || '.*', '*')
    );
$$;

-- An HOD must still be an active faculty member of the same institution.
CREATE FUNCTION public.transfer_is_active_faculty(p_user uuid, p_tenant uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.institutions i ON i.institution_id = p_tenant
        JOIN public.organizations org ON org.organization_id = i.organization_id
        WHERE u.id = p_user AND u.status = 'active' AND r.name = 'faculty' AND r.is_active
          AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
          AND ur.scope_organization_id = i.organization_id
          AND i.is_active AND i.status = 'active' AND org.status = 'active'
    );
$$;

-- Active departments the actor currently heads. Empty for everyone else.
CREATE FUNCTION public.transfer_hod_departments(p_actor uuid, p_tenant uuid)
RETURNS uuid[] LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(array_agg(h.department_id ORDER BY h.department_id), '{}'::uuid[])
    FROM public.department_heads h
    JOIN public.departments d
        ON d.department_id = h.department_id AND d.institution_id = p_tenant AND d.is_active
    WHERE h.institution_id = p_tenant AND h.faculty_user_id = p_actor AND h.ended_at IS NULL
      AND public.transfer_is_active_faculty(p_actor, p_tenant);
$$;

-- Resolves the actor's own approved, active student record. A browser can
-- never name another student because the identity is derived from the actor.
CREATE FUNCTION public.assert_transfer_student(p_actor uuid, p_tenant uuid, p_permission text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_student uuid;
BEGIN
    PERFORM public.assert_transfer_backend();
    SELECT s.student_id INTO v_student
    FROM public.students s
    JOIN public.users u ON u.id = s.user_id
    JOIN public.institutions i ON i.institution_id = s.institution_id
    JOIN public.organizations org ON org.organization_id = i.organization_id
    JOIN public.user_roles ur ON ur.user_id = u.id
    JOIN public.roles r ON r.id = ur.role_id
    JOIN public.role_permissions rp ON rp.role_id = r.id
    JOIN public.permissions p ON p.permission_id = rp.permission_id
    WHERE u.id = p_actor AND u.status = 'active' AND s.institution_id = p_tenant
      AND s.is_active AND s.status = 'active' AND s.approval_status = 'approved'
      AND i.is_active AND i.status = 'active' AND org.status = 'active'
      AND r.name = 'student' AND r.is_active AND ur.scope_type = 'institution'
      AND ur.scope_id = p_tenant AND ur.scope_organization_id = i.organization_id
      AND p.is_active AND p.scope = 'institution'
      AND p.code IN (p_permission, 'transfers.*', '*')
    LIMIT 1
    FOR SHARE OF s;
    IF v_student IS NULL THEN
        RAISE EXCEPTION 'Approved student with transfer permission required' USING ERRCODE = '42501';
    END IF;
    RETURN v_student;
END;
$$;

-- The student's current placement: the registration in the latest term,
-- matching the ordering used by the student directory.
CREATE FUNCTION public.transfer_current_registration(p_student uuid, p_tenant uuid)
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT registration.semester_registration_id
    FROM public.student_semester_registrations registration
    JOIN public.semesters term ON term.semester_id = registration.semester_id
    WHERE registration.student_id = p_student AND registration.institution_id = p_tenant
    ORDER BY term.start_date DESC, registration.assigned_at DESC, registration.semester_registration_id
    LIMIT 1;
$$;
