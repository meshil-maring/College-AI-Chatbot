-- B05 Stage 1 source patch. NOT EXECUTED. Requires database review/replay
-- before deployment with the backend changes. The containment candidate is
-- separate and unchanged. The legacy phase723 invitation routine is retained.
-- Service-role RPC arguments are supplied only by the verified backend
-- principal; auth.uid() on a service-role connection is not the end user.
-- Repository replay scripts use psql -f without -1; retain a file transaction
-- so creator defaults cannot expose intermediate functions before their REVOKEs.
-- Deployed owner/ACL/ledger state and runner behavior remain UNVERIFIED.
BEGIN;

ALTER TABLE public.platform_admin_invitations
    ADD COLUMN acceptance_id uuid,
    ADD COLUMN acceptance_user_id uuid,
    ADD COLUMN acceptance_auth_user_id uuid;
ALTER TABLE public.platform_super_admin_invitations
    ADD COLUMN acceptance_id uuid,
    ADD COLUMN acceptance_user_id uuid,
    ADD COLUMN acceptance_auth_user_id uuid;

-- No automatic lease release. Provider uncertainty freezes the operation.
CREATE TABLE public.b05_invitation_operations (
    acceptance_id uuid PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('institution', 'platform')),
    invitation_id uuid NOT NULL,
    stage text NOT NULL CHECK (stage IN ('reserved', 'provider_started', 'provider_created', 'user_created', 'accepted', 'confirmed')),
    auth_user_id uuid,
    user_id uuid REFERENCES public.users(id),
    new_account boolean NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (kind, invitation_id)
);
ALTER TABLE public.b05_invitation_operations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.b05_invitation_operations FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.b05_invitation_operations TO service_role;
CREATE FUNCTION public.b05_assert_platform_actor(p_actor_user_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        WHERE u.id = p_actor_user_id AND u.status = 'active'
          AND r.name = 'super_admin' AND r.is_active
          AND ur.scope_type = 'platform' AND ur.scope_id IS NULL
          AND ur.scope_organization_id IS NULL
    ) THEN
        RAISE EXCEPTION 'Active platform administrator required'
            USING ERRCODE = '42501';
    END IF;
END;
$$;

