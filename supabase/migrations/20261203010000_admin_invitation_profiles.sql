-- Administrator invitations carry an optional employee profile, and the
-- administrator list shows each administrator's profile (20261203000000).
-- create_admin_invitation is as in 20261202010000 plus p_profile.
BEGIN;

DROP FUNCTION public.create_admin_invitation(uuid, uuid, text, text, text, timestamptz, text, text[]);

CREATE FUNCTION public.create_admin_invitation(
    p_actor uuid, p_tenant uuid, p_email text, p_full_name text,
    p_token_hash text, p_expires_at timestamptz, p_protected_token text, p_access_areas text[] DEFAULT NULL,
    p_profile jsonb DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_email text := lower(btrim(p_email));
    v_areas text[];
    v_profile jsonb;
    v_invitation public.platform_admin_invitations%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    PERFORM public.institution_owner_assert(p_actor, p_tenant);
    IF v_email IS NULL OR v_email = '' THEN
        RAISE EXCEPTION 'Email required' USING ERRCODE = '22023';
    END IF;
    IF p_access_areas IS NOT NULL AND NOT p_access_areas <@ public.institution_admin_areas() THEN
        RAISE EXCEPTION 'Unknown access area' USING ERRCODE = '22023';
    END IF;
    IF p_access_areas IS NOT NULL AND NOT public.institution_admin_areas() <@ p_access_areas THEN
        v_areas := ARRAY(SELECT a FROM unnest(public.institution_admin_areas()) WITH ORDINALITY t(a, n)
                         WHERE a = ANY (p_access_areas) ORDER BY n);
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(p_tenant::text || ':' || v_email, 0));
    IF EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id
        WHERE lower(u.email) = v_email AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
    ) THEN
        RAISE EXCEPTION 'This person already belongs to the institution' USING ERRCODE = 'P1202';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.platform_admin_invitations
        WHERE institution_id = p_tenant AND lower(email) = v_email
          AND status = 'invited' AND expires_at > clock_timestamp()
    ) THEN
        RAISE EXCEPTION 'An invitation is already pending for this email' USING ERRCODE = 'P1203';
    END IF;
    v_profile := public.admin_invitation_profile(p_tenant, p_profile);
    INSERT INTO public.platform_admin_invitations (
        institution_id, email, token_hash, role_name, status, expires_at, created_by,
        email_delivery_status, admin_invited, invited_full_name, invited_admin_areas, invited_profile
    ) VALUES (
        p_tenant, v_email, p_token_hash, 'admin', 'invited', p_expires_at, p_actor,
        'pending', true, NULLIF(btrim(p_full_name), ''), v_areas, v_profile
    ) RETURNING * INTO v_invitation;
    INSERT INTO public.email_outbox (aggregate_id, protected_token)
    VALUES (v_invitation.invitation_id, p_protected_token) RETURNING id INTO v_outbox_id;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'institution.admin.invite', 'platform_admin_invitations',
        v_invitation.invitation_id::text, jsonb_build_object('email', v_email, 'expires_at', p_expires_at,
            'access_areas', to_jsonb(v_areas), 'profile', v_profile -> 'common'));
    RETURN (to_jsonb(v_invitation) - 'token_hash') || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;

-- As in 20261202000000, plus each administrator's and invitation's profile.
CREATE OR REPLACE FUNCTION public.read_institution_admins(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    RETURN jsonb_build_object(
        'owner_user_id', (SELECT owner_user_id FROM public.institutions WHERE institution_id = p_tenant),
        'access_areas', to_jsonb(public.institution_admin_areas()),
        'administrators', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'user_id', u.id, 'email', u.email, 'status', u.status, 'assigned_at', ur.assigned_at,
                'name', COALESCE(NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email),
                'access_areas', to_jsonb(a.areas),
                'profile', CASE WHEN p.user_id IS NULL THEN NULL ELSE jsonb_build_object(
                    'employee_id', p.employee_id, 'phone', p.phone, 'designation', p.designation,
                    'joining_date', p.joining_date) END
            ) ORDER BY ur.assigned_at, u.id)
            FROM public.user_roles ur
            JOIN public.roles r ON r.id = ur.role_id AND r.name = 'admin'
            JOIN public.users u ON u.id = ur.user_id
            LEFT JOIN public.institution_admin_access a ON a.institution_id = p_tenant AND a.user_id = u.id
            LEFT JOIN public.institution_member_profiles p ON p.institution_id = p_tenant AND p.user_id = u.id
            WHERE ur.scope_type = 'institution' AND ur.scope_id = p_tenant), '[]'::jsonb),
        'invitations', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'invitation_id', i.invitation_id, 'email', i.email, 'full_name', i.invited_full_name,
                'expires_at', i.expires_at, 'created_at', i.created_at,
                'email_delivery_status', i.email_delivery_status,
                'access_areas', to_jsonb(i.invited_admin_areas),
                'profile', i.invited_profile -> 'common'
            ) ORDER BY i.created_at DESC)
            FROM public.platform_admin_invitations i
            WHERE i.institution_id = p_tenant AND i.role_name = 'admin' AND i.status = 'invited'
              AND i.expires_at > clock_timestamp()), '[]'::jsonb)
    );
END;
$$;

REVOKE ALL ON FUNCTION public.create_admin_invitation(uuid, uuid, text, text, text, timestamptz, text, text[], jsonb)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_admin_invitation(uuid, uuid, text, text, text, timestamptz, text, text[], jsonb)
    TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
