-- Accept Staff/Faculty invitations created by an institution administrator.
--
-- Companion to 20261127000000_member_invitations. Finalization is unchanged
-- from 20261017000000 except for administrator invitations (admin_invited):
-- the approved membership request is recorded at acceptance, decided by the
-- inviting administrator, instead of being required beforehand, and the
-- department chosen at invitation is assigned. All of it commits with the
-- role grant in one transaction.
BEGIN;

-- Finalization from 20261017000000, changed only for administrator invitations
-- (admin_invited): the approved request is recorded at acceptance instead of
-- being required beforehand, and the chosen department is assigned.
CREATE OR REPLACE FUNCTION public.b05_finalize_invitation(
    p_kind text, p_invitation_id uuid, p_token_hash text,
    p_acceptance_id uuid, p_target_user_id uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_invitation record;
    v_decision_time timestamptz;
    v_operation public.b05_invitation_operations%ROWTYPE;
    v_admin_invited boolean := false;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;
    IF p_acceptance_id IS NULL OR p_token_hash IS NULL THEN RETURN NULL; END IF;
    IF p_kind = 'institution' THEN
        SELECT * INTO v_invitation FROM public.platform_admin_invitations
            WHERE invitation_id = p_invitation_id FOR UPDATE;
    ELSIF p_kind = 'platform' THEN
        SELECT i.*, 'super_admin'::text AS role_name, NULL::uuid AS institution_id
            INTO v_invitation FROM public.platform_super_admin_invitations i
            WHERE invitation_id = p_invitation_id FOR UPDATE OF i;
    ELSE
        RAISE EXCEPTION 'Invalid invitation kind' USING ERRCODE = '23514';
    END IF;
    IF NOT FOUND OR v_invitation.token_hash IS DISTINCT FROM p_token_hash
       OR v_invitation.acceptance_id IS DISTINCT FROM p_acceptance_id THEN RETURN NULL; END IF;
    SELECT * INTO v_operation FROM public.b05_invitation_operations
        WHERE acceptance_id = p_acceptance_id FOR UPDATE;
    IF NOT FOUND OR v_operation.kind IS DISTINCT FROM p_kind
       OR v_operation.invitation_id IS DISTINCT FROM p_invitation_id
       OR v_operation.user_id IS DISTINCT FROM p_target_user_id
       OR v_operation.stage NOT IN ('user_created', 'accepted', 'confirmed') THEN RETURN NULL; END IF;
    IF v_invitation.status = 'accepted' AND v_invitation.accepted_user_id = p_target_user_id THEN
        PERFORM 1 FROM public.users WHERE id = p_target_user_id
            AND auth_user_id = v_operation.auth_user_id AND status = 'active'
            AND lower(email) = lower(v_invitation.email) FOR SHARE;
        IF NOT FOUND THEN RETURN NULL; END IF;
        RETURN jsonb_build_object('accepted', true, 'already_applied', true);
    END IF;
    IF v_invitation.status <> 'invited' OR v_invitation.expires_at <= clock_timestamp() THEN
        RETURN NULL;
    END IF;
    IF p_kind = 'platform' THEN
        PERFORM public.b05_assert_platform_actor(v_invitation.created_by);
    ELSE
        v_admin_invited := v_invitation.admin_invited AND v_invitation.role_name IN ('staff', 'faculty');
        IF v_invitation.role_name = 'admin' THEN
            PERFORM public.b05_assert_platform_actor(v_invitation.created_by);
        ELSE
            -- The inviting administrator must still administer the institution.
            PERFORM public.phase81_assert_institution_admin(
                v_invitation.created_by, v_invitation.institution_id);
            IF NOT v_admin_invited THEN
                PERFORM 1 FROM public.institution_membership_requests mr
                    JOIN public.institutions i ON i.institution_id = mr.institution_id
                    WHERE mr.user_id = p_target_user_id AND mr.status = 'approved'
                      AND mr.institution_id = v_invitation.institution_id
                      AND mr.organization_id = i.organization_id
                      AND mr.requested_role = v_invitation.role_name
                      AND lower(mr.official_email) = lower(v_invitation.email) FOR SHARE OF mr;
                IF NOT FOUND THEN RETURN NULL; END IF;
            END IF;
        END IF;
    END IF;
    PERFORM 1 FROM public.users WHERE id = p_target_user_id AND status = 'active'
        AND auth_user_id = v_operation.auth_user_id AND lower(email) = lower(v_invitation.email)
        AND (v_invitation.acceptance_user_id IS NULL OR (
            id = v_invitation.acceptance_user_id
            AND auth_user_id = v_invitation.acceptance_auth_user_id
        )) FOR UPDATE;
    IF NOT FOUND THEN RETURN NULL; END IF;
    IF v_admin_invited THEN
        -- The administrator's invitation is the approval: record it like any other.
        INSERT INTO public.institution_membership_requests (
            institution_id, organization_id, user_id, requested_role, official_email, full_name,
            status, decision_reason, decided_by_user_id, decided_at
        )
        SELECT v_invitation.institution_id, i.organization_id, p_target_user_id,
            v_invitation.role_name, lower(btrim(v_invitation.email)), v_invitation.invited_full_name,
            'approved', 'Invited by an administrator', v_invitation.created_by, clock_timestamp()
        FROM public.institutions i WHERE i.institution_id = v_invitation.institution_id;
    END IF;
    IF p_kind = 'platform' THEN
        PERFORM public.phase712_assign_super_admin(v_invitation.email,
            'super_admin_invitation:' || p_invitation_id::text);
    ELSE
        PERFORM public.b05_grant_institution_role(v_invitation.created_by,
            p_target_user_id, v_invitation.institution_id, v_invitation.role_name);
    END IF;
    -- The department chosen at invitation, if it is still active in this institution.
    IF v_admin_invited AND v_invitation.invited_department_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM public.departments
        WHERE department_id = v_invitation.invited_department_id
          AND institution_id = v_invitation.institution_id AND is_active
    ) THEN
        INSERT INTO public.institution_member_departments (institution_id, user_id, department_id, assigned_by)
        VALUES (v_invitation.institution_id, p_target_user_id, v_invitation.invited_department_id,
            v_invitation.created_by)
        ON CONFLICT (institution_id, user_id) DO NOTHING;
    END IF;
    -- Re-check at the final decision too: target/grant locks may have waited.
    v_decision_time := clock_timestamp();
    IF v_invitation.expires_at <= v_decision_time THEN
        RAISE EXCEPTION 'Invitation expired during finalization' USING ERRCODE = '23514';
    END IF;
    PERFORM set_config('b05.acceptance_id', p_acceptance_id::text, true);
    IF p_kind = 'institution' THEN
        UPDATE public.platform_admin_invitations SET status = 'accepted',
            accepted_user_id = p_target_user_id, accepted_at = v_decision_time,
            email_verified_at = v_decision_time WHERE invitation_id = p_invitation_id;
        IF v_invitation.role_name = 'admin' THEN
            INSERT INTO public.platform_institution_audit_log
                (actor_user_id, institution_id, action, target_user_id, result, details)
            VALUES (p_target_user_id, v_invitation.institution_id,
                'institution_admin_invitation_verified', p_target_user_id, 'success',
                jsonb_build_object('email', v_invitation.email, 'verified_by', 'invitation_acceptance')),
                (p_target_user_id, v_invitation.institution_id,
                'institution_admin_invitation_accepted', p_target_user_id, 'success',
                jsonb_build_object('email', v_invitation.email, 'role', v_invitation.role_name));
        END IF;
    ELSE
        UPDATE public.platform_super_admin_invitations SET status = 'accepted',
            accepted_user_id = p_target_user_id, accepted_at = v_decision_time
            WHERE invitation_id = p_invitation_id;
    END IF;
    UPDATE public.b05_invitation_operations SET stage = 'accepted', updated_at = clock_timestamp()
        WHERE acceptance_id = p_acceptance_id;
    RETURN jsonb_build_object('accepted', true);
END;
$$;

REVOKE ALL ON FUNCTION public.b05_finalize_invitation(text, uuid, text, uuid, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_finalize_invitation(text, uuid, text, uuid, uuid) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
