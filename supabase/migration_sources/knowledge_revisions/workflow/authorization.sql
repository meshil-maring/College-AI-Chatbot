-- Only the trusted backend supplies actor identity. Resolve role and permission
-- provenance again in PostgreSQL; client audience selections confer no grants.
CREATE FUNCTION public.knowledge_actor_roles(actor uuid, tenant uuid, required_permission text)
RETURNS text[] LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE result text[] := '{}'; role_name text;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Trusted backend required' USING ERRCODE = '42501';
    END IF;
    IF (SELECT count(DISTINCT ur.scope_id) FROM public.user_roles ur
        JOIN public.roles r ON r.id = ur.role_id
        WHERE ur.user_id = actor AND ur.scope_type = 'institution' AND r.is_active
            AND r.name IN ('admin', 'faculty', 'staff', 'student')) <> 1 THEN RETURN result; END IF;
    FOR role_name IN
        SELECT r.name FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.role_permissions rp ON rp.role_id = r.id
        JOIN public.permissions permission ON permission.permission_id = rp.permission_id
        JOIN public.institutions i ON i.institution_id = tenant
        JOIN public.organizations o ON o.organization_id = i.organization_id
        WHERE u.id = actor AND u.status = 'active' AND r.is_active
            AND r.name IN ('admin', 'faculty', 'staff', 'student')
            AND ur.scope_type = 'institution' AND ur.scope_id = tenant
            AND ur.scope_organization_id = i.organization_id
            AND i.is_active AND i.status = 'active' AND o.status = 'active'
            AND permission.is_active AND permission.scope IN ('institution', 'global')
            AND permission.code IN (required_permission, split_part(required_permission, '.', 1) || '.*', '*')
            AND (r.name <> 'student' OR EXISTS (
                SELECT 1 FROM public.students s WHERE s.user_id = actor AND s.institution_id = tenant
                    AND s.approval_status = 'approved' AND s.is_active))
        FOR SHARE OF u, ur, r, rp, permission, i, o
    LOOP
        result := array_append(result, role_name);
    END LOOP;
    FOR role_name IN
        SELECT r.name FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.user_permission_grants grant_row ON grant_row.user_id = u.id
        JOIN public.permissions permission ON permission.permission_id = grant_row.permission_id
        JOIN public.institutions i ON i.institution_id = tenant
        JOIN public.organizations o ON o.organization_id = i.organization_id
        WHERE u.id = actor AND u.status = 'active' AND r.name = 'staff' AND r.is_active
            AND ur.scope_type = 'institution' AND ur.scope_id = tenant
            AND ur.scope_organization_id = i.organization_id
            AND grant_row.institution_id = tenant AND grant_row.revoked_at IS NULL
            AND permission.code = required_permission AND permission.is_active
            AND permission.scope IN ('institution', 'global') AND i.is_active AND i.status = 'active' AND o.status = 'active'
        FOR SHARE OF u, ur, r, grant_row, permission, i, o
    LOOP
        result := array_append(result, role_name);
    END LOOP;
    RETURN result;
END;
$$;

CREATE FUNCTION public.assert_knowledge_actor(actor uuid, tenant uuid, permission text, administrator boolean DEFAULT false)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE roles text[];
BEGIN
    roles := public.knowledge_actor_roles(actor, tenant, permission);
    IF (administrator AND NOT 'admin' = ANY(roles))
        OR (NOT administrator AND NOT roles && ARRAY['admin', 'faculty', 'staff']) THEN
        RAISE EXCEPTION 'Resource permission required' USING ERRCODE = '42501';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('knowledge:' || tenant::text, 0));
END;
$$;

CREATE FUNCTION public.audit_knowledge_revision(actor uuid, tenant uuid, action text, revision uuid, previous jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data)
    SELECT actor, tenant, 'knowledge.' || action, 'knowledge_source_revisions', revision::text,
        jsonb_build_object('before', previous, 'after', to_jsonb(r))
    FROM public.knowledge_source_revisions r WHERE r.revision_id = revision;
END;
$$;
