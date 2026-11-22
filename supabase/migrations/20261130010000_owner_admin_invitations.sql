-- Administrators invited by the institution Owner.
--
-- Owner invitations reuse the invitation table, email outbox and acceptance.
-- They are marked admin_invited; reservation and finalization (20261130020000)
-- then require the sender to still be the Owner instead of a platform super
-- admin. Platform super admin invitations are unchanged.
-- P1401 Owner required, P1202 already a member, P1203 invitation pending.
BEGIN;

ALTER TABLE public.platform_admin_invitations
    DROP CONSTRAINT platform_admin_invitations_admin_invited_role_check,
    ADD CONSTRAINT platform_admin_invitations_admin_invited_role_check
        CHECK (NOT admin_invited OR role_name IN ('staff', 'faculty', 'admin'));

CREATE FUNCTION public.create_admin_invitation(
    p_actor uuid, p_tenant uuid, p_email text, p_full_name text,
    p_token_hash text, p_expires_at timestamptz, p_protected_token text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_email text := lower(btrim(p_email));
    v_invitation public.platform_admin_invitations%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    PERFORM public.institution_owner_assert(p_actor, p_tenant);
    IF v_email IS NULL OR v_email = '' THEN
        RAISE EXCEPTION 'Email required' USING ERRCODE = '22023';
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
    INSERT INTO public.platform_admin_invitations (
        institution_id, email, token_hash, role_name, status, expires_at, created_by,
        email_delivery_status, admin_invited, invited_full_name
    ) VALUES (
        p_tenant, v_email, p_token_hash, 'admin', 'invited', p_expires_at, p_actor,
        'pending', true, NULLIF(btrim(p_full_name), '')
    ) RETURNING * INTO v_invitation;
    INSERT INTO public.email_outbox (aggregate_id, protected_token)
    VALUES (v_invitation.invitation_id, p_protected_token) RETURNING id INTO v_outbox_id;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'institution.admin.invite', 'platform_admin_invitations',
        v_invitation.invitation_id::text, jsonb_build_object('email', v_email, 'expires_at', p_expires_at));
    RETURN (to_jsonb(v_invitation) - 'token_hash') || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;

-- Cancel a pending administrator invitation of this institution.
CREATE FUNCTION public.cancel_admin_invitation(p_actor uuid, p_tenant uuid, p_invitation uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_result jsonb;
BEGIN
    PERFORM public.institution_owner_assert(p_actor, p_tenant);
    PERFORM 1 FROM public.platform_admin_invitations
    WHERE invitation_id = p_invitation AND institution_id = p_tenant AND role_name = 'admin';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invitation not found' USING ERRCODE = 'P0002';
    END IF;
    v_result := public.b05_transition_invitation('institution', p_invitation, 'cancelled', p_actor);
    RETURN jsonb_build_object('invitation_id', p_invitation, 'cancelled', v_result IS NOT NULL);
END;
$$;

-- b05_reserve_invitation from 20261127020000, changed only for Owner invitations.
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
    IF p_kind = 'platform' THEN
        PERFORM public.b05_assert_platform_actor(v_invitation.created_by);
    ELSIF v_invitation.role_name = 'admin' THEN
        -- Sent by the institution's Owner, who must still be its Owner;
        -- otherwise by a platform super admin, as before.
        IF v_invitation.admin_invited THEN
            PERFORM public.institution_owner_assert(v_invitation.created_by, v_invitation.institution_id);
        ELSE
            PERFORM public.b05_assert_platform_actor(v_invitation.created_by);
        END IF;
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

REVOKE ALL ON FUNCTION public.create_admin_invitation(uuid, uuid, text, text, text, timestamptz, text),
    public.cancel_admin_invitation(uuid, uuid, uuid)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_admin_invitation(uuid, uuid, text, text, text, timestamptz, text),
    public.cancel_admin_invitation(uuid, uuid, uuid)
    TO service_role;
REVOKE ALL ON FUNCTION public.b05_reserve_invitation(text, uuid, text, uuid, uuid, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_reserve_invitation(text, uuid, text, uuid, uuid, uuid) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