-- Internal grant primitive. Lock the target to serialize grants even when
-- user_roles has no row yet. Never replace another institution's grant.
CREATE FUNCTION public.b05_grant_institution_role(
    p_actor_user_id uuid, p_target_user_id uuid,
    p_institution_id uuid, p_role_name text
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_role_id uuid;
    v_organization_id uuid;
    v_changed boolean;
BEGIN
    IF p_role_name IS NULL OR p_role_name NOT IN ('admin', 'staff', 'faculty') THEN
        RAISE EXCEPTION 'Unsupported institution role' USING ERRCODE = '23514';
    END IF;
    PERFORM 1 FROM public.users WHERE id = p_target_user_id AND status = 'active'
        FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active target account required' USING ERRCODE = '23514';
    END IF;
    SELECT organization_id INTO v_organization_id FROM public.institutions
        WHERE institution_id = p_institution_id AND status = 'active' AND is_active
        FOR SHARE;
    SELECT id INTO v_role_id FROM public.roles
        WHERE name = p_role_name AND is_active FOR SHARE;
    IF v_organization_id IS NULL OR v_role_id IS NULL THEN
        RAISE EXCEPTION 'Active institution and configured role required'
            USING ERRCODE = '23514';
    END IF;
    INSERT INTO public.user_roles
        (user_id, role_id, scope_type, scope_id, scope_organization_id)
    VALUES (p_target_user_id, v_role_id, 'institution', p_institution_id, v_organization_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;
    v_changed := FOUND;
    IF NOT EXISTS (
        SELECT 1 FROM public.user_roles WHERE user_id = p_target_user_id
          AND role_id = v_role_id AND scope_type = 'institution'
          AND scope_id = p_institution_id AND scope_organization_id = v_organization_id
    ) THEN
        RAISE EXCEPTION 'Existing role belongs to another scope' USING ERRCODE = '42501';
    END IF;
    IF v_changed THEN
        INSERT INTO public.admin_audit_log
            (actor_user_id, institution_id, action, table_name, record_id, record_data, status)
        VALUES (p_actor_user_id, p_institution_id, 'role.assignment', 'user_roles',
            p_target_user_id::text,
            jsonb_build_object('role', p_role_name, 'institution_id', p_institution_id), 'success');
    END IF;
    RETURN v_changed;
END;
$$;

-- Legacy four-argument role assignment remains a HARD BLOCKER pending consumer decision.
CREATE FUNCTION public.phase81_assign_institution_role_audited(
    p_actor_user_id uuid, p_target_user_id uuid, p_institution_id uuid,
    p_role_name text, p_actor_auth_user_id uuid
) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.users WHERE id = p_actor_user_id
        AND auth_user_id = p_actor_auth_user_id AND status = 'active') THEN
        RAISE EXCEPTION 'Verified actor identity mismatch' USING ERRCODE = '42501';
    END IF;
    IF p_role_name = 'admin' THEN
        PERFORM public.b05_assert_platform_actor(p_actor_user_id);
    ELSIF p_role_name IN ('staff', 'faculty') THEN
        IF EXISTS (
            SELECT 1 FROM public.user_roles ur JOIN public.roles r ON r.id = ur.role_id
            WHERE ur.user_id = p_actor_user_id AND r.name = 'super_admin' AND r.is_active
              AND ur.scope_type = 'platform' AND ur.scope_id IS NULL
              AND ur.scope_organization_id IS NULL
        ) THEN
            PERFORM public.b05_assert_platform_actor(p_actor_user_id);
        ELSE
            PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
        END IF;
        PERFORM 1 FROM public.institution_membership_requests mr
            JOIN public.institutions i ON i.institution_id = mr.institution_id
            JOIN public.users u ON u.id = mr.user_id
            WHERE mr.user_id = p_target_user_id AND mr.institution_id = p_institution_id
              AND mr.organization_id = i.organization_id AND mr.requested_role = p_role_name
              AND mr.status = 'approved' AND lower(mr.official_email) = lower(u.email)
            FOR SHARE OF mr;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Approved matching membership required' USING ERRCODE = '42501';
        END IF;
    ELSE
        RAISE EXCEPTION 'Unsupported institution role' USING ERRCODE = '23514';
    END IF;
    RETURN public.b05_grant_institution_role(
        p_actor_user_id, p_target_user_id, p_institution_id, p_role_name);
END;
$$;

-- Covers direct UPDATEs and all existing SQL writers, including resend,
-- cancel, expiry, and creation housekeeping. Updates hold the same row lock
-- as reserve/finalize. The local setting routes trusted internal writes;
-- it is not an end-user identity assertion or a substitute for service-role ACLs.
CREATE FUNCTION public.b05_guard_invitation_acceptance()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
DECLARE
    v_operation text := current_setting('b05.acceptance_id', true);
BEGIN
    IF NEW.email IS DISTINCT FROM OLD.email
       OR NEW.created_by IS DISTINCT FROM OLD.created_by
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'Invitation identity is immutable' USING ERRCODE = '23514';
    END IF;
    IF OLD.status <> 'invited' AND (
        NEW.status IS DISTINCT FROM OLD.status
        OR NEW.token_hash IS DISTINCT FROM OLD.token_hash
        OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
        OR NEW.accepted_user_id IS DISTINCT FROM OLD.accepted_user_id
        OR NEW.accepted_at IS DISTINCT FROM OLD.accepted_at
    ) THEN
        RAISE EXCEPTION 'Invitation is terminal' USING ERRCODE = '23514';
    END IF;
    IF OLD.acceptance_id IS NOT NULL AND (
        NEW.token_hash IS DISTINCT FROM OLD.token_hash
        OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
        OR NEW.acceptance_id IS DISTINCT FROM OLD.acceptance_id
        OR NEW.acceptance_user_id IS DISTINCT FROM OLD.acceptance_user_id
        OR NEW.acceptance_auth_user_id IS DISTINCT FROM OLD.acceptance_auth_user_id
        OR (NEW.status IS DISTINCT FROM OLD.status AND
            (NEW.status <> 'accepted' OR v_operation IS DISTINCT FROM OLD.acceptance_id::text)
            AND NOT (NEW.status IN ('cancelled','expired')
                AND current_setting('b05.recovery_id',true) IS NOT DISTINCT FROM OLD.acceptance_id::text))
    ) THEN
        RAISE EXCEPTION 'Invitation acceptance requires reconciliation' USING ERRCODE = '55P03';
    END IF;
    IF NEW.acceptance_id IS DISTINCT FROM OLD.acceptance_id AND
        (OLD.status <> 'invited' OR NEW.acceptance_id IS NULL
         OR v_operation IS DISTINCT FROM NEW.acceptance_id::text) THEN
        RAISE EXCEPTION 'Reservation RPC required' USING ERRCODE = '42501';
    END IF;
    IF NEW.status = 'accepted' AND OLD.status <> 'accepted' AND (
        OLD.acceptance_id IS NULL OR v_operation IS DISTINCT FROM OLD.acceptance_id::text
    ) THEN
        RAISE EXCEPTION 'Finalization RPC required' USING ERRCODE = '42501';
    END IF;
    IF (NEW.token_hash IS DISTINCT FROM OLD.token_hash
        OR NEW.expires_at IS DISTINCT FROM OLD.expires_at)
       AND OLD.expires_at <= clock_timestamp() THEN
        RAISE EXCEPTION 'Expired invitation cannot rotate' USING ERRCODE = '23514';
    END IF;
    IF NEW.status = 'expired' AND OLD.status = 'invited' AND OLD.expires_at > clock_timestamp() THEN
        RAISE EXCEPTION 'Invitation has not expired' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_b05_invitation_acceptance BEFORE UPDATE ON public.platform_admin_invitations
    FOR EACH ROW EXECUTE FUNCTION public.b05_guard_invitation_acceptance();
CREATE TRIGGER trg_b05_super_invitation_acceptance BEFORE UPDATE ON public.platform_super_admin_invitations
    FOR EACH ROW EXECUTE FUNCTION public.b05_guard_invitation_acceptance();

CREATE FUNCTION public.b05_reserve_invitation(
    p_kind text, p_invitation_id uuid, p_token_hash text, p_acceptance_id uuid,
    p_existing_user_id uuid, p_existing_auth_user_id uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
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
        PERFORM 1 FROM public.institution_membership_requests mr
            JOIN public.institutions i ON i.institution_id = mr.institution_id
            WHERE mr.user_id = p_existing_user_id AND mr.status = 'approved'
              AND mr.institution_id = v_invitation.institution_id
              AND mr.organization_id = i.organization_id
              AND mr.requested_role = v_invitation.role_name
              AND lower(mr.official_email) = lower(v_invitation.email) FOR SHARE OF mr;
        IF NOT FOUND THEN RETURN NULL; END IF;
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

CREATE FUNCTION public.b05_finalize_invitation(
    p_kind text, p_invitation_id uuid, p_token_hash text,
    p_acceptance_id uuid, p_target_user_id uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_invitation record;
    v_decision_time timestamptz;
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
        IF v_invitation.role_name = 'admin' THEN
            PERFORM public.b05_assert_platform_actor(v_invitation.created_by);
        ELSE
            PERFORM public.phase81_assert_institution_admin(
                v_invitation.created_by, v_invitation.institution_id);
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
    PERFORM 1 FROM public.users WHERE id = p_target_user_id AND status = 'active'
        AND auth_user_id = v_operation.auth_user_id AND lower(email) = lower(v_invitation.email)
        AND (v_invitation.acceptance_user_id IS NULL OR (
            id = v_invitation.acceptance_user_id
            AND auth_user_id = v_invitation.acceptance_auth_user_id
        )) FOR UPDATE;
    IF NOT FOUND THEN RETURN NULL; END IF;
    IF p_kind = 'platform' THEN
        PERFORM public.phase712_assign_super_admin(v_invitation.email,
            'super_admin_invitation:' || p_invitation_id::text);
    ELSE
        PERFORM public.b05_grant_institution_role(v_invitation.created_by,
            p_target_user_id, v_invitation.institution_id, v_invitation.role_name);
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

REVOKE ALL ON FUNCTION public.b05_assert_platform_actor(uuid) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.b05_grant_institution_role(uuid, uuid, uuid, text) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.b05_guard_invitation_acceptance() FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.b05_reserve_invitation(text, uuid, text, uuid, uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.b05_finalize_invitation(text, uuid, text, uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.phase81_assign_institution_role_audited(uuid, uuid, uuid, text, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_reserve_invitation(text, uuid, text, uuid, uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.b05_finalize_invitation(text, uuid, text, uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.phase81_assign_institution_role_audited(uuid, uuid, uuid, text, uuid) TO service_role;

-- Resend takes the same row lock and loses to a reserved acceptance.
CREATE OR REPLACE FUNCTION "public"."phase717_rotate_invitation_with_outbox"(
    "p_invitation_id" uuid,
    "p_token_hash" text,
    "p_expires_at" timestamp with time zone,
    "p_expected_updated_at" timestamp with time zone,
    "p_protected_token" text,
    "p_lock_seconds" integer
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_invitation "public"."platform_admin_invitations"%ROWTYPE;
    v_outbox_id uuid;
BEGIN
    SELECT * INTO v_invitation
    FROM "public"."platform_admin_invitations"
    WHERE "invitation_id" = p_invitation_id
    FOR UPDATE;

    IF NOT FOUND OR v_invitation."status" <> 'invited'::text
       OR v_invitation."expires_at" <= clock_timestamp()
       OR v_invitation."acceptance_id" IS NOT NULL
       OR (p_expected_updated_at IS NOT NULL
           AND v_invitation."updated_at" IS DISTINCT FROM p_expected_updated_at) THEN
        RETURN NULL;
    END IF;

    -- Recover an abandoned lease before deciding whether resend can proceed.
    UPDATE "public"."email_delivery_attempts" AS a
    SET "result" = 'retry'::text, "completed_at" = now(),
        "failure_category" = 'WORKER_LEASE_EXPIRED'::text
    FROM "public"."email_outbox" AS o
    WHERE a."outbox_id" = o."id"
      AND a."attempt_number" = o."attempt_count"
      AND a."result" = 'processing'::text
      AND o."aggregate_id" = p_invitation_id
      AND o."status" = 'processing'::text
      AND o."locked_at" <= now() - make_interval(secs => p_lock_seconds);

    UPDATE "public"."email_outbox"
    SET "status" = 'pending'::text, "locked_at" = NULL,
        "available_at" = now(), "updated_at" = now(),
        "last_error_category" = 'WORKER_LEASE_EXPIRED'::text
    WHERE "aggregate_id" = p_invitation_id
      AND "status" = 'processing'::text
      AND "locked_at" <= now() - make_interval(secs => p_lock_seconds);

    -- A non-stale worker may already be inside provider I/O. Refuse the resend
    -- rather than rotate the token underneath that delivery.
    IF EXISTS (
        SELECT 1 FROM "public"."email_outbox"
        WHERE "aggregate_id" = p_invitation_id
          AND "status" = 'processing'::text
    ) THEN
        RETURN NULL;
    END IF;

    UPDATE "public"."email_outbox"
    SET "status" = 'cancelled'::text, "locked_at" = NULL,
        "protected_token" = NULL, "updated_at" = now(),
        "last_error_category" = 'INVITATION_SUPERSEDED'::text
    WHERE "aggregate_id" = p_invitation_id
      AND "status" = 'pending'::text;

    UPDATE "public"."platform_admin_invitations"
    SET "token_hash" = p_token_hash, "expires_at" = p_expires_at,
        "resend_count" = "resend_count" + 1,
        "email_delivery_status" = 'pending'::text,
        "email_delivery_at" = NULL, "updated_at" = now()
    WHERE "invitation_id" = p_invitation_id
    RETURNING * INTO v_invitation;

    INSERT INTO "public"."email_outbox" ("aggregate_id", "protected_token")
    VALUES (p_invitation_id, p_protected_token)
    RETURNING "id" INTO v_outbox_id;

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;


ALTER TABLE public.admin_audit_log ADD COLUMN decision_key text;
CREATE UNIQUE INDEX b05_decision_audit_key ON public.admin_audit_log(decision_key);

-- Approval/grant commits before provider confirmation, including repeat decisions.
CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_and_grant_role"(
    "p_request_id" uuid,
    "p_institution_id" uuid,
    "p_decided_by" uuid,
    "p_reason" text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    "v_request" "public"."institution_membership_requests"%ROWTYPE;
    "v_role_id" uuid;
BEGIN
    IF COALESCE("auth"."role"(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Phase 7.24: service role required'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    PERFORM "public"."phase81_assert_institution_admin"(
        "p_decided_by", "p_institution_id"
    );

    SELECT * INTO "v_request"
      FROM "public"."institution_membership_requests"
     WHERE "request_id" = "p_request_id"
       AND "institution_id" = "p_institution_id"
     FOR UPDATE;

    IF NOT FOUND THEN
        RETURN "jsonb_build_object"('not_found', true);
    END IF;
    IF "v_request"."status" NOT IN ('pending'::text, 'approved'::text) THEN
        RETURN "jsonb_build_object"('conflict', true);
    END IF;
    IF "v_request"."requested_role" NOT IN ('staff', 'faculty') THEN
        RETURN "jsonb_build_object"('invalid_role', true);
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM "public"."institutions" AS "institution"
          JOIN "public"."users" AS "applicant"
            ON "applicant"."id" = "v_request"."user_id"
         WHERE "institution"."institution_id" = "p_institution_id"
           AND "institution"."organization_id" = "v_request"."organization_id"
           AND "institution"."status" = 'active'::text
           AND "institution"."is_active" = true
           AND "lower"("applicant"."email") = "lower"("v_request"."official_email")
           AND "applicant"."status" = 'active'::text
    ) THEN
        RETURN "jsonb_build_object"('invalid_state', true);
    END IF;


    SELECT "id" INTO "v_role_id"
      FROM "public"."roles"
     WHERE "name" = "v_request"."requested_role"
       AND "is_active" = true;
    IF "v_role_id" IS NULL THEN
        RETURN "jsonb_build_object"('role_not_configured', true);
    END IF;

    IF "v_request"."status" = 'approved' THEN
        PERFORM 1 FROM public.user_roles
            WHERE user_id = "v_request"."user_id" AND role_id = "v_role_id"
              AND scope_type = 'institution' AND scope_id = "p_institution_id"
              AND scope_organization_id = "v_request"."organization_id";
        IF NOT FOUND THEN
            RETURN jsonb_build_object('invalid_state', true);
        END IF;
        INSERT INTO public.admin_audit_log
            (actor_user_id, institution_id, action, table_name, record_id, record_data, status, decision_key)
        VALUES (v_request.decided_by_user_id, p_institution_id, 'membership_request_approved',
            'institution_membership_requests', p_request_id::text,
            jsonb_build_object('role', v_request.requested_role, 'status', 'approved', 'access_granted', true),
            'success', 'membership:' || p_request_id::text)
        ON CONFLICT (decision_key) DO NOTHING;
        RETURN jsonb_build_object('already_applied', true, 'role_granted', true, 'audit_persisted', true);
    END IF;
    PERFORM public.b05_grant_institution_role("p_decided_by", "v_request"."user_id",
        "p_institution_id", "v_request"."requested_role");

    UPDATE "public"."institution_membership_requests"
       SET "status" = 'approved'::text,
           "decided_by_user_id" = "p_decided_by",
           "decided_at" = "now"(),
           "decision_reason" = "p_reason",
           "updated_at" = "now"()
     WHERE "request_id" = "p_request_id";

    INSERT INTO public.admin_audit_log
        (actor_user_id, institution_id, action, table_name, record_id, record_data, status, decision_key)
    VALUES (p_decided_by, p_institution_id, 'membership_request_approved',
        'institution_membership_requests', p_request_id::text,
        jsonb_build_object('role', v_request.requested_role, 'status', 'approved', 'access_granted', true),
        'success', 'membership:' || p_request_id::text);
    RETURN "jsonb_build_object"(
        'audit_persisted', true,
        'already_applied', false,
        'role_granted', true
    );
END;
$$;

-- Private operation state is advanced only through this service entry point.
-- Every path locks invitation before operation; no automatic reservation release.
CREATE FUNCTION public.b05_advance_invitation_operation(
    p_acceptance_id uuid, p_expected_stage text, p_stage text,
    p_auth_user_id uuid, p_user_id uuid, p_first_name text, p_last_name text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_op public.b05_invitation_operations%ROWTYPE;
    v_user public.users%ROWTYPE;
    v_email text;
    v_expiry timestamptz;
    v_status text;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;
    SELECT * INTO v_op FROM public.b05_invitation_operations WHERE acceptance_id = p_acceptance_id;
    IF NOT FOUND THEN RETURN NULL; END IF;
    IF v_op.kind = 'institution' THEN
        SELECT email, expires_at, status INTO v_email, v_expiry, v_status
            FROM public.platform_admin_invitations WHERE invitation_id = v_op.invitation_id FOR UPDATE;
    ELSE
        SELECT email, expires_at, status INTO v_email, v_expiry, v_status
            FROM public.platform_super_admin_invitations WHERE invitation_id = v_op.invitation_id FOR UPDATE;
    END IF;
    IF NOT FOUND THEN RETURN NULL; END IF;
    SELECT * INTO v_op FROM public.b05_invitation_operations WHERE acceptance_id = p_acceptance_id FOR UPDATE;
    IF v_op.stage <> p_expected_stage THEN RETURN NULL; END IF;
    IF p_stage <> 'confirmed' AND (v_status <> 'invited'
        OR (p_stage <> 'provider_created' AND v_expiry <= clock_timestamp())) THEN
        RETURN NULL;
    END IF;
    IF p_expected_stage = 'reserved' AND p_stage = 'provider_started' AND v_op.new_account THEN
        NULL;
    ELSIF p_expected_stage = 'provider_started' AND p_stage = 'provider_created'
          AND p_auth_user_id IS NOT NULL AND v_op.new_account THEN
        v_op.auth_user_id := p_auth_user_id;
    ELSIF p_expected_stage = 'provider_created' AND p_stage = 'user_created'
          AND p_auth_user_id = v_op.auth_user_id AND v_op.new_account THEN
        SELECT * INTO v_user FROM public.users WHERE auth_user_id = v_op.auth_user_id FOR UPDATE;
        IF NOT FOUND THEN
            INSERT INTO public.users (auth_user_id, email, first_name, last_name, status)
            VALUES (v_op.auth_user_id, v_email, COALESCE(NULLIF(p_first_name,''),'Invited'),
                COALESCE(NULLIF(p_last_name,''),'User'), 'active') RETURNING * INTO v_user;
        END IF;
        IF lower(v_user.email) <> lower(v_email) OR v_user.status <> 'active' THEN
            RAISE EXCEPTION 'Recorded identity mismatch' USING ERRCODE = '23514';
        END IF;
        v_op.user_id := v_user.id;
    ELSIF p_expected_stage = 'accepted' AND p_stage = 'confirmed' AND v_status = 'accepted' THEN
        NULL;
    ELSE
        RAISE EXCEPTION 'Invalid operation transition' USING ERRCODE = '23514';
    END IF;
    UPDATE public.b05_invitation_operations SET stage = p_stage,
        auth_user_id = v_op.auth_user_id, user_id = v_op.user_id, updated_at = clock_timestamp()
        WHERE acceptance_id = p_acceptance_id RETURNING * INTO v_op;
    RETURN to_jsonb(v_op);
END;
$$;
REVOKE ALL ON FUNCTION public.b05_advance_invitation_operation(uuid,text,text,uuid,uuid,text,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_advance_invitation_operation(uuid,text,text,uuid,uuid,text,text) TO service_role;

-- Separate student command. Existing API contract: live institution admin/staff,
-- verified Auth linkage, active tenant. No student role added to invite allowlists.
CREATE FUNCTION public.b05_approve_student(
    p_student_id uuid, p_institution_id uuid, p_actor_user_id uuid, p_actor_auth_user_id uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_student public.students%ROWTYPE;
    v_org uuid;
    v_role uuid;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' OR NOT EXISTS (
        SELECT 1 FROM public.users u JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.institutions i ON i.institution_id = p_institution_id
        WHERE u.id = p_actor_user_id AND u.auth_user_id = p_actor_auth_user_id AND u.status = 'active'
          AND r.name IN ('admin','staff') AND r.is_active
          AND ur.scope_type = 'institution' AND ur.scope_id = p_institution_id
          AND ur.scope_organization_id = i.organization_id AND i.status = 'active' AND i.is_active
    ) THEN RAISE EXCEPTION 'Authorized student approver required' USING ERRCODE = '42501'; END IF;
    SELECT * INTO v_student FROM public.students
        WHERE student_id = p_student_id AND institution_id = p_institution_id FOR UPDATE;
    IF NOT FOUND THEN RETURN jsonb_build_object('not_found',true); END IF;
    IF v_student.approval_status NOT IN ('pending','approved') THEN
        RETURN jsonb_build_object('conflict',true);
    END IF;
    SELECT organization_id INTO v_org FROM public.institutions
        WHERE institution_id = p_institution_id AND status = 'active' AND is_active FOR SHARE;
    SELECT id INTO v_role FROM public.roles WHERE name = 'student' AND is_active FOR SHARE;
    PERFORM 1 FROM public.users WHERE id = v_student.user_id AND status = 'active'
        AND auth_user_id IS NOT NULL AND lower(email) = lower(v_student.email) FOR UPDATE;
    IF NOT FOUND OR v_role IS NULL OR v_org IS NULL THEN
        RAISE EXCEPTION 'Student provisioning prerequisites missing' USING ERRCODE = '23514';
    END IF;
    INSERT INTO public.user_roles (user_id,role_id,scope_type,scope_id,scope_organization_id)
        VALUES (v_student.user_id,v_role,'institution',p_institution_id,v_org)
        ON CONFLICT (user_id,role_id) DO NOTHING;
    IF NOT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = v_student.user_id
        AND role_id = v_role AND scope_type = 'institution' AND scope_id = p_institution_id
        AND scope_organization_id = v_org) THEN
        RAISE EXCEPTION 'Student role scope conflict' USING ERRCODE = '42501';
    END IF;
    UPDATE public.students SET approval_status = 'approved' WHERE student_id = p_student_id RETURNING * INTO v_student;
    INSERT INTO public.admin_audit_log
        (actor_user_id,institution_id,action,table_name,record_id,record_data,status,decision_key)
        VALUES (p_actor_user_id,p_institution_id,'student.approve','students',p_student_id::text,
            jsonb_build_object('approval_status','approved','role_granted',true),'success','student:' || p_student_id::text)
        ON CONFLICT (decision_key) DO NOTHING;
    RETURN jsonb_build_object('student',to_jsonb(v_student),'role_granted',true,'audit_persisted',true);
END;
$$;
REVOKE ALL ON FUNCTION public.b05_approve_student(uuid,uuid,uuid,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_approve_student(uuid,uuid,uuid,uuid) TO service_role;

CREATE FUNCTION public.b05_reject_membership(
    p_request_id uuid, p_institution_id uuid, p_decided_by uuid, p_reason text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_request public.institution_membership_requests%ROWTYPE;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;
    PERFORM public.phase81_assert_institution_admin(p_decided_by,p_institution_id);
    SELECT * INTO v_request FROM public.institution_membership_requests
        WHERE request_id = p_request_id AND institution_id = p_institution_id FOR UPDATE;
    IF NOT FOUND OR v_request.status NOT IN ('pending','rejected') THEN RETURN NULL; END IF;
    IF v_request.status = 'pending' THEN
        UPDATE public.institution_membership_requests SET status = 'rejected',
            decided_by_user_id = p_decided_by, decided_at = clock_timestamp(), decision_reason = p_reason
            WHERE request_id = p_request_id RETURNING * INTO v_request;
    END IF;
    INSERT INTO public.admin_audit_log
        (actor_user_id,institution_id,action,table_name,record_id,record_data,status,decision_key)
        VALUES (v_request.decided_by_user_id,p_institution_id,'membership_request_rejected',
            'institution_membership_requests',p_request_id::text,
            jsonb_build_object('role',v_request.requested_role,'status','rejected','access_granted',false),
            'success','membership:' || p_request_id::text)
        ON CONFLICT (decision_key) DO NOTHING;
    RETURN to_jsonb(v_request) || jsonb_build_object('audit_persisted',true);
END;
$$;
REVOKE ALL ON FUNCTION public.b05_reject_membership(uuid,uuid,uuid,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_reject_membership(uuid,uuid,uuid,text) TO service_role;

-- Stage 1.4: preserve legacy authorization; the five-argument assignment still
-- decides whether approval is allowed. In particular, organization-admin
-- disposition remains open. A denied grant now rolls back the decision too.
CREATE FUNCTION public.b05_decide_legacy_membership(
    p_request_id uuid, p_status text, p_actor_user_id uuid,
    p_actor_auth_user_id uuid, p_reason text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_req public.institution_membership_requests%ROWTYPE;
    v_repeat boolean;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' OR p_status IS NULL
       OR p_status NOT IN ('approved','rejected') THEN
        RAISE EXCEPTION 'Invalid trusted decision' USING ERRCODE = '42501';
    END IF;
    -- The legacy backend retains its institution/org/platform scope checks.
    SELECT * INTO v_req FROM public.institution_membership_requests
        WHERE request_id = p_request_id FOR UPDATE;
    IF NOT FOUND THEN RETURN NULL; END IF;
    v_repeat := v_req.status = p_status;
    IF v_req.status <> 'pending' AND (NOT v_repeat
       OR v_req.decided_by_user_id IS DISTINCT FROM p_actor_user_id
       OR v_req.decision_reason IS DISTINCT FROM p_reason) THEN RETURN NULL; END IF;
    IF NOT v_repeat THEN
        UPDATE public.institution_membership_requests SET status = p_status,
            decided_by_user_id = p_actor_user_id, decision_reason = p_reason,
            decided_at = clock_timestamp() WHERE request_id = p_request_id;
    END IF;
    IF p_status = 'approved' THEN
        PERFORM public.phase81_assign_institution_role_audited(
            p_actor_user_id, v_req.user_id, v_req.institution_id,
            v_req.requested_role, p_actor_auth_user_id);
    END IF;
    -- Rejection grants nothing and revokes nothing. Retry repairs an absent
    -- audit without overwriting the original decision or timestamp.
    INSERT INTO public.admin_audit_log
        (actor_user_id,institution_id,action,table_name,record_id,record_data,status,decision_key)
    VALUES (p_actor_user_id,v_req.institution_id,'membership.' || p_status,
        'institution_membership_requests',p_request_id::text,
        jsonb_build_object('status',p_status,'reason',p_reason),'success',
        'membership:' || p_request_id::text) ON CONFLICT (decision_key) DO NOTHING;
    RETURN jsonb_build_object('decided',true,'already_applied',v_repeat,'audit_persisted',true);
END;
$$;
REVOKE ALL ON FUNCTION public.b05_decide_legacy_membership(uuid,text,uuid,uuid,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_decide_legacy_membership(uuid,text,uuid,uuid,text) TO service_role;

-- Authoritative immutable lifecycle audit, including platform invitations for
-- which the institution ledger has no applicable institution FK. No token,
-- digest, credential or inferred human identity is stored here.
CREATE TABLE public.b05_invitation_lifecycle_audit (
    kind text NOT NULL CHECK (kind IN ('institution','platform')),
    invitation_id uuid NOT NULL,
    status text NOT NULL CHECK (status IN ('cancelled','expired')),
    actor_user_id uuid REFERENCES public.users(id) ON DELETE RESTRICT,
    attribution text NOT NULL CHECK (attribution IN ('backend_actor','repair_actor','issuer_for_expiry','unrecorded_initiator')),
    repaired boolean NOT NULL,
    performed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (kind,invitation_id,status)
);
ALTER TABLE public.b05_invitation_lifecycle_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.b05_invitation_lifecycle_audit FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.b05_invitation_lifecycle_audit TO service_role;

CREATE FUNCTION public.b05_record_invitation_lifecycle(p_kind text, p_id uuid, p_actor uuid, p_repair boolean)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_inv record; v_attribution text; v_actor uuid;
BEGIN
    IF p_kind = 'institution' THEN
        SELECT * INTO v_inv FROM public.platform_admin_invitations WHERE invitation_id = p_id;
    ELSIF p_kind = 'platform' THEN
        SELECT i.*, NULL::uuid AS institution_id, 'super_admin'::text AS role_name
            INTO v_inv FROM public.platform_super_admin_invitations i WHERE invitation_id = p_id;
    ELSE RAISE EXCEPTION 'Invalid kind'; END IF;
    IF NOT FOUND OR v_inv.status NOT IN ('cancelled','expired') THEN RETURN; END IF;
    v_actor := p_actor;
    v_attribution := CASE WHEN p_actor IS NULL THEN 'unrecorded_initiator'
        WHEN p_repair THEN 'repair_actor' ELSE 'backend_actor' END;
    IF v_inv.status = 'expired' AND p_actor IS NULL THEN
        v_actor := v_inv.created_by; v_attribution := 'issuer_for_expiry';
    END IF;
    INSERT INTO public.b05_invitation_lifecycle_audit(kind,invitation_id,status,actor_user_id,attribution,repaired)
        VALUES (p_kind,p_id,v_inv.status,v_actor,v_attribution,p_repair) ON CONFLICT DO NOTHING;
    IF NOT FOUND THEN RETURN; END IF;
    -- Historical projection rows contain no reliable invitation correlation.
    -- Repair the authoritative event explicitly, without guessing which old
    -- projection is missing or attributing the original decision to the retry.
    IF p_repair THEN RETURN; END IF;
    -- Preserve the established institution-admin audit projection, atomically.
    IF p_kind = 'institution' AND v_inv.role_name = 'admin' THEN
        INSERT INTO public.platform_institution_audit_log(actor_user_id,institution_id,action,result,details)
        VALUES (COALESCE(v_actor,v_inv.created_by),v_inv.institution_id,
            'institution_admin_invitation_' || v_inv.status,'success',
            jsonb_build_object('email',v_inv.email,'invitation_id',p_id,'attribution',v_attribution));
    END IF;
END;
$$;
REVOKE ALL ON FUNCTION public.b05_record_invitation_lifecycle(text,uuid,uuid,boolean) FROM PUBLIC, anon, authenticated, service_role;

CREATE FUNCTION public.b05_audit_invitation_transition()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF NEW.status IN ('cancelled','expired') THEN
        PERFORM public.b05_record_invitation_lifecycle(
            CASE WHEN TG_TABLE_NAME = 'platform_admin_invitations' THEN 'institution' ELSE 'platform' END,
            NEW.invitation_id, NULLIF(current_setting('b05.lifecycle_actor',true),'')::uuid,
            OLD.status = NEW.status);
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.b05_audit_invitation_transition() FROM PUBLIC, anon, authenticated, service_role;
CREATE TRIGGER trg_b05_lifecycle_audit AFTER UPDATE OF status ON public.platform_admin_invitations
    FOR EACH ROW EXECUTE FUNCTION public.b05_audit_invitation_transition();
CREATE TRIGGER trg_b05_platform_lifecycle_audit AFTER UPDATE OF status ON public.platform_super_admin_invitations
    FOR EACH ROW EXECUTE FUNCTION public.b05_audit_invitation_transition();
CREATE TRIGGER trg_b05_lifecycle_immutable BEFORE UPDATE OR DELETE ON public.b05_invitation_lifecycle_audit
    FOR EACH ROW EXECUTE FUNCTION public.phase81_prevent_audit_mutation();
CREATE TRIGGER trg_b05_lifecycle_no_truncate BEFORE TRUNCATE ON public.b05_invitation_lifecycle_audit
    FOR EACH STATEMENT EXECUTE FUNCTION public.phase81_prevent_audit_mutation();

CREATE FUNCTION public.b05_transition_invitation(p_kind text,p_id uuid,p_status text,p_actor uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_inv record; v_op public.b05_invitation_operations%ROWTYPE; v_repeat boolean;
BEGIN
    IF COALESCE(auth.role(),'') <> 'service_role' OR p_status IS NULL
       OR p_status NOT IN ('cancelled','expired') THEN
        RAISE EXCEPTION 'Trusted lifecycle command required' USING ERRCODE = '42501';
    END IF;
    IF p_kind = 'institution' THEN
        SELECT * INTO v_inv FROM public.platform_admin_invitations WHERE invitation_id = p_id FOR UPDATE;
    ELSIF p_kind = 'platform' THEN
        SELECT * INTO v_inv FROM public.platform_super_admin_invitations WHERE invitation_id = p_id FOR UPDATE;
    ELSE RETURN NULL; END IF;
    IF NOT FOUND THEN RETURN NULL; END IF;
    v_repeat := v_inv.status = p_status;
    IF NOT v_repeat THEN
        IF v_inv.status <> 'invited' THEN RETURN NULL; END IF;
        IF p_status = 'expired' AND v_inv.expires_at > clock_timestamp() THEN RETURN NULL; END IF;
        IF v_inv.acceptance_id IS NOT NULL THEN
            SELECT * INTO v_op FROM public.b05_invitation_operations
                WHERE acceptance_id = v_inv.acceptance_id FOR UPDATE;
            IF NOT FOUND OR v_op.stage <> 'reserved' OR NOT v_op.new_account
               OR v_op.kind IS DISTINCT FROM p_kind OR v_op.invitation_id IS DISTINCT FROM p_id THEN RETURN NULL; END IF;
        END IF;
        PERFORM set_config('b05.recovery_id',COALESCE(v_inv.acceptance_id::text,''),true);
        PERFORM set_config('b05.lifecycle_actor',COALESCE(p_actor::text,''),true);
        IF p_kind = 'institution' THEN
            UPDATE public.platform_admin_invitations SET status = p_status,
                cancelled_at = CASE WHEN p_status = 'cancelled' THEN clock_timestamp() ELSE cancelled_at END
                WHERE invitation_id = p_id RETURNING * INTO v_inv;
        ELSE
            UPDATE public.platform_super_admin_invitations SET status = p_status,
                cancelled_at = CASE WHEN p_status = 'cancelled' THEN clock_timestamp() ELSE cancelled_at END
                WHERE invitation_id = p_id RETURNING * INTO v_inv;
        END IF;
    END IF;
    PERFORM public.b05_record_invitation_lifecycle(p_kind,p_id,p_actor,v_repeat);
    PERFORM set_config('b05.lifecycle_actor','',true);
    RETURN jsonb_build_object('closed',true,'already_applied',v_repeat,'audit_persisted',true,
        'invitation',to_jsonb(v_inv) - 'token_hash');
END;
$$;
REVOKE ALL ON FUNCTION public.b05_transition_invitation(text,uuid,text,uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_transition_invitation(text,uuid,text,uuid) TO service_role;

-- Retain the existing two-argument RPC identity and its boolean contract.
CREATE FUNCTION public.b05_close_unstarted_invitation(p_invitation_id uuid,p_status text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    RETURN COALESCE((public.b05_transition_invitation('institution',p_invitation_id,p_status,NULL)->>'closed')::boolean,false);
END;
$$;
REVOKE ALL ON FUNCTION public.b05_close_unstarted_invitation(uuid,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_close_unstarted_invitation(uuid,text) TO service_role;

-- Recovery is a capability for the recorded NEW account only. It cannot
-- reserve/create accounts, grant another membership or update a password.
CREATE FUNCTION public.b05_recover_accepted_invitation(p_kind text,p_id uuid,p_digest text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_inv record; v_op public.b05_invitation_operations%ROWTYPE;
BEGIN
    IF COALESCE(auth.role(),'') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501'; END IF;
    IF p_kind = 'institution' THEN
        SELECT * INTO v_inv FROM public.platform_admin_invitations WHERE invitation_id = p_id FOR UPDATE;
    ELSIF p_kind = 'platform' THEN
        SELECT * INTO v_inv FROM public.platform_super_admin_invitations WHERE invitation_id = p_id FOR UPDATE;
    ELSE RETURN NULL; END IF;
    IF NOT FOUND OR v_inv.status <> 'accepted' OR p_digest IS NULL
       OR v_inv.token_hash IS DISTINCT FROM p_digest OR v_inv.acceptance_id IS NULL THEN RETURN NULL; END IF;
    SELECT * INTO v_op FROM public.b05_invitation_operations
        WHERE acceptance_id = v_inv.acceptance_id FOR UPDATE;
    IF NOT FOUND OR NOT v_op.new_account OR v_op.stage NOT IN ('accepted','confirmed')
       OR v_op.kind IS DISTINCT FROM p_kind OR v_op.invitation_id IS DISTINCT FROM p_id
       OR v_op.user_id IS DISTINCT FROM v_inv.accepted_user_id OR v_op.auth_user_id IS NULL THEN RETURN NULL; END IF;
    PERFORM 1 FROM public.users WHERE id = v_op.user_id AND auth_user_id = v_op.auth_user_id
        AND status = 'active' AND lower(email) = lower(v_inv.email) FOR SHARE;
    IF NOT FOUND THEN RETURN NULL; END IF;
    RETURN to_jsonb(v_op);
END;
$$;
REVOKE ALL ON FUNCTION public.b05_recover_accepted_invitation(text,uuid,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_recover_accepted_invitation(text,uuid,text) TO service_role;

-- Include terminal rows missing the new event so a sweep also repairs historical
-- asynchronous-audit gaps. Token material never leaves this cleanup RPC.
CREATE FUNCTION public.b05_expiry_candidates(p_limit integer)
RETURNS SETOF jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(),'') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501'; END IF;
    RETURN QUERY SELECT to_jsonb(i) - 'token_hash' FROM public.platform_admin_invitations i
    WHERE (i.status = 'invited' AND i.expires_at <= clock_timestamp() AND i.acceptance_id IS NULL)
       OR (i.status = 'expired' AND NOT EXISTS (
            SELECT 1 FROM public.b05_invitation_lifecycle_audit a
            WHERE a.kind = 'institution' AND a.invitation_id = i.invitation_id AND a.status = 'expired'))
    ORDER BY i.expires_at LIMIT greatest(1,least(COALESCE(p_limit,200),200));
END;
$$;
REVOKE ALL ON FUNCTION public.b05_expiry_candidates(integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.b05_expiry_candidates(integer) TO service_role;

COMMIT;
