-- Administrator profile contracts. LOCAL database only:
--   psql -f tests/member_management/sql/admin_profile_contracts.sql   (rolled back)
-- "admin" is the Owner of institution A; "invitee" is a second administrator.
\set ON_ERROR_STOP 1
BEGIN;
\ir profile_fixture.sql

INSERT INTO public.user_roles (user_id, role_id, scope_type, scope_id, scope_organization_id, assigned_at)
SELECT member_fixture.id('invitee'), id, 'institution', member_fixture.id('tenant'), member_fixture.id('org'),
       now() + interval '1 second'
FROM public.roles WHERE name = 'admin';

CREATE FUNCTION member_fixture.common(p_employee_id text) RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
    SELECT jsonb_build_object('employee_id', p_employee_id, 'designation', 'Registrar',
        'joining_date', '2026-01-05', 'phone', '+91 90000 00000');
$$;

DO $$
DECLARE
    owner uuid := member_fixture.id('admin');
    admin2 uuid := member_fixture.id('invitee');
    tenant uuid := member_fixture.id('tenant');
    listed jsonb;
    invitation jsonb;
    new_auth uuid := '0f000000-0000-4000-8000-00000000e301';
    newcomer uuid;
    op jsonb;
BEGIN
    -- 1. The Owner edits another administrator; an administrator edits only their own.
    PERFORM public.save_admin_profile(owner, tenant, admin2, member_fixture.common('ADM-2'));
    PERFORM public.save_admin_profile(admin2, tenant, admin2,
        member_fixture.common('ADM-2') || '{"designation": "Deputy Registrar", "phone": ""}');
    IF (SELECT designation || '|' || COALESCE(phone, '-') FROM public.institution_member_profiles
        WHERE user_id = admin2) <> 'Deputy Registrar|-' THEN
        RAISE EXCEPTION 'Own profile edit was not saved';
    END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.save_admin_profile(%L, %L, %L, %L)',
        admin2, tenant, owner, member_fixture.common('ADM-1')), 'P1401', 'non-owner edits another administrator');
    PERFORM member_fixture.expect_error(format('SELECT public.save_admin_profile(%L, %L, %L, %L)',
        owner, tenant, member_fixture.id('s1'), member_fixture.common('ADM-9')), 'P1402', 'staff target');
    PERFORM member_fixture.expect_error(format('SELECT public.save_admin_profile(%L, %L, %L, %L)',
        owner, tenant, owner, '{"employee_id": "ADM-1"}'), '22023', 'missing designation and date');
    PERFORM member_fixture.expect_error(format('SELECT public.save_admin_profile(%L, %L, %L, %L)',
        owner, tenant, owner, member_fixture.common('ADM-1') || '{"joining_date": "2026-02-31"}'),
        '22023', 'impossible date');

    -- 2. Employee IDs are unique across Staff, Faculty and administrators.
    PERFORM public.save_member_profile(owner, tenant, member_fixture.id('f1'), member_fixture.faculty('EMP-1'));
    PERFORM member_fixture.expect_error(format('SELECT public.save_admin_profile(%L, %L, %L, %L)',
        owner, tenant, owner, member_fixture.common('emp-1')), 'P1204', 'faculty employee ID reused');

    -- 3. The list shows profiles; the Owner has none yet.
    listed := public.read_institution_admins(owner, tenant) -> 'administrators';
    IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(listed) a
                   WHERE a ->> 'user_id' = admin2::text AND a #>> '{profile,employee_id}' = 'ADM-2')
       OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(listed) a
                      WHERE a ->> 'user_id' = owner::text AND a -> 'profile' = 'null') THEN
        RAISE EXCEPTION 'Listing does not show profiles: %', listed;
    END IF;

    -- 4. An invitation's profile reserves its employee ID and applies on acceptance.
    PERFORM member_fixture.expect_error(format(
        'SELECT public.create_admin_invitation(%L, %L, %L, NULL, %L, now() + interval ''1 day'', %L, NULL, %L)',
        owner, tenant, 'dup@member.test', repeat('c3', 32), repeat('r', 96), member_fixture.common('ADM-2')),
        'P1204', 'invitation with a used employee ID');
    invitation := public.create_admin_invitation(owner, tenant, 'prof@member.test', 'Pro', repeat('d4', 32),
        now() + interval '1 day', repeat('s', 96), NULL, member_fixture.common('ADM-7'));
    PERFORM member_fixture.expect_error(format('SELECT public.save_member_profile(%L, %L, %L, %L)',
        owner, tenant, member_fixture.id('f2'), member_fixture.faculty('ADM-7')), 'P1204', 'reserved by invitation');
    IF (public.read_institution_admins(owner, tenant) #>> '{invitations,0,profile,designation}') <> 'Registrar' THEN
        RAISE EXCEPTION 'Invitation listing does not show the profile';
    END IF;
    INSERT INTO auth.users (id, email, instance_id, aud, role)
    VALUES (new_auth, 'prof@member.test', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated');
    op := public.b05_reserve_invitation('institution', (invitation ->> 'invitation_id')::uuid, repeat('d4', 32),
        '0f000000-0000-4000-8000-00000000f301', NULL, NULL);
    PERFORM public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f301', 'reserved', 'provider_started', NULL, NULL, NULL, NULL);
    PERFORM public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f301', 'provider_started', 'provider_created', new_auth, NULL, NULL, NULL);
    op := public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f301', 'provider_created', 'user_created', new_auth, NULL, 'Pro', 'Admin');
    newcomer := (op ->> 'user_id')::uuid;
    op := public.b05_finalize_invitation('institution', (invitation ->> 'invitation_id')::uuid, repeat('d4', 32),
        '0f000000-0000-4000-8000-00000000f301', newcomer);
    IF op IS NULL OR (SELECT employee_id FROM public.institution_member_profiles WHERE user_id = newcomer) <> 'ADM-7'
       OR EXISTS (SELECT 1 FROM public.staff_profiles WHERE user_id = newcomer)
       OR EXISTS (SELECT 1 FROM public.faculty_profiles WHERE user_id = newcomer) THEN
        RAISE EXCEPTION 'Accepted invitation did not apply only the administrator profile: %', op;
    END IF;

    -- 5. Audit and privileges.
    IF (SELECT count(*) FROM public.admin_audit_log WHERE action = 'institution.admin.profile'
        AND record_id = admin2::text) <> 2 THEN
        RAISE EXCEPTION 'Profile changes were not audited against the administrator';
    END IF;
    IF has_function_privilege('service_role', 'public.admin_profile_write(uuid,uuid,jsonb,uuid,uuid)', 'EXECUTE')
       OR has_function_privilege('authenticated', 'public.save_admin_profile(uuid,uuid,uuid,jsonb)', 'EXECUTE')
       OR NOT has_function_privilege('service_role', 'public.save_admin_profile(uuid,uuid,uuid,jsonb)', 'EXECUTE')
       OR NOT has_function_privilege('service_role',
           'public.create_admin_invitation(uuid,uuid,text,text,text,timestamptz,text,text[],jsonb)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Unexpected profile privileges';
    END IF;
    RAISE NOTICE 'admin profile contracts passed';
END;
$$;

ROLLBACK;
