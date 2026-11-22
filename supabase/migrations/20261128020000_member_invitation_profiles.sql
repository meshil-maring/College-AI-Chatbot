-- Staff/Faculty invitations that carry the employee profile (User Management U9).
--
-- create_member_invitation gains p_profile: the common profile, the Faculty or
-- Staff profile and additional departments entered by the administrator. It is
-- stored on the invitation, is immutable, and is applied when the person accepts,
-- in the same transaction as the role grant and primary department. Invitations
-- without a profile keep working; the administrator completes the profile later.
--
-- The previous nine-argument function is replaced so PostgREST resolves one
-- candidate. P1201 department, P1202 already a member, P1203 invitation pending,
-- P1204 employee ID in use, 22023 malformed input.
BEGIN;

DROP FUNCTION public.create_member_invitation(uuid, uuid, text, text, text, uuid, text, timestamptz, text);

CREATE FUNCTION public.create_member_invitation(
    p_actor uuid, p_tenant uuid, p_email text, p_full_name text, p_role text,
    p_department uuid, p_token_hash text, p_expires_at timestamptz, p_protected_token text,
    p_profile jsonb DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_email text := lower(btrim(p_email));
    v_invitation public.platform_admin_invitations%ROWTYPE;
    v_outbox_id uuid;
    v_employee_id text := btrim(p_profile #>> '{common,employee_id}');
    v_additional jsonb := COALESCE(p_profile -> 'additional_department_ids', '[]'::jsonb);
BEGIN
    -- Requires the service role and an active administrator of this institution.
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    IF p_role IS NULL OR p_role NOT IN ('staff', 'faculty') THEN
        RAISE EXCEPTION 'Unsupported member role' USING ERRCODE = '22023';
    END IF;
    IF v_email IS NULL OR v_email = '' THEN
        RAISE EXCEPTION 'Email required' USING ERRCODE = '22023';
    END IF;
    PERFORM 1 FROM public.departments
        WHERE department_id = p_department AND institution_id = p_tenant AND is_active
        FOR SHARE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Choose an active department of this institution' USING ERRCODE = 'P1201';
    END IF;
    IF p_profile IS NOT NULL THEN
        IF jsonb_typeof(p_profile -> 'common') IS DISTINCT FROM 'object'
           OR jsonb_typeof(p_profile -> p_role) IS DISTINCT FROM 'object'
           OR COALESCE(v_employee_id, '') = '' OR jsonb_typeof(v_additional) <> 'array' THEN
            RAISE EXCEPTION 'Profile details for this role are required' USING ERRCODE = '22023';
        END IF;
        IF jsonb_array_length(v_additional) > 10 OR v_additional ? p_department::text THEN
            RAISE EXCEPTION 'Check the additional departments' USING ERRCODE = '22023';
        END IF;
        IF EXISTS (
            SELECT 1 FROM jsonb_array_elements_text(v_additional) d
            WHERE NOT EXISTS (SELECT 1 FROM public.departments x
                              WHERE x.department_id::text = d AND x.institution_id = p_tenant AND x.is_active)
        ) THEN
            RAISE EXCEPTION 'Choose active departments of this institution' USING ERRCODE = 'P1201';
        END IF;
        PERFORM public.member_employee_id_lock(p_tenant, v_employee_id);
        IF public.member_employee_id_taken(p_tenant, v_employee_id, NULL, NULL) THEN
            RAISE EXCEPTION 'This employee ID is already in use' USING ERRCODE = 'P1204';
        END IF;
    END IF;
    -- One invitation decision per person per institution at a time.
    PERFORM pg_advisory_xact_lock(hashtextextended(p_tenant::text || ':' || v_email, 0));
    IF EXISTS (
        SELECT 1 FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
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

    INSERT INTO public.platform_admin_invitations (
        institution_id, email, token_hash, role_name, status, expires_at, created_by,
        email_delivery_status, admin_invited, invited_department_id, invited_full_name, invited_profile
    ) VALUES (
        p_tenant, v_email, p_token_hash, p_role, 'invited', p_expires_at, p_actor,
        'pending', true, p_department, NULLIF(btrim(p_full_name), ''), p_profile
    ) RETURNING * INTO v_invitation;

    INSERT INTO public.email_outbox (aggregate_id, protected_token)
    VALUES (v_invitation.invitation_id, p_protected_token)
    RETURNING id INTO v_outbox_id;

    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'membership.invitation.created', 'platform_admin_invitations',
        v_invitation.invitation_id::text,
        jsonb_build_object('email', v_email, 'role', p_role, 'department_id', p_department,
            'expires_at', p_expires_at, 'employee_id', v_employee_id));

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;

-- Apply the invited profile once b05_finalize_invitation marks the invitation
-- accepted. Runs inside that transaction, after the role and primary department.
-- Departments deactivated since the invitation are skipped, as for the primary.
CREATE FUNCTION public.member_invitation_apply_profile()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.member_profile_apply(NEW.institution_id, NEW.accepted_user_id, NEW.role_name,
        NEW.invited_profile, NEW.created_by, NEW.invitation_id);
    INSERT INTO public.institution_member_additional_departments (institution_id, user_id, department_id, assigned_by)
    SELECT NEW.institution_id, NEW.accepted_user_id, d.department_id, NEW.created_by
    FROM public.departments d
    WHERE d.institution_id = NEW.institution_id AND d.is_active
      AND d.department_id::text IN (
          SELECT jsonb_array_elements_text(COALESCE(NEW.invited_profile -> 'additional_department_ids', '[]')))
      AND NOT EXISTS (SELECT 1 FROM public.institution_member_departments p
                      WHERE p.institution_id = NEW.institution_id AND p.user_id = NEW.accepted_user_id
                        AND p.department_id = d.department_id)
    ON CONFLICT (institution_id, user_id, department_id) DO NOTHING;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_member_invitation_apply_profile
    AFTER UPDATE OF status ON public.platform_admin_invitations
    FOR EACH ROW
    WHEN (NEW.status = 'accepted' AND OLD.status IS DISTINCT FROM 'accepted'
          AND NEW.admin_invited AND NEW.invited_profile IS NOT NULL
          AND NEW.accepted_user_id IS NOT NULL)
    EXECUTE FUNCTION public.member_invitation_apply_profile();

REVOKE ALL ON FUNCTION public.member_invitation_apply_profile() FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.create_member_invitation(
    uuid, uuid, text, text, text, uuid, text, timestamptz, text, jsonb
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_member_invitation(
    uuid, uuid, text, text, text, uuid, text, timestamptz, text, jsonb
) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
