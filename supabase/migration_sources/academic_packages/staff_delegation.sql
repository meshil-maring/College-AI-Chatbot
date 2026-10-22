CREATE OR REPLACE FUNCTION public.phase81_manage_staff_permission_grants(
    p_actor_user_id uuid, p_institution_id uuid, p_target_user_id uuid,
    p_permission_codes text[], p_grant boolean
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE permission_code text; permission_row public.permissions; changed_count integer := 0; grant_id uuid;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
    IF p_actor_user_id = p_target_user_id THEN
        RAISE EXCEPTION 'Administrators cannot delegate staff permissions to themselves' USING ERRCODE = '42501';
    END IF;
    PERFORM 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id JOIN public.roles r ON r.id = ur.role_id
    WHERE u.id = p_target_user_id AND u.status = 'active' AND r.name = 'staff' AND r.is_active
      AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id FOR SHARE OF u, ur, r;
    IF NOT FOUND THEN RAISE EXCEPTION 'Active institution staff member required' USING ERRCODE = '42501'; END IF;
    IF COALESCE(array_length(p_permission_codes, 1), 0) NOT BETWEEN 1 AND 32
        OR cardinality(p_permission_codes) <> (SELECT count(DISTINCT code) FROM unnest(p_permission_codes) code) THEN
        RAISE EXCEPTION 'Supply 1 to 32 unique permission codes' USING ERRCODE = '23514';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'staff-permissions:' || p_institution_id::text || ':' || p_target_user_id::text, 0));
    FOREACH permission_code IN ARRAY p_permission_codes LOOP
        IF permission_code <> ALL(ARRAY[
            'ai.knowledge.create','attendance.read','attendance.manage','results.read','results.manage',
            'students.read','students.update','documents.read','documents.create','documents.update',
            'notices.read','notices.create','notices.update','academic.curriculum.read','academic.class.read',
            'academic.package.assign','academic.package.change','academic.package.requests.review'
        ]::text[]) THEN
            RAISE EXCEPTION 'Permission is outside the staff delegation allowlist' USING ERRCODE = '42501';
        END IF;
        SELECT * INTO permission_row FROM public.permissions p WHERE p.code = permission_code FOR SHARE;
        IF NOT FOUND OR (p_grant AND NOT permission_row.is_active) THEN
            RAISE EXCEPTION 'Unknown or inactive permission' USING ERRCODE = '23514';
        END IF;
        grant_id := NULL;
        IF p_grant THEN
            INSERT INTO public.user_permission_grants(user_id, institution_id, permission_id, granted_by)
            VALUES (p_target_user_id, p_institution_id, permission_row.permission_id, p_actor_user_id)
            ON CONFLICT (user_id, institution_id, permission_id) WHERE revoked_at IS NULL DO NOTHING
            RETURNING user_permission_grants.grant_id INTO grant_id;
        ELSE
            UPDATE public.user_permission_grants g SET revoked_by = p_actor_user_id, revoked_at = clock_timestamp()
            WHERE g.user_id = p_target_user_id AND g.institution_id = p_institution_id
              AND g.permission_id = permission_row.permission_id AND g.revoked_at IS NULL RETURNING g.grant_id INTO grant_id;
        END IF;
        IF grant_id IS NOT NULL THEN
            INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data, status)
            VALUES (p_actor_user_id, p_institution_id, CASE WHEN p_grant THEN 'permission.grant' ELSE 'permission.revoke' END,
                'user_permission_grants', grant_id::text,
                jsonb_build_object('target_user_id', p_target_user_id, 'permission_code', permission_code, 'source', 'direct'), 'success');
            changed_count := changed_count + 1;
        END IF;
    END LOOP;
    RETURN changed_count;
END;
$$;
REVOKE ALL ON FUNCTION public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean) TO service_role;
