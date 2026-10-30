INSERT INTO public.permissions (code, name, description, scope, is_active)
VALUES
    ('registration.own.read', 'Read own semester registration', 'View assigned semesters and subject options', 'institution', true),
    ('registration.own.manage', 'Complete own semester registration', 'Choose complete subject options for an assigned section', 'institution', true)
ON CONFLICT (code) DO UPDATE SET is_active=true, scope='institution', updated_at=now();
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.permission_id FROM public.roles r CROSS JOIN public.permissions p
WHERE r.name='student' AND p.code IN ('registration.own.read','registration.own.manage')
ON CONFLICT (role_id, permission_id) DO NOTHING;

CREATE FUNCTION public.assert_semester_registration_admin(p_actor uuid,p_tenant uuid,p_permission text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    PERFORM 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id=u.id
    JOIN public.roles r ON r.id=ur.role_id JOIN public.role_permissions rp ON rp.role_id=r.id
    JOIN public.permissions p ON p.permission_id=rp.permission_id
    JOIN public.institutions i ON i.institution_id=p_tenant
    JOIN public.organizations org ON org.organization_id=i.organization_id
    WHERE u.id=p_actor AND u.status='active' AND r.name='admin' AND r.is_active
      AND ur.scope_type='institution' AND ur.scope_id=p_tenant AND ur.scope_organization_id=i.organization_id
      -- Existing student-account permissions retain their historical global catalogue label;
      -- authority still comes exclusively from this exact institution-scoped admin grant.
      AND i.is_active AND i.status='active' AND org.status='active' AND p.is_active AND p.scope IN ('institution','global')
      AND p.code IN (p_permission,split_part(p_permission,'.',1)||'.*','*')
    FOR SHARE OF u,ur,r,rp,p,i,org;
    IF NOT FOUND THEN RAISE EXCEPTION 'Administrator permission required' USING ERRCODE='42501'; END IF;
END;
$$;

CREATE FUNCTION public.assert_semester_registration_student(p_actor uuid, p_tenant uuid, p_action text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE result uuid;
BEGIN
    IF COALESCE(auth.role(),'')<>'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE='42501';
    END IF;
    SELECT s.student_id INTO result
    FROM public.students s JOIN public.users u ON u.id=s.user_id
    JOIN public.institutions i ON i.institution_id=s.institution_id
    JOIN public.organizations org ON org.organization_id=i.organization_id
    JOIN public.user_roles ur ON ur.user_id=u.id
    JOIN public.roles r ON r.id=ur.role_id
    JOIN public.role_permissions rp ON rp.role_id=r.id
    JOIN public.permissions p ON p.permission_id=rp.permission_id
    WHERE u.id=p_actor AND u.status='active' AND s.institution_id=p_tenant
      AND s.is_active AND s.status='active' AND s.approval_status='approved'
      AND i.is_active AND i.status='active' AND org.status='active'
      AND r.name='student' AND r.is_active AND ur.scope_type='institution'
      AND ur.scope_id=p_tenant AND ur.scope_organization_id=i.organization_id
      AND p.is_active AND p.scope='institution'
      AND p.code IN ('registration.own.'||p_action,'registration.*','*')
    FOR SHARE OF s,u,i,org,ur,r,rp,p;
    IF result IS NULL THEN
        RAISE EXCEPTION 'Approved student with registration permission required' USING ERRCODE='42501';
    END IF;
    RETURN result;
END;
$$;
