CREATE FUNCTION public.academic_package_actor(p_actor uuid, p_tenant uuid) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE actor_role text;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;
    SELECT r.name INTO actor_role
    FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id
    JOIN public.roles r ON r.id = ur.role_id
    JOIN public.institutions i ON i.institution_id = p_tenant
    WHERE u.id = p_actor AND u.status = 'active' AND r.is_active
      AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
      AND r.name IN ('admin','staff','faculty','student') AND i.is_active AND i.status = 'active'
    ORDER BY CASE r.name WHEN 'admin' THEN 1 WHEN 'staff' THEN 2 WHEN 'faculty' THEN 3 ELSE 4 END
    LIMIT 1 FOR SHARE OF u, ur, r, i;
    IF actor_role IS NULL THEN
        RAISE EXCEPTION 'Active institution account required' USING ERRCODE = '42501';
    END IF;
    RETURN actor_role;
END;
$$;

CREATE FUNCTION public.academic_package_allowed(
    p_actor uuid, p_tenant uuid, p_permission text, p_class uuid DEFAULT NULL
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE role_name text; class_row public.academic_classes; program uuid; department uuid; year_id uuid;
    responsibility uuid;
BEGIN
    role_name := public.academic_package_actor(p_actor, p_tenant);
    IF role_name IN ('admin','staff','student') THEN
        PERFORM 1 FROM public.user_roles ur JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id
        JOIN public.permissions permission ON permission.permission_id = rp.permission_id
        WHERE ur.user_id = p_actor AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
          AND r.name = role_name AND r.is_active AND permission.is_active
          AND (permission.code = p_permission OR permission.code = '*'
            OR (right(permission.code, 2) = '.*'
                AND left(p_permission, length(permission.code)-1) = left(permission.code, length(permission.code)-1)))
        LIMIT 1 FOR SHARE OF ur, r, rp, permission;
        IF FOUND THEN RETURN true; END IF;
        IF role_name = 'staff' THEN
            PERFORM 1 FROM public.user_permission_grants g
            JOIN public.permissions permission USING(permission_id)
            WHERE g.user_id = p_actor AND g.institution_id = p_tenant AND g.revoked_at IS NULL
              AND permission.is_active AND permission.code = p_permission
            LIMIT 1 FOR SHARE OF g, permission;
            IF FOUND THEN RETURN true; END IF;
        END IF;
    END IF;
    IF role_name <> 'faculty' OR p_class IS NULL THEN RETURN false; END IF;
    SELECT * INTO class_row FROM public.academic_classes
    WHERE class_id = p_class AND institution_id = p_tenant;
    IF NOT FOUND THEN RETURN false; END IF;
    SELECT b.program_id, p.department_id INTO program, department
    FROM public.academic_batches b JOIN public.programs p USING(program_id)
    WHERE b.batch_id = class_row.batch_id AND b.institution_id = p_tenant AND b.is_active AND p.is_active;
    SELECT academic_year_id INTO year_id FROM public.semesters WHERE semester_id = class_row.semester_id;
    SELECT fr.responsibility_id INTO responsibility FROM public.faculty_responsibilities fr
    JOIN public.responsibility_definitions rd ON rd.code = fr.responsibility_code
    JOIN public.responsibility_permissions rp ON rp.responsibility_code = rd.code
    JOIN public.permissions permission ON permission.permission_id = rp.permission_id
    WHERE fr.faculty_user_id = p_actor AND fr.institution_id = p_tenant
      AND fr.is_active AND fr.revoked_at IS NULL AND fr.start_at <= clock_timestamp()
      AND (fr.end_at IS NULL OR clock_timestamp() < fr.end_at) AND rd.is_active
      AND fr.scope_type = ANY(rd.allowed_scope_types)
      AND permission.is_active AND permission.code = p_permission
      AND ((fr.responsibility_code = 'hod' AND fr.scope_type = 'department' AND fr.department_id = department)
        OR (fr.responsibility_code = 'class_in_charge' AND fr.scope_type = 'section'
          AND fr.program_id = program AND fr.semester_id = class_row.semester_id
          AND fr.academic_year_id = year_id
          AND EXISTS (SELECT 1 FROM public.academic_class_subjects cs
            WHERE cs.class_id = p_class AND cs.section_id = fr.section_id)
          AND EXISTS (SELECT 1 FROM public.academic_class_responsibilities cr
            WHERE cr.class_id = p_class AND cr.responsibility_id = fr.responsibility_id)))
    LIMIT 1 FOR SHARE OF fr, rd, rp, permission;
    IF responsibility IS NULL THEN RETURN false; END IF;
    -- A lock wait alone does not change the row, so WHERE may have evaluated
    -- before the appointment expired. Recheck wall-clock validity after locks.
    RETURN EXISTS (SELECT 1 FROM public.faculty_responsibilities fr
        WHERE fr.responsibility_id = responsibility AND fr.is_active AND fr.revoked_at IS NULL
          AND fr.start_at <= clock_timestamp() AND (fr.end_at IS NULL OR clock_timestamp() < fr.end_at));
END;
$$;

CREATE FUNCTION public.academic_package_require(
    p_actor uuid, p_tenant uuid, p_permission text, p_class uuid DEFAULT NULL
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF NOT public.academic_package_allowed(p_actor, p_tenant, p_permission, p_class) THEN
        RAISE EXCEPTION 'Academic package permission or scope denied' USING ERRCODE = '42501';
    END IF;
END;
$$;

CREATE FUNCTION public.academic_package_owns(p_actor uuid, p_tenant uuid, p_placement uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE registration public.student_registrations; identity jsonb;
BEGIN
    SELECT r.* INTO registration FROM public.academic_class_placements cp
    JOIN public.student_registrations r USING(registration_id)
    WHERE cp.placement_id = p_placement AND r.institution_id = p_tenant;
    IF NOT FOUND THEN RETURN false; END IF;
    identity := public.faculty_attendance_identity(p_tenant, registration.register_number, registration.university_roll_number);
    IF COALESCE((identity->>'conflict')::boolean, true) THEN RETURN false; END IF;
    PERFORM 1 FROM public.students s WHERE s.student_id = (identity->>'student_id')::uuid
      AND s.user_id = p_actor AND s.institution_id = p_tenant
      AND s.approval_status = 'approved' AND s.is_active AND s.status = 'active' FOR SHARE;
    RETURN FOUND;
END;
$$;

CREATE FUNCTION public.academic_package_audit(p_actor uuid, p_tenant uuid, p_operation text,
    p_table text, p_id uuid, p_before jsonb, p_after jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.package.' || p_operation, p_table, p_id::text,
        jsonb_build_object('before', p_before, 'after', p_after));
END;
$$;
