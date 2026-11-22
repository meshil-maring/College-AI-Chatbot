-- Administrator employee profiles (User Management U2/U3).
--
-- An administrator's profile holds the shared employee fields only: employee
-- ID, phone, designation and joining date, in institution_member_profiles, so
-- employee IDs stay unique across Staff, Faculty and administrators. The Owner
-- edits any administrator's profile and each administrator may edit their own.
-- A profile is optional when inviting; administrators without one are shown as
-- "Profile incomplete". Admin access areas are separate (20261202000000).
-- Codes: P1204 employee ID in use, P1401 not the Owner, P1402 not an
-- administrator, 22023 invalid fields.
BEGIN;

-- Invited profiles for administrators carry no Staff/Faculty details, so the
-- Staff/Faculty apply trigger (20261128020000) now runs only for those roles.
DROP TRIGGER trg_member_invitation_apply_profile ON public.platform_admin_invitations;
CREATE TRIGGER trg_member_invitation_apply_profile
    AFTER UPDATE OF status ON public.platform_admin_invitations
    FOR EACH ROW
    WHEN (NEW.status = 'accepted' AND OLD.status IS DISTINCT FROM 'accepted'
          AND NEW.admin_invited AND NEW.invited_profile IS NOT NULL
          AND NEW.accepted_user_id IS NOT NULL AND NEW.role_name IN ('staff', 'faculty'))
    EXECUTE FUNCTION public.member_invitation_apply_profile();

-- Validated shared fields: {"employee_id", "designation", "joining_date", "phone"?}.
CREATE FUNCTION public.admin_profile_common(p_common jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = '' AS $$
DECLARE
    v_employee_id text := btrim(p_common ->> 'employee_id');
    v_designation text := btrim(p_common ->> 'designation');
    v_phone text := NULLIF(btrim(p_common ->> 'phone'), '');
    v_joining date;
BEGIN
    IF jsonb_typeof(p_common) IS DISTINCT FROM 'object' OR COALESCE(v_employee_id, '') = ''
       OR COALESCE(v_designation, '') = '' OR COALESCE(p_common ->> 'joining_date', '') = '' THEN
        RAISE EXCEPTION 'Employee ID, designation and joining date are required' USING ERRCODE = '22023';
    END IF;
    v_joining := (p_common ->> 'joining_date')::date;
    RETURN jsonb_build_object('employee_id', v_employee_id, 'designation', v_designation,
        'joining_date', v_joining, 'phone', v_phone);
EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN
    RAISE EXCEPTION 'Joining date is not a valid date' USING ERRCODE = '22023';
END;
$$;

-- Write an administrator's shared profile; employee IDs are unique per institution.
CREATE FUNCTION public.admin_profile_write(
    p_tenant uuid, p_user uuid, p_common jsonb, p_actor uuid, p_invitation uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_common jsonb := public.admin_profile_common(p_common);
BEGIN
    PERFORM public.member_employee_id_lock(p_tenant, v_common ->> 'employee_id');
    IF public.member_employee_id_taken(p_tenant, v_common ->> 'employee_id', p_user, p_invitation) THEN
        RAISE EXCEPTION 'This employee ID is already in use' USING ERRCODE = 'P1204';
    END IF;
    INSERT INTO public.institution_member_profiles AS p (
        institution_id, user_id, employee_id, phone, designation, joining_date, created_by, updated_by
    ) VALUES (
        p_tenant, p_user, v_common ->> 'employee_id', v_common ->> 'phone', v_common ->> 'designation',
        (v_common ->> 'joining_date')::date, p_actor, p_actor
    )
    ON CONFLICT (institution_id, user_id) DO UPDATE SET
        employee_id = EXCLUDED.employee_id, phone = EXCLUDED.phone, designation = EXCLUDED.designation,
        joining_date = EXCLUDED.joining_date, updated_by = p_actor, updated_at = now();
    RETURN v_common;
END;
$$;

-- The Owner saves any administrator's profile; an administrator saves their own.
CREATE FUNCTION public.save_admin_profile(p_actor uuid, p_tenant uuid, p_user uuid, p_common jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_common jsonb;
BEGIN
    IF p_actor = p_user THEN
        PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    ELSE
        PERFORM public.institution_owner_assert(p_actor, p_tenant);
    END IF;
    IF p_user IS NULL OR NOT p_user = ANY (public.institution_admin_ids(p_tenant)) THEN
        RAISE EXCEPTION 'Choose an active administrator of the institution' USING ERRCODE = 'P1402';
    END IF;
    v_common := public.admin_profile_write(p_tenant, p_user, p_common, p_actor, NULL);
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'institution.admin.profile', 'institution_member_profiles', p_user::text,
        jsonb_build_object('target_user_id', p_user, 'profile', v_common));
    RETURN jsonb_build_object('user_id', p_user, 'profile', v_common);
END;
$$;

-- Apply an invited administrator's profile when the invitation is accepted.
CREATE FUNCTION public.admin_invitation_apply_profile()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.admin_profile_write(NEW.institution_id, NEW.accepted_user_id,
        NEW.invited_profile -> 'common', NEW.created_by, NEW.invitation_id);
    RETURN NULL;
END;
$$;
CREATE TRIGGER trg_admin_invitation_apply_profile
    AFTER UPDATE OF status ON public.platform_admin_invitations
    FOR EACH ROW
    WHEN (NEW.status = 'accepted' AND OLD.status IS DISTINCT FROM 'accepted' AND NEW.role_name = 'admin'
          AND NEW.admin_invited AND NEW.invited_profile IS NOT NULL AND NEW.accepted_user_id IS NOT NULL)
    EXECUTE FUNCTION public.admin_invitation_apply_profile();

-- Record a validated profile on a new administrator invitation (called by
-- create_admin_invitation, 20261203010000), reserving its employee ID.
CREATE FUNCTION public.admin_invitation_profile(p_tenant uuid, p_common jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_common jsonb;
BEGIN
    IF p_common IS NULL THEN
        RETURN NULL;
    END IF;
    v_common := public.admin_profile_common(p_common);
    PERFORM public.member_employee_id_lock(p_tenant, v_common ->> 'employee_id');
    IF public.member_employee_id_taken(p_tenant, v_common ->> 'employee_id', NULL, NULL) THEN
        RAISE EXCEPTION 'This employee ID is already in use' USING ERRCODE = 'P1204';
    END IF;
    RETURN jsonb_build_object('common', v_common);
END;
$$;

REVOKE ALL ON FUNCTION public.admin_profile_common(jsonb),
    public.admin_profile_write(uuid, uuid, jsonb, uuid, uuid),
    public.admin_invitation_apply_profile(), public.admin_invitation_profile(uuid, jsonb)
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.save_admin_profile(uuid, uuid, uuid, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.save_admin_profile(uuid, uuid, uuid, jsonb) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
