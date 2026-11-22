-- Let people accept Staff/Faculty invitations sent by an administrator.
--
-- 20261127010000 taught b05_finalize_invitation that an administrator's
-- invitation (admin_invited) is the approval and records the approved
-- membership request at acceptance. b05_reserve_invitation, which runs first,
-- still required that approved request to exist beforehand. A new person can
-- never have one (p_existing_user_id is NULL), so every administrator
-- invitation was rejected as "This invitation link is not valid".
--
-- This replaces b05_reserve_invitation from 20261017000000 unchanged except for
-- that one rule. Self-service membership requests keep requiring approval.
BEGIN;

CREATE OR REPLACE FUNCTION public.b05_reserve_invitation(p_kind text, p_invitation_id uuid, p_token_hash text, p_acceptance_id uuid, p_existing_user_id uuid, p_existing_auth_user_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = ''
AS $$
DECLARE
    v_invitation record;
    v_operation public.b05_invitation_operations%ROWTYPE;
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
    -- Invitation first, then operation: every operation RPC uses this order.
    IF NOT FOUND OR v_invitation.token_hash IS DISTINCT FROM p_token_hash THEN RETURN NULL; END IF;
    IF v_invitation.acceptance_id IS NOT NULL THEN
        SELECT * INTO v_operation FROM public.b05_invitation_operations
            WHERE acceptance_id = v_invitation.acceptance_id FOR UPDATE;
        IF NOT FOUND THEN
            RETURN jsonb_build_object('reconciliation_required', true);
        END IF;
        IF v_operation.kind IS DISTINCT FROM p_kind
           OR v_operation.invitation_id IS DISTINCT FROM p_invitation_id THEN RETURN NULL; END IF;
        IF v_invitation.status = 'accepted' THEN
            IF v_operation.stage NOT IN ('accepted','confirmed')
               OR v_operation.user_id IS DISTINCT FROM v_invitation.accepted_user_id THEN RETURN NULL; END IF;
            PERFORM 1 FROM public.users WHERE id = v_operation.user_id
                AND auth_user_id = v_operation.auth_user_id AND status = 'active'
                AND lower(email) = lower(v_invitation.email) FOR SHARE;
            IF NOT FOUND THEN RETURN NULL; END IF;
        END IF;
        IF v_operation.new_account AND p_existing_user_id IS NOT NULL AND (
            p_existing_user_id IS DISTINCT FROM v_operation.user_id OR
            p_existing_auth_user_id IS DISTINCT FROM v_operation.auth_user_id
        ) THEN RETURN NULL; END IF;
        IF NOT v_operation.new_account AND (
            p_existing_user_id IS DISTINCT FROM v_operation.user_id OR
            p_existing_auth_user_id IS DISTINCT FROM v_operation.auth_user_id
        ) THEN RETURN NULL; END IF;
        IF v_invitation.status <> 'accepted' AND v_invitation.expires_at <= clock_timestamp() THEN
            RETURN to_jsonb(v_operation) || jsonb_build_object('reconciliation_required', true);
        END IF;
        IF v_invitation.status NOT IN ('invited', 'accepted') THEN RETURN NULL; END IF;
        RETURN to_jsonb(v_operation) || jsonb_build_object('reserved', true);
    END IF;
    -- clock_timestamp() is evaluated AFTER the row lock, not at transaction start.
    IF NOT FOUND OR v_invitation.status <> 'invited'
       OR v_invitation.token_hash IS DISTINCT FROM p_token_hash
       OR v_invitation.expires_at <= clock_timestamp()
       OR v_invitation.acceptance_id IS NOT NULL THEN RETURN NULL; END IF;
    IF p_kind = 'platform' OR v_invitation.role_name = 'admin' THEN
        PERFORM public.b05_assert_platform_actor(v_invitation.created_by);
    ELSE
        PERFORM public.phase81_assert_institution_admin(
            v_invitation.created_by, v_invitation.institution_id);
    END IF;
    IF p_kind = 'institution' THEN
        PERFORM 1 FROM public.institutions WHERE institution_id = v_invitation.institution_id
            AND status = 'active' AND is_active FOR SHARE;
        IF NOT FOUND THEN RETURN NULL; END IF;
    END IF;
    IF p_existing_user_id IS NOT NULL THEN
        IF p_kind <> 'institution' THEN RETURN NULL; END IF;
        PERFORM 1 FROM public.users WHERE id = p_existing_user_id
            AND auth_user_id = p_existing_auth_user_id AND status = 'active'
            AND lower(email) = lower(v_invitation.email);
        IF NOT FOUND THEN RETURN NULL; END IF;
    ELSIF p_existing_auth_user_id IS NOT NULL OR EXISTS (
        SELECT 1 FROM public.users WHERE lower(email) = lower(v_invitation.email)
    ) THEN
        RETURN NULL;
    END IF;
    IF p_kind = 'institution' AND v_invitation.role_name IN ('staff', 'faculty') THEN
        -- An administrator's invitation is itself the approval: finalization
        -- records the approved request. Only self-service requests need one now.
        -- Nested so the platform record, which has no admin_invited, never reads it.
        IF NOT v_invitation.admin_invited THEN
            PERFORM 1 FROM public.institution_membership_requests mr
                JOIN public.institutions i ON i.institution_id = mr.institution_id
                WHERE mr.user_id = p_existing_user_id AND mr.status = 'approved'
                  AND mr.institution_id = v_invitation.institution_id
                  AND mr.organization_id = i.organization_id
                  AND mr.requested_role = v_invitation.role_name
                  AND lower(mr.official_email) = lower(v_invitation.email) FOR SHARE OF mr;
            IF NOT FOUND THEN RETURN NULL; END IF;
        END IF;
    END IF;
    -- Other authorization locks may have waited beyond the expiry window.
    IF v_invitation.expires_at <= clock_timestamp() THEN RETURN NULL; END IF;
    PERFORM set_config('b05.acceptance_id', p_acceptance_id::text, true);
    IF p_kind = 'institution' THEN
        UPDATE public.platform_admin_invitations SET acceptance_id = p_acceptance_id,
            acceptance_user_id = p_existing_user_id, acceptance_auth_user_id = p_existing_auth_user_id
            WHERE invitation_id = p_invitation_id;
    ELSE
        UPDATE public.platform_super_admin_invitations SET acceptance_id = p_acceptance_id
            WHERE invitation_id = p_invitation_id;
    END IF;
    INSERT INTO public.b05_invitation_operations
        (acceptance_id, kind, invitation_id, stage, user_id, auth_user_id, new_account)
    VALUES (p_acceptance_id, p_kind, p_invitation_id,
        CASE WHEN p_existing_user_id IS NULL THEN 'reserved' ELSE 'user_created' END,
        p_existing_user_id, p_existing_auth_user_id, p_existing_user_id IS NULL)
    RETURNING * INTO v_operation;
    RETURN to_jsonb(v_operation) || jsonb_build_object('reserved', true);
END;
$$;

REVOKE ALL ON FUNCTION public.b05_reserve_invitation(text, uuid, text, uuid, uuid, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_reserve_invitation(text, uuid, text, uuid, uuid, uuid) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
