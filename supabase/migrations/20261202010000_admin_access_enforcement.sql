-- Enforce administrator access areas (20261202000000) where the database itself
-- decides, and let the Owner choose access when inviting an administrator.
--
-- * create_admin_invitation takes the access areas; accepting the invitation
--   applies them (none chosen, or every area, means full access).
-- * A staff permission can be granted only by an administrator whose own
--   access includes it, so a limited administrator cannot pass on more (P1405).
-- * Teaching assignments count an administrator only when their access
--   includes Staff and Faculty (users.update).
-- Routes under /admin are already checked against the limited permission codes
-- by the backend; transfer_admin_allowed follows in 20261202020000.
BEGIN;

DROP FUNCTION public.create_admin_invitation(uuid, uuid, text, text, text, timestamptz, text);

-- As in 20261130010000, plus the access areas for the new administrator.
CREATE FUNCTION public.create_admin_invitation(
    p_actor uuid, p_tenant uuid, p_email text, p_full_name text,
    p_token_hash text, p_expires_at timestamptz, p_protected_token text, p_access_areas text[] DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_email text := lower(btrim(p_email));
    v_areas text[];
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
    INSERT INTO public.platform_admin_invitations (
        institution_id, email, token_hash, role_name, status, expires_at, created_by,
        email_delivery_status, admin_invited, invited_full_name, invited_admin_areas
    ) VALUES (
        p_tenant, v_email, p_token_hash, 'admin', 'invited', p_expires_at, p_actor,
        'pending', true, NULLIF(btrim(p_full_name), ''), v_areas
    ) RETURNING * INTO v_invitation;
    INSERT INTO public.email_outbox (aggregate_id, protected_token)
    VALUES (v_invitation.invitation_id, p_protected_token) RETURNING id INTO v_outbox_id;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'institution.admin.invite', 'platform_admin_invitations',
        v_invitation.invitation_id::text, jsonb_build_object('email', v_email, 'expires_at', p_expires_at,
            'access_areas', to_jsonb(v_areas)));
    RETURN (to_jsonb(v_invitation) - 'token_hash') || jsonb_build_object('email_outbox_id', v_outbox_id);
END;
$$;

-- Apply the invited access once b05_finalize_invitation marks the invitation
-- accepted (the admin role is granted in that same transaction).
CREATE FUNCTION public.admin_invitation_apply_access()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF NEW.invited_admin_areas IS NULL OR EXISTS (
        SELECT 1 FROM public.institutions
        WHERE institution_id = NEW.institution_id AND owner_user_id = NEW.accepted_user_id) THEN
        DELETE FROM public.institution_admin_access
        WHERE institution_id = NEW.institution_id AND user_id = NEW.accepted_user_id;
    ELSE
        INSERT INTO public.institution_admin_access (institution_id, user_id, areas, allowed_codes, updated_by)
        VALUES (NEW.institution_id, NEW.accepted_user_id, NEW.invited_admin_areas,
            public.institution_admin_area_codes(NEW.invited_admin_areas), NEW.created_by)
        ON CONFLICT (institution_id, user_id) DO UPDATE
        SET areas = EXCLUDED.areas, allowed_codes = EXCLUDED.allowed_codes,
            updated_by = EXCLUDED.updated_by, updated_at = now();
    END IF;
    RETURN NULL;
END;
$$;
CREATE TRIGGER trg_admin_invitation_apply_access
    AFTER UPDATE OF status ON public.platform_admin_invitations
    FOR EACH ROW
    WHEN (NEW.status = 'accepted' AND OLD.status IS DISTINCT FROM 'accepted'
          AND NEW.role_name = 'admin' AND NEW.admin_invited AND NEW.accepted_user_id IS NOT NULL)
    EXECUTE FUNCTION public.admin_invitation_apply_access();

-- No escalation through Staff permissions: the granting administrator's own
-- access must include every code they grant.
CREATE FUNCTION public.staff_grant_within_granter_access()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_code text;
BEGIN
    SELECT code INTO v_code FROM public.permissions WHERE permission_id = NEW.permission_id;
    IF NEW.granted_by IS NOT NULL
       AND NOT public.institution_admin_access_allows(NEW.granted_by, NEW.institution_id, v_code) THEN
        RAISE EXCEPTION 'You can grant only permissions your own access includes' USING ERRCODE = 'P1405';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER user_permission_grants_within_access
    BEFORE INSERT ON public.user_permission_grants
    FOR EACH ROW EXECUTE FUNCTION public.staff_grant_within_granter_access();

-- As in 20261201000000; an administrator counts only with Staff and Faculty access.
CREATE OR REPLACE FUNCTION public.teaching_actor(p_actor uuid, p_tenant uuid, OUT is_admin boolean, OUT heads uuid[])
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;
    is_admin := EXISTS (
        SELECT 1 FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.id
        JOIN public.roles r ON r.id = ur.role_id
        JOIN public.institutions i ON i.institution_id = p_tenant
        WHERE u.id = p_actor AND u.status = 'active' AND r.name = 'admin' AND r.is_active
          AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
          AND i.status = 'active' AND i.is_active)
        AND public.institution_admin_access_allows(p_actor, p_tenant, 'users.update');
    heads := public.transfer_hod_departments(p_actor, p_tenant);
    IF NOT is_admin AND cardinality(heads) = 0 THEN
        RAISE EXCEPTION 'Only administrators and Heads of Department manage teaching' USING ERRCODE = '42501';
    END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.admin_invitation_apply_access(), public.staff_grant_within_granter_access()
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.create_admin_invitation(uuid, uuid, text, text, text, timestamptz, text, text[])
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_admin_invitation(uuid, uuid, text, text, text, timestamptz, text, text[])
    TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
