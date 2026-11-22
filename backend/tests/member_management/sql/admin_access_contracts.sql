-- Administrator access area contracts. LOCAL database only:
--   psql -f tests/member_management/sql/admin_access_contracts.sql   (rolled back)
-- "admin" is the Owner of institution A; "invitee" is a second administrator.
\set ON_ERROR_STOP 1
BEGIN;
\ir profile_fixture.sql

INSERT INTO public.user_roles (user_id, role_id, scope_type, scope_id, scope_organization_id, assigned_at)
SELECT member_fixture.id('invitee'), id, 'institution', member_fixture.id('tenant'), member_fixture.id('org'),
       now() + interval '1 second'
FROM public.roles WHERE name = 'admin';

DO $$
DECLARE
    owner uuid := member_fixture.id('admin');
    admin2 uuid := member_fixture.id('invitee');
    tenant uuid := member_fixture.id('tenant');
    staff uuid := member_fixture.id('s1');
    result jsonb;
    listed jsonb;
    invitation jsonb;
    new_auth uuid := '0f000000-0000-4000-8000-00000000e201';
    newcomer uuid;
    op jsonb;
BEGIN
    -- 1. The Owner limits another administrator; codes follow the chosen areas.
    result := public.set_institution_admin_access(owner, tenant, admin2, ARRAY['content', 'students']);
    IF (result ->> 'full_access')::boolean OR result -> 'access_areas' <> '["students", "content"]'::jsonb THEN
        RAISE EXCEPTION 'Limit was not stored in area order: %', result;
    END IF;
    IF NOT public.institution_admin_access_allows(admin2, tenant, 'notices.create')
       OR NOT public.institution_admin_access_allows(admin2, tenant, 'courses.read')
       OR public.institution_admin_access_allows(admin2, tenant, 'users.read')
       OR public.institution_admin_access_allows(admin2, tenant, 'some.future.permission')
       OR NOT public.institution_admin_access_allows(owner, tenant, 'users.read') THEN
        RAISE EXCEPTION 'Access checks do not follow the areas';
    END IF;
    listed := public.read_institution_admins(admin2, tenant);
    IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(listed -> 'administrators') a
                   WHERE a ->> 'user_id' = admin2::text AND a -> 'access_areas' = '["students", "content"]')
       OR jsonb_array_length(listed -> 'access_areas') <> 6 THEN
        RAISE EXCEPTION 'Listing does not show the access: %', listed;
    END IF;

    -- 2. Only the Owner sets access, never their own, and only known areas.
    PERFORM member_fixture.expect_error(format('SELECT public.set_institution_admin_access(%L, %L, %L, NULL)',
        admin2, tenant, owner), 'P1401', 'non-owner changes access');
    PERFORM member_fixture.expect_error(format('SELECT public.set_institution_admin_access(%L, %L, %L, %L)',
        owner, tenant, owner, '{content}'), 'P1404', 'Owner limits themselves');
    PERFORM member_fixture.expect_error(format('SELECT public.set_institution_admin_access(%L, %L, %L, %L)',
        owner, tenant, admin2, '{everything}'), '22023', 'unknown area');
    PERFORM member_fixture.expect_error(format('SELECT public.set_institution_admin_access(%L, %L, %L, NULL)',
        owner, tenant, staff), 'P1402', 'staff member as target');

    -- 3. Database-decided paths respect the limit.
    IF NOT public.transfer_admin_allowed(admin2, tenant, 'transfers.read') THEN
        RAISE EXCEPTION 'Students access should allow transfer reviews';
    END IF;
    PERFORM public.set_institution_admin_access(owner, tenant, admin2, ARRAY['content']);
    IF public.transfer_admin_allowed(admin2, tenant, 'transfers.read') THEN
        RAISE EXCEPTION 'Transfers stayed open without Students access';
    END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.read_teaching_assignments(%L, %L)',
        admin2, tenant), '42501', 'teaching without Staff and Faculty access');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.phase81_manage_staff_permission_grants(%L, %L, %L, %L, true)',
        admin2, tenant, staff, '{students.read}'), 'P1405', 'granting a permission outside own access');
    IF public.phase81_manage_staff_permission_grants(admin2, tenant, staff, ARRAY['notices.read'], true) <> 1
       OR public.phase81_manage_staff_permission_grants(owner, tenant, staff, ARRAY['students.read'], true) <> 1 THEN
        RAISE EXCEPTION 'Grants within access were refused';
    END IF;

    -- 4. Every area means full access again.
    result := public.set_institution_admin_access(owner, tenant, admin2, public.institution_admin_areas());
    IF NOT (result ->> 'full_access')::boolean
       OR EXISTS (SELECT 1 FROM public.institution_admin_access WHERE user_id = admin2) THEN
        RAISE EXCEPTION 'Full access did not clear the limit';
    END IF;

    -- 5. Access chosen at invitation applies on acceptance; every area is stored as full.
    invitation := public.create_admin_invitation(owner, tenant, 'limited@member.test', 'Lim', repeat('a1', 32),
        now() + interval '1 day', repeat('p', 96), ARRAY['content']);
    IF invitation -> 'invited_admin_areas' <> '["content"]' THEN
        RAISE EXCEPTION 'Invitation did not keep the access: %', invitation;
    END IF;
    IF (public.create_admin_invitation(owner, tenant, 'full@member.test', 'Full', repeat('b2', 32),
            now() + interval '1 day', repeat('q', 96), public.institution_admin_areas()) -> 'invited_admin_areas')
        <> 'null'::jsonb THEN
        RAISE EXCEPTION 'Every area should be stored as full access';
    END IF;
    INSERT INTO auth.users (id, email, instance_id, aud, role)
    VALUES (new_auth, 'limited@member.test', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated');
    op := public.b05_reserve_invitation('institution', (invitation ->> 'invitation_id')::uuid, repeat('a1', 32),
        '0f000000-0000-4000-8000-00000000f201', NULL, NULL);
    PERFORM public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f201', 'reserved', 'provider_started', NULL, NULL, NULL, NULL);
    PERFORM public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f201', 'provider_started', 'provider_created', new_auth, NULL, NULL, NULL);
    op := public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f201', 'provider_created', 'user_created', new_auth, NULL, 'Lim', 'Admin');
    newcomer := (op ->> 'user_id')::uuid;
    op := public.b05_finalize_invitation('institution', (invitation ->> 'invitation_id')::uuid, repeat('a1', 32),
        '0f000000-0000-4000-8000-00000000f201', newcomer);
    IF op IS NULL THEN RAISE EXCEPTION 'Limited invitation could not be accepted'; END IF;
    IF (SELECT areas FROM public.institution_admin_access WHERE user_id = newcomer) <> ARRAY['content'] THEN
        RAISE EXCEPTION 'Accepted invitation did not apply the access';
    END IF;

    -- 6. A new Owner is never limited; removing the admin role clears the limit.
    PERFORM public.transfer_institution_ownership(owner, tenant, newcomer);
    IF EXISTS (SELECT 1 FROM public.institution_admin_access WHERE user_id = newcomer) THEN
        RAISE EXCEPTION 'The new Owner kept a limit';
    END IF;
    PERFORM public.set_institution_admin_access(newcomer, tenant, admin2, ARRAY['content']);
    PERFORM public.revoke_institution_admin(newcomer, tenant, admin2);
    IF EXISTS (SELECT 1 FROM public.institution_admin_access WHERE user_id = admin2) THEN
        RAISE EXCEPTION 'Removing the administrator kept the limit';
    END IF;

    -- 7. Audit and privileges.
    IF (SELECT count(*) FROM public.admin_audit_log WHERE action = 'institution.admin.access'
        AND record_id = admin2::text) < 4 THEN
        RAISE EXCEPTION 'Access changes were not audited against the administrator';
    END IF;
    IF NOT has_table_privilege('service_role', 'public.institution_admin_access', 'SELECT')
       OR has_table_privilege('service_role', 'public.institution_admin_access', 'INSERT')
       OR has_function_privilege('service_role', 'public.institution_admin_access_allows(uuid,uuid,text)', 'EXECUTE')
       OR has_function_privilege('authenticated', 'public.set_institution_admin_access(uuid,uuid,uuid,text[])', 'EXECUTE')
       OR NOT has_function_privilege('service_role',
           'public.set_institution_admin_access(uuid,uuid,uuid,text[])', 'EXECUTE') THEN
        RAISE EXCEPTION 'Unexpected access privileges';
    END IF;
    RAISE NOTICE 'admin access contracts passed';
END;
$$;

ROLLBACK;
