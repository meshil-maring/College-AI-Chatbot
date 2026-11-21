-- Staff and Faculty invited by an institution administrator.
--
-- The administrator enters the person's email, name, role and department. The
-- invitation reuses the existing invitation table, email outbox, acceptance
-- reservation and finalization; it adds no second token or delivery system.
--
-- Every Staff/Faculty grant keeps an approved membership request. For an
-- administrator invitation that record is written when the person accepts,
-- decided by the inviting administrator, in the same transaction as the role
-- grant and the department assignment. Older invitations keep the original
-- rule (an approved request must already exist).
--
-- The department is stored without a foreign key so an expired or cancelled
-- invitation never blocks deleting an unused department. It is checked when
-- the invitation is created and again when it is accepted.
BEGIN;

ALTER TABLE public.platform_admin_invitations
    ADD COLUMN admin_invited boolean NOT NULL DEFAULT false,
    ADD COLUMN invited_department_id uuid,
    ADD COLUMN invited_full_name text;

ALTER TABLE public.platform_admin_invitations
    ADD CONSTRAINT platform_admin_invitations_admin_invited_role_check
        CHECK (NOT admin_invited OR role_name IN ('staff', 'faculty')),
    ADD CONSTRAINT platform_admin_invitations_invited_details_check
        CHECK ((invited_department_id IS NULL AND invited_full_name IS NULL) OR admin_invited),
    ADD CONSTRAINT platform_admin_invitations_invited_full_name_check
        CHECK (invited_full_name IS NULL
               OR (btrim(invited_full_name) <> '' AND length(invited_full_name) <= 200));

-- What the administrator chose cannot be rewritten after the invitation is sent.
CREATE FUNCTION public.member_invitation_details_immutable()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF NEW.admin_invited IS DISTINCT FROM OLD.admin_invited
       OR NEW.invited_department_id IS DISTINCT FROM OLD.invited_department_id
       OR NEW.invited_full_name IS DISTINCT FROM OLD.invited_full_name
       OR NEW.role_name IS DISTINCT FROM OLD.role_name THEN
        RAISE EXCEPTION 'Invitation details are immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_member_invitation_details_immutable
    BEFORE UPDATE ON public.platform_admin_invitations
    FOR EACH ROW EXECUTE FUNCTION public.member_invitation_details_immutable();

-- Create one Staff/Faculty invitation and its email job atomically.
-- P1201 department, P1202 already a member, P1203 invitation already pending.
CREATE FUNCTION public.create_member_invitation(
    p_actor uuid, p_tenant uuid, p_email text, p_full_name text, p_role text,
    p_department uuid, p_token_hash text, p_expires_at timestamptz, p_protected_token text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_email text := lower(btrim(p_email));
    v_invitation public.platform_admin_invitations%ROWTYPE;
    v_outbox_id uuid;
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
        email_delivery_status, admin_invited, invited_department_id, invited_full_name
    ) VALUES (
        p_tenant, v_email, p_token_hash, p_role, 'invited', p_expires_at, p_actor,
        'pending', true, p_department, NULLIF(btrim(p_full_name), '')
    ) RETURNING * INTO v_invitation;

    INSERT INTO public.email_outbox (aggregate_id, protected_token)
    VALUES (v_invitation.invitation_id, p_protected_token)
    RETURNING id INTO v_outbox_id;

    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'membership.invitation.created', 'platform_admin_invitations',
        v_invitation.invitation_id::text,
        jsonb_build_object('email', v_email, 'role', p_role, 'department_id', p_department,
            'expires_at', p_expires_at));

    RETURN (to_jsonb(v_invitation) - 'token_hash')
        || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;

REVOKE ALL ON FUNCTION public.member_invitation_details_immutable() FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.create_member_invitation(
    uuid, uuid, text, text, text, uuid, text, timestamptz, text
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_member_invitation(
    uuid, uuid, text, text, text, uuid, text, timestamptz, text
) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
