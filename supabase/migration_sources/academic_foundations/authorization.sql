-- Do not reuse retired academic helpers or aggregate permission provenance.
CREATE FUNCTION public.assert_academic_foundation_actor(
    p_actor_user_id uuid, p_institution_id uuid, p_resource text
) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Academic Setup requires the trusted backend' USING ERRCODE = '42501';
    END IF;
    -- Permission and authority must come from the SAME institution-scoped admin
    -- assignment. Platform/org roles and delegated user grants cannot satisfy it.
    PERFORM 1
    FROM public.users u
    JOIN public.user_roles ur ON ur.user_id = u.id
    JOIN public.roles r ON r.id = ur.role_id
    JOIN public.role_permissions rp ON rp.role_id = r.id
    JOIN public.permissions permission ON permission.permission_id = rp.permission_id
    JOIN public.institutions i ON i.institution_id = p_institution_id
    JOIN public.organizations o ON o.organization_id = i.organization_id
    WHERE u.id = p_actor_user_id AND u.status = 'active'
      AND r.name = 'admin' AND r.is_active
      AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
      AND ur.scope_organization_id = i.organization_id
      AND i.is_active AND i.status = 'active' AND o.status = 'active'
      AND permission.is_active AND permission.scope = 'institution'
      AND permission.code IN (p_resource || '.manage', p_resource || '.*', '*')
    FOR SHARE OF u, ur, r, rp, permission, i, o;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Institution administrator with academic permission required'
            USING ERRCODE = '42501';
    END IF;
END;
$$;
