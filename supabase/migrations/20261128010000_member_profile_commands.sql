-- Commands that write Staff/Faculty employee profiles and additional departments.
--
-- Each command requires the service role and an active administrator of the
-- institution (phase81_assert_institution_admin), checks that the person holds
-- a Staff or Faculty grant in that institution, writes, and audits atomically.
-- P1201 department, P1204 employee ID in use, P1205 member not found,
-- 22023 malformed input.
BEGIN;

-- The Staff or Faculty role the person holds in this institution, or P1205.
CREATE FUNCTION public.member_profile_role(p_tenant uuid, p_user uuid)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_role text;
BEGIN
    SELECT r.name INTO v_role
    FROM public.user_roles ur JOIN public.roles r ON r.id = ur.role_id
    WHERE ur.user_id = p_user AND ur.scope_type = 'institution' AND ur.scope_id = p_tenant
      AND r.name IN ('staff', 'faculty')
    ORDER BY r.name = 'faculty' DESC
    LIMIT 1;
    IF v_role IS NULL THEN
        RAISE EXCEPTION 'Staff or faculty member not found' USING ERRCODE = 'P1205';
    END IF;
    RETURN v_role;
END;
$$;

-- True when another member, or another pending invitation, already uses the ID.
CREATE FUNCTION public.member_employee_id_taken(
    p_tenant uuid, p_employee_id text, p_user uuid, p_invitation uuid
) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.institution_member_profiles
        WHERE institution_id = p_tenant AND lower(employee_id) = lower(btrim(p_employee_id))
          AND user_id IS DISTINCT FROM p_user
    ) OR EXISTS (
        SELECT 1 FROM public.platform_admin_invitations
        WHERE institution_id = p_tenant AND status = 'invited' AND expires_at > clock_timestamp()
          AND lower(invited_profile #>> '{common,employee_id}') = lower(btrim(p_employee_id))
          AND invitation_id IS DISTINCT FROM p_invitation
    );
$$;

-- Serialize decisions about one employee ID within one institution.
CREATE FUNCTION public.member_employee_id_lock(p_tenant uuid, p_employee_id text)
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
    SELECT pg_advisory_xact_lock(hashtextextended(
        p_tenant::text || ':employee:' || lower(btrim(p_employee_id)), 0));
$$;

-- Write the common profile and the profile of the member's role. Callers have
-- already authorized the actor and resolved the role.
CREATE FUNCTION public.member_profile_apply(
    p_tenant uuid, p_user uuid, p_role text, p_profile jsonb, p_actor uuid, p_invitation uuid
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_common jsonb := p_profile -> 'common';
    v_detail jsonb := p_profile -> p_role;
    v_employee_id text := btrim(p_profile #>> '{common,employee_id}');
BEGIN
    IF jsonb_typeof(v_common) IS DISTINCT FROM 'object' OR jsonb_typeof(v_detail) IS DISTINCT FROM 'object'
       OR COALESCE(v_employee_id, '') = '' THEN
        RAISE EXCEPTION 'Profile details for this role are required' USING ERRCODE = '22023';
    END IF;
    PERFORM public.member_employee_id_lock(p_tenant, v_employee_id);
    IF public.member_employee_id_taken(p_tenant, v_employee_id, p_user, p_invitation) THEN
        RAISE EXCEPTION 'This employee ID is already in use' USING ERRCODE = 'P1204';
    END IF;
    INSERT INTO public.institution_member_profiles AS p (
        institution_id, user_id, employee_id, phone, designation, joining_date, created_by, updated_by
    ) VALUES (
        p_tenant, p_user, v_employee_id, NULLIF(btrim(v_common ->> 'phone'), ''),
        btrim(v_common ->> 'designation'), (v_common ->> 'joining_date')::date, p_actor, p_actor
    )
    ON CONFLICT (institution_id, user_id) DO UPDATE SET
        employee_id = EXCLUDED.employee_id, phone = EXCLUDED.phone,
        designation = EXCLUDED.designation, joining_date = EXCLUDED.joining_date,
        updated_by = p_actor, updated_at = now();

    IF p_role = 'faculty' THEN
        INSERT INTO public.faculty_profiles (
            institution_id, user_id, qualification, specialization, experience_years,
            employment_type, employment_start_date, contract_end_date
        ) VALUES (
            p_tenant, p_user, NULLIF(btrim(v_detail ->> 'qualification'), ''),
            NULLIF(btrim(v_detail ->> 'specialization'), ''), (v_detail ->> 'experience_years')::numeric,
            v_detail ->> 'employment_type', (v_detail ->> 'employment_start_date')::date,
            (v_detail ->> 'contract_end_date')::date
        )
        ON CONFLICT (institution_id, user_id) DO UPDATE SET
            qualification = EXCLUDED.qualification, specialization = EXCLUDED.specialization,
            experience_years = EXCLUDED.experience_years, employment_type = EXCLUDED.employment_type,
            employment_start_date = EXCLUDED.employment_start_date,
            contract_end_date = EXCLUDED.contract_end_date, updated_at = now();
    ELSE
        INSERT INTO public.staff_profiles (
            institution_id, user_id, staff_category, employment_type,
            employment_start_date, contract_end_date, responsibilities
        ) VALUES (
            p_tenant, p_user, v_detail ->> 'staff_category', v_detail ->> 'employment_type',
            (v_detail ->> 'employment_start_date')::date, (v_detail ->> 'contract_end_date')::date,
            ARRAY(SELECT btrim(value) FROM jsonb_array_elements_text(
                COALESCE(v_detail -> 'responsibilities', '[]'::jsonb)) AS value)
        )
        ON CONFLICT (institution_id, user_id) DO UPDATE SET
            staff_category = EXCLUDED.staff_category, employment_type = EXCLUDED.employment_type,
            employment_start_date = EXCLUDED.employment_start_date,
            contract_end_date = EXCLUDED.contract_end_date,
            responsibilities = EXCLUDED.responsibilities, updated_at = now();
    END IF;
END;
$$;

-- Administrator edit of an existing member's profile.
CREATE FUNCTION public.save_member_profile(
    p_actor uuid, p_tenant uuid, p_user uuid, p_profile jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_role text;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    v_role := public.member_profile_role(p_tenant, p_user);
    PERFORM public.member_profile_apply(p_tenant, p_user, v_role, p_profile, p_actor, NULL);
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'member.profile.saved', 'institution_member_profiles', p_user::text,
        jsonb_build_object('role', v_role, 'profile', p_profile));
    RETURN jsonb_build_object('user_id', p_user, 'role', v_role);
END;
$$;

-- Replace the member's additional departments. The primary department is kept
-- in institution_member_departments and may not be repeated here.
CREATE FUNCTION public.set_member_additional_departments(
    p_actor uuid, p_tenant uuid, p_user uuid, p_departments uuid[]
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_wanted uuid[] := ARRAY(SELECT DISTINCT d FROM unnest(COALESCE(p_departments, '{}')) d WHERE d IS NOT NULL);
    v_role text;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    v_role := public.member_profile_role(p_tenant, p_user);
    IF cardinality(v_wanted) > 10 THEN
        RAISE EXCEPTION 'Choose at most 10 additional departments' USING ERRCODE = '22023';
    END IF;
    IF EXISTS (
        SELECT 1 FROM unnest(v_wanted) d
        WHERE NOT EXISTS (SELECT 1 FROM public.departments x
                          WHERE x.department_id = d AND x.institution_id = p_tenant AND x.is_active)
    ) THEN
        RAISE EXCEPTION 'Choose active departments of this institution' USING ERRCODE = 'P1201';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.institution_member_departments
        WHERE institution_id = p_tenant AND user_id = p_user AND department_id = ANY (v_wanted)
    ) THEN
        RAISE EXCEPTION 'The primary department cannot also be additional' USING ERRCODE = '22023';
    END IF;
    DELETE FROM public.institution_member_additional_departments
    WHERE institution_id = p_tenant AND user_id = p_user AND NOT (department_id = ANY (v_wanted));
    INSERT INTO public.institution_member_additional_departments (institution_id, user_id, department_id, assigned_by)
    SELECT p_tenant, p_user, d, p_actor FROM unnest(v_wanted) d
    ON CONFLICT (institution_id, user_id, department_id) DO NOTHING;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'member.departments.additional', 'institution_member_additional_departments',
        p_user::text, jsonb_build_object('role', v_role, 'department_ids', to_jsonb(v_wanted)));
    RETURN jsonb_build_object('user_id', p_user, 'department_ids', to_jsonb(v_wanted));
END;
$$;

-- A department that becomes primary stops being additional for that member.
CREATE FUNCTION public.member_primary_department_dedupe()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    DELETE FROM public.institution_member_additional_departments
    WHERE institution_id = NEW.institution_id AND user_id = NEW.user_id
      AND department_id = NEW.department_id;
    RETURN NULL;
END;
$$;

CREATE TRIGGER institution_member_departments_dedupe_additional
    AFTER INSERT OR UPDATE OF department_id ON public.institution_member_departments
    FOR EACH ROW EXECUTE FUNCTION public.member_primary_department_dedupe();

REVOKE ALL ON FUNCTION public.member_primary_department_dedupe() FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.member_profile_role(uuid, uuid),
    public.member_employee_id_taken(uuid, text, uuid, uuid),
    public.member_employee_id_lock(uuid, text),
    public.member_profile_apply(uuid, uuid, text, jsonb, uuid, uuid)
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.save_member_profile(uuid, uuid, uuid, jsonb),
    public.set_member_additional_departments(uuid, uuid, uuid, uuid[])
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.save_member_profile(uuid, uuid, uuid, jsonb),
    public.set_member_additional_departments(uuid, uuid, uuid, uuid[])
    TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
