-- Retain an installed B05 rejection routine; older deployments lack this RPC.
DO $repair$
BEGIN
    IF to_regprocedure('public.b05_reject_membership(uuid,uuid,uuid,text)') IS NOT NULL THEN RETURN; END IF;
    EXECUTE $definition$
    CREATE FUNCTION public.b05_reject_membership(
        p_request_id uuid, p_institution_id uuid, p_decided_by uuid, p_reason text
    ) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $body$
    DECLARE applicant public.institution_membership_requests%ROWTYPE;
    BEGIN
        IF COALESCE(auth.role(), '') <> 'service_role' THEN
            RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
        END IF;
        PERFORM public.phase81_assert_institution_admin(p_decided_by, p_institution_id);
        PERFORM 1 FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.institutions i ON i.institution_id = p_institution_id
        JOIN public.organizations o ON o.organization_id = i.organization_id
        WHERE u.id = p_decided_by AND u.status = 'active' AND u.auth_user_id IS NOT NULL
          AND r.name = 'admin' AND r.is_active AND ur.scope_type = 'institution'
          AND ur.scope_id = i.institution_id AND ur.scope_organization_id = i.organization_id
          AND i.status = 'active' AND i.is_active AND o.status = 'active'
        FOR SHARE OF u, ur, r, i, o;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Active institution administrator required' USING ERRCODE = '42501';
        END IF;
        SELECT * INTO applicant FROM public.institution_membership_requests
        WHERE request_id = p_request_id AND institution_id = p_institution_id FOR UPDATE;
        IF NOT FOUND OR applicant.status NOT IN ('pending', 'rejected')
            OR applicant.requested_role NOT IN ('staff', 'faculty') THEN RETURN NULL; END IF;
        IF applicant.status = 'pending' THEN
            UPDATE public.institution_membership_requests
            SET status = 'rejected', decided_by_user_id = p_decided_by,
                decided_at = clock_timestamp(), decision_reason = p_reason, updated_at = clock_timestamp()
            WHERE request_id = p_request_id RETURNING * INTO applicant;
        END IF;
        IF NOT EXISTS(SELECT 1 FROM public.admin_audit_log
            WHERE institution_id = p_institution_id AND action = 'membership_request_rejected'
              AND table_name = 'institution_membership_requests' AND record_id = p_request_id::text
              AND record_data->>'access_granted' = 'false' AND status = 'success') THEN
            INSERT INTO public.admin_audit_log
                (actor_user_id, institution_id, action, table_name, record_id, record_data, status)
            VALUES(applicant.decided_by_user_id, p_institution_id, 'membership_request_rejected',
                'institution_membership_requests', p_request_id::text,
                jsonb_build_object('role', applicant.requested_role, 'status', 'rejected', 'access_granted', false),
                'success');
        END IF;
        RETURN to_jsonb(applicant) || jsonb_build_object('audit_persisted', true);
    END;
    $body$;
    $definition$;
END;
$repair$;

REVOKE ALL ON FUNCTION public.b05_reject_membership(uuid,uuid,uuid,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_reject_membership(uuid,uuid,uuid,text) TO service_role;
