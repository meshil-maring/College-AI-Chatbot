-- Institution Owner and owner-managed administrators (User Management U2).
--
-- The Owner is an administrator of the institution with protected authority,
-- not a separate role: only the Owner invites or removes other administrators
-- and transfers ownership. Every administrator keeps the full admin permission
-- set; per-administrator permission scoping is a later phase.
--
-- Existing institutions get their longest-standing active administrator as
-- Owner. The first administrator of a new institution becomes its Owner when
-- the role is granted. If a platform super admin removes the Owner's admin role,
-- ownership passes to the next longest-standing active administrator (or none).
-- P1401 Owner required, P1402 target is not an administrator, P1403 the Owner
-- cannot be removed, P1202/P1203 as for member invitations.
BEGIN;

ALTER TABLE public.institutions ADD COLUMN owner_user_id uuid REFERENCES public.users(id);

-- Active administrators of one institution, longest-standing first.
CREATE FUNCTION public.institution_admin_ids(p_tenant uuid)
RETURNS uuid[] LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(array_agg(u.id ORDER BY ur.assigned_at, u.id), '{}'::uuid[])
    FROM public.user_roles ur
    JOIN public.roles r ON r.id = ur.role_id AND r.name = 'admin'
    JOIN public.users u ON u.id = ur.user_id AND u.status = 'active'
    WHERE ur.scope_type = 'institution' AND ur.scope_id = p_tenant;
$$;

UPDATE public.institutions i SET owner_user_id = (public.institution_admin_ids(i.institution_id))[1];

-- The Owner must be an active administrator of the institution.
CREATE FUNCTION public.institution_owner_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF NEW.owner_user_id IS NOT NULL
       AND NOT NEW.owner_user_id = ANY (public.institution_admin_ids(NEW.institution_id)) THEN
        RAISE EXCEPTION 'The Owner must be an active administrator of the institution' USING ERRCODE = 'P1402';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER institutions_owner_guard
    BEFORE UPDATE OF owner_user_id ON public.institutions
    FOR EACH ROW EXECUTE FUNCTION public.institution_owner_guard();

-- Ownership follows administrator grants: the first administrator becomes Owner,
-- and removing the Owner's grant passes ownership to the next administrator.
CREATE FUNCTION public.institution_owner_follow_grants()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_row public.user_roles := COALESCE(NEW, OLD);
BEGIN
    IF v_row.scope_type <> 'institution' OR NOT EXISTS (
        SELECT 1 FROM public.roles WHERE id = v_row.role_id AND name = 'admin') THEN
        RETURN NULL;
    END IF;
    IF TG_OP = 'INSERT' THEN
        UPDATE public.institutions SET owner_user_id = v_row.user_id
        WHERE institution_id = v_row.scope_id AND owner_user_id IS NULL
          AND v_row.user_id = ANY (public.institution_admin_ids(v_row.scope_id));
    ELSE
        UPDATE public.institutions SET owner_user_id = (public.institution_admin_ids(v_row.scope_id))[1]
        WHERE institution_id = v_row.scope_id AND owner_user_id = v_row.user_id;
    END IF;
    RETURN NULL;
END;
$$;
CREATE TRIGGER user_roles_institution_owner
    AFTER INSERT OR DELETE ON public.user_roles
    FOR EACH ROW EXECUTE FUNCTION public.institution_owner_follow_grants();

-- An active administrator who is also the institution's current Owner.
CREATE FUNCTION public.institution_owner_assert(p_actor uuid, p_tenant uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    IF NOT EXISTS (SELECT 1 FROM public.institutions WHERE institution_id = p_tenant AND owner_user_id = p_actor) THEN
        RAISE EXCEPTION 'Only the institution Owner can do this' USING ERRCODE = 'P1401';
    END IF;
END;
$$;

-- Administrators, the Owner and pending administrator invitations.
CREATE FUNCTION public.read_institution_admins(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    RETURN jsonb_build_object(
        'owner_user_id', (SELECT owner_user_id FROM public.institutions WHERE institution_id = p_tenant),
        'administrators', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'user_id', u.id, 'email', u.email, 'status', u.status, 'assigned_at', ur.assigned_at,
                'name', COALESCE(NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email)
            ) ORDER BY ur.assigned_at, u.id)
            FROM public.user_roles ur
            JOIN public.roles r ON r.id = ur.role_id AND r.name = 'admin'
            JOIN public.users u ON u.id = ur.user_id
            WHERE ur.scope_type = 'institution' AND ur.scope_id = p_tenant), '[]'::jsonb),
        'invitations', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'invitation_id', i.invitation_id, 'email', i.email, 'full_name', i.invited_full_name,
                'expires_at', i.expires_at, 'created_at', i.created_at,
                'email_delivery_status', i.email_delivery_status
            ) ORDER BY i.created_at DESC)
            FROM public.platform_admin_invitations i
            WHERE i.institution_id = p_tenant AND i.role_name = 'admin' AND i.status = 'invited'
              AND i.expires_at > clock_timestamp()), '[]'::jsonb)
    );
END;
$$;

-- Hand ownership to another active administrator; the previous Owner stays an administrator.
CREATE FUNCTION public.transfer_institution_ownership(p_actor uuid, p_tenant uuid, p_new_owner uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.institution_owner_assert(p_actor, p_tenant);
    IF p_new_owner IS NULL OR NOT p_new_owner = ANY (public.institution_admin_ids(p_tenant)) THEN
        RAISE EXCEPTION 'Choose an active administrator of the institution' USING ERRCODE = 'P1402';
    END IF;
    IF p_new_owner = p_actor THEN
        RETURN jsonb_build_object('owner_user_id', p_actor, 'already_applied', true);
    END IF;
    UPDATE public.institutions SET owner_user_id = p_new_owner WHERE institution_id = p_tenant;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'institution.owner.transfer', 'institutions', p_tenant::text,
        jsonb_build_object('before', p_actor, 'after', p_new_owner));
    RETURN jsonb_build_object('owner_user_id', p_new_owner, 'already_applied', false);
END;
$$;

-- Remove another administrator's admin role. The account and its records stay.
CREATE FUNCTION public.revoke_institution_admin(p_actor uuid, p_tenant uuid, p_user uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.institution_owner_assert(p_actor, p_tenant);
    IF p_user = p_actor THEN
        RAISE EXCEPTION 'Transfer ownership before removing your own access' USING ERRCODE = 'P1403';
    END IF;
    DELETE FROM public.user_roles ur USING public.roles r
    WHERE r.id = ur.role_id AND r.name = 'admin' AND ur.user_id = p_user
      AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'This person is not an administrator of the institution' USING ERRCODE = 'P1402';
    END IF;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'institution.admin.revoke', 'user_roles', p_user::text,
        jsonb_build_object('role', 'admin'));
    RETURN jsonb_build_object('user_id', p_user, 'revoked', true);
END;
$$;

REVOKE ALL ON FUNCTION public.institution_admin_ids(uuid), public.institution_owner_guard(),
    public.institution_owner_follow_grants(), public.institution_owner_assert(uuid, uuid)
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.read_institution_admins(uuid, uuid),
    public.transfer_institution_ownership(uuid, uuid, uuid), public.revoke_institution_admin(uuid, uuid, uuid)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.read_institution_admins(uuid, uuid),
    public.transfer_institution_ownership(uuid, uuid, uuid), public.revoke_institution_admin(uuid, uuid, uuid)
    TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
