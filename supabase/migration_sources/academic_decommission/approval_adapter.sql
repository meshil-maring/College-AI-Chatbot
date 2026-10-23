-- The observed deployment has never installed the optional B05 invitation
-- draft/approval repair. Keep existing approval routines untouched; provide
-- only the identity/account transaction required by the retained backend.
DO $adapter$
BEGIN
    IF to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NOT NULL THEN RETURN; END IF;
    EXECUTE $definition$
    CREATE FUNCTION public.b05_approve_student(
        p_student_id uuid, p_institution_id uuid, p_actor_user_id uuid, p_actor_auth_user_id uuid
    ) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $body$
    DECLARE student public.students; organization uuid; student_role uuid;
    BEGIN
        IF COALESCE(auth.role(),'') <> 'service_role' THEN
            RAISE EXCEPTION 'Authorized student approver required' USING ERRCODE='42501';
        END IF;
        PERFORM 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id=u.id
        JOIN public.roles r ON r.id=ur.role_id JOIN public.institutions i ON i.institution_id=p_institution_id
        JOIN public.organizations o ON o.organization_id=i.organization_id
        WHERE u.id=p_actor_user_id AND u.auth_user_id=p_actor_auth_user_id AND u.status='active'
          AND r.name IN('admin','staff') AND r.is_active AND ur.scope_type='institution'
          AND ur.scope_id=p_institution_id AND ur.scope_organization_id=i.organization_id
          AND i.status='active' AND i.is_active AND o.status='active' FOR SHARE OF u,ur,r,i,o;
        IF NOT FOUND THEN RAISE EXCEPTION 'Authorized student approver required' USING ERRCODE='42501'; END IF;
        PERFORM 1 FROM public.user_roles ur JOIN public.roles r ON r.id=ur.role_id
        JOIN public.role_permissions rp ON rp.role_id=r.id JOIN public.permissions p ON p.permission_id=rp.permission_id
        WHERE ur.user_id=p_actor_user_id AND ur.scope_type='institution' AND ur.scope_id=p_institution_id
          AND r.name IN('admin','staff') AND r.is_active AND p.is_active
          AND p.code IN('students.approve','students.*','*') FOR SHARE OF ur,r,rp,p;
        IF NOT FOUND THEN
            PERFORM 1 FROM public.user_permission_grants g JOIN public.permissions p USING(permission_id)
            WHERE g.user_id=p_actor_user_id AND g.institution_id=p_institution_id AND g.revoked_at IS NULL
              AND p.is_active AND p.code IN('students.approve','students.*','*') FOR SHARE OF g,p;
            IF NOT FOUND THEN RAISE EXCEPTION 'Student approval permission required' USING ERRCODE='42501'; END IF;
        END IF;
        SELECT * INTO student FROM public.students
        WHERE student_id=p_student_id AND institution_id=p_institution_id FOR UPDATE;
        IF NOT FOUND THEN RETURN jsonb_build_object('not_found',true); END IF;
        IF student.approval_status NOT IN('pending','approved') THEN RETURN jsonb_build_object('conflict',true); END IF;
        SELECT organization_id INTO organization FROM public.institutions
        WHERE institution_id=p_institution_id AND status='active' AND is_active FOR SHARE;
        SELECT id INTO student_role FROM public.roles WHERE name='student' AND is_active FOR SHARE;
        PERFORM 1 FROM public.users WHERE id=student.user_id AND status='active' AND auth_user_id IS NOT NULL
          AND lower(email)=lower(student.email) FOR UPDATE;
        IF NOT FOUND OR student_role IS NULL OR organization IS NULL THEN
            RAISE EXCEPTION 'Student provisioning prerequisites missing' USING ERRCODE='23514';
        END IF;
        INSERT INTO public.user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id)
        VALUES(student.user_id,student_role,'institution',p_institution_id,organization)
        ON CONFLICT(user_id,role_id) DO NOTHING;
        IF NOT EXISTS(SELECT 1 FROM public.user_roles WHERE user_id=student.user_id AND role_id=student_role
            AND scope_type='institution' AND scope_id=p_institution_id AND scope_organization_id=organization) THEN
            RAISE EXCEPTION 'Student role scope conflict' USING ERRCODE='42501';
        END IF;
        UPDATE public.students SET approval_status='approved' WHERE student_id=p_student_id RETURNING * INTO student;
        -- The student row lock serializes all calls for this identity. Reuse
        -- the existing action/snapshot contract without adding invitation or
        -- decision-key schema to deployments that never installed B05.
        IF NOT EXISTS(SELECT 1 FROM public.admin_audit_log WHERE institution_id=p_institution_id
            AND action='student.approve' AND table_name='students' AND record_id=p_student_id::text
            AND record_data->>'role_granted'='true' AND status='success') THEN
            INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data,status)
            VALUES(p_actor_user_id,p_institution_id,'student.approve','students',p_student_id::text,
                jsonb_build_object('approval_status','approved','role_granted',true),'success');
        END IF;
        RETURN jsonb_build_object('student',to_jsonb(student),'role_granted',true,'audit_persisted',true);
    END;
    $body$;
    $definition$;
    EXECUTE 'REVOKE ALL ON FUNCTION public.b05_approve_student(uuid,uuid,uuid,uuid) FROM PUBLIC,anon,authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.b05_approve_student(uuid,uuid,uuid,uuid) TO service_role';
END;
$adapter$;
