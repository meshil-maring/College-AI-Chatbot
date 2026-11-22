-- Institution Owner and owner-managed administrators. LOCAL database only:
--   psql -f tests/member_management/sql/owner_contracts.sql   (rolled back)
\set ON_ERROR_STOP 1
BEGIN;
\ir profile_fixture.sql

-- A second administrator of institution A (granted after the first).
INSERT INTO public.user_roles (user_id, role_id, scope_type, scope_id, scope_organization_id, assigned_at)
SELECT member_fixture.id('invitee'), id, 'institution', member_fixture.id('tenant'), member_fixture.id('org'),
       now() + interval '1 second'
FROM public.roles WHERE name = 'admin';

DO $$
DECLARE
    owner uuid := member_fixture.id('admin');
    admin2 uuid := member_fixture.id('invitee');
    tenant uuid := member_fixture.id('tenant');
    listed jsonb;
    invitation uuid;
    late uuid;
    new_auth uuid := '0f000000-0000-4000-8000-00000000e101';
    op jsonb;
BEGIN
    -- 1. The first administrator of each institution became its Owner.
    IF (SELECT owner_user_id FROM public.institutions WHERE institution_id = tenant) <> owner
       OR (SELECT owner_user_id FROM public.institutions WHERE institution_id = member_fixture.id('tenant_b'))
          <> member_fixture.id('admin_b') THEN
        RAISE EXCEPTION 'Owners were not set from the first administrator';
    END IF;
    listed := public.read_institution_admins(admin2, tenant);
    IF jsonb_array_length(listed -> 'administrators') <> 2 OR listed ->> 'owner_user_id' <> owner::text THEN
        RAISE EXCEPTION 'Administrator listing is wrong: %', listed;
    END IF;

    -- 2. Only the Owner invites, removes and transfers.
    PERFORM member_fixture.expect_error(format(
        'SELECT public.create_admin_invitation(%L, %L, %L, %L, %L, now() + interval ''1 day'', repeat(''p'', 96))',
        admin2, tenant, 'x@member.test', 'X', repeat('e1', 32)), 'P1401', 'non-owner invites');
    PERFORM member_fixture.expect_error(format('SELECT public.revoke_institution_admin(%L, %L, %L)',
        admin2, tenant, owner), 'P1401', 'non-owner revokes the Owner');
    PERFORM member_fixture.expect_error(format('SELECT public.transfer_institution_ownership(%L, %L, %L)',
        admin2, tenant, admin2), 'P1401', 'non-owner takes ownership');
    PERFORM member_fixture.expect_error(format('SELECT public.read_institution_admins(%L, %L)',
        member_fixture.id('f1'), tenant), '42501', 'faculty reads administrators');

    -- 3. The Owner invites a new administrator; duplicates and members are refused.
    invitation := (public.create_admin_invitation(owner, tenant, 'NewAdmin@member.test', 'New Admin',
        repeat('e2', 32), now() + interval '1 day', repeat('p', 96)) ->> 'invitation_id')::uuid;
    PERFORM member_fixture.expect_error(format(
        'SELECT public.create_admin_invitation(%L, %L, %L, NULL, %L, now() + interval ''1 day'', repeat(''p'', 96))',
        owner, tenant, 'newadmin@member.test', repeat('e3', 32)), 'P1203', 'pending invitation');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.create_admin_invitation(%L, %L, %L, NULL, %L, now() + interval ''1 day'', repeat(''p'', 96))',
        owner, tenant, 'f1@member.test', repeat('e4', 32)), 'P1202', 'existing member');
    IF jsonb_array_length(public.read_institution_admins(owner, tenant) -> 'invitations') <> 1 THEN
        RAISE EXCEPTION 'Pending administrator invitation is not listed';
    END IF;

    -- 4. The invited person accepts through the real flow and becomes an administrator.
    INSERT INTO auth.users (id, email, instance_id, aud, role)
    VALUES (new_auth, 'newadmin@member.test', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated');
    op := public.b05_reserve_invitation('institution', invitation, repeat('e2', 32),
        '0f000000-0000-4000-8000-00000000f101', NULL, NULL);
    IF op IS NULL THEN RAISE EXCEPTION 'Owner invitation could not be reserved'; END IF;
    PERFORM public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f101', 'reserved', 'provider_started', NULL, NULL, NULL, NULL);
    PERFORM public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f101', 'provider_started', 'provider_created', new_auth, NULL, NULL, NULL);
    op := public.b05_advance_invitation_operation('0f000000-0000-4000-8000-00000000f101', 'provider_created', 'user_created', new_auth, NULL, 'New', 'Admin');
    op := public.b05_finalize_invitation('institution', invitation, repeat('e2', 32),
        '0f000000-0000-4000-8000-00000000f101', (op ->> 'user_id')::uuid);
    IF op IS NULL OR jsonb_array_length(public.read_institution_admins(owner, tenant) -> 'administrators') <> 3
       OR (SELECT owner_user_id FROM public.institutions WHERE institution_id = tenant) <> owner THEN
        RAISE EXCEPTION 'Accepting did not add an administrator: %', op;
    END IF;

    -- 5. Removing: never yourself, only administrators; the account stays.
    PERFORM member_fixture.expect_error(format('SELECT public.revoke_institution_admin(%L, %L, %L)',
        owner, tenant, owner), 'P1403', 'Owner removes themselves');
    PERFORM member_fixture.expect_error(format('SELECT public.revoke_institution_admin(%L, %L, %L)',
        owner, tenant, member_fixture.id('f1')), 'P1402', 'removing a non-administrator');
    PERFORM public.revoke_institution_admin(owner, tenant, (SELECT id FROM public.users WHERE email = 'newadmin@member.test'));
    IF jsonb_array_length(public.read_institution_admins(owner, tenant) -> 'administrators') <> 2
       OR NOT EXISTS (SELECT 1 FROM public.users WHERE email = 'newadmin@member.test') THEN
        RAISE EXCEPTION 'Revoking removed the account or kept the role';
    END IF;

    -- 6. An invitation stops working once its sender is no longer the Owner.
    late := (public.create_admin_invitation(owner, tenant, 'late@member.test', NULL,
        repeat('e5', 32), now() + interval '1 day', repeat('p', 96)) ->> 'invitation_id')::uuid;
    PERFORM member_fixture.expect_error(format('SELECT public.transfer_institution_ownership(%L, %L, %L)',
        owner, tenant, member_fixture.id('f1')), 'P1402', 'ownership to a non-administrator');
    PERFORM member_fixture.expect_error(format('UPDATE public.institutions SET owner_user_id = %L WHERE institution_id = %L',
        member_fixture.id('f1'), tenant), 'P1402', 'direct owner change to a non-administrator');
    PERFORM public.transfer_institution_ownership(owner, tenant, admin2);
    PERFORM member_fixture.expect_error(format(
        'SELECT public.b05_reserve_invitation(%L, %L, %L, %L, NULL, NULL)', 'institution', late, repeat('e5', 32),
        '0f000000-0000-4000-8000-00000000f102'), 'P1401', 'invitation from a former Owner');
    PERFORM member_fixture.expect_error(format('SELECT public.cancel_admin_invitation(%L, %L, %L)',
        owner, tenant, late), 'P1401', 'former Owner cancels');
    IF NOT (public.cancel_admin_invitation(admin2, tenant, late) ->> 'cancelled')::boolean THEN
        RAISE EXCEPTION 'The new Owner could not cancel the invitation';
    END IF;

    -- 7. When the Owner loses the admin role elsewhere, ownership passes on.
    DELETE FROM public.user_roles ur USING public.roles r
    WHERE r.id = ur.role_id AND r.name = 'admin' AND ur.user_id = admin2;
    IF (SELECT owner_user_id FROM public.institutions WHERE institution_id = tenant) <> owner THEN
        RAISE EXCEPTION 'Ownership did not pass to the next administrator';
    END IF;

    -- 8. A non-owner invitation still needs a platform super admin as its sender.
    INSERT INTO public.platform_admin_invitations (institution_id, email, token_hash, role_name, status,
        expires_at, created_by, email_delivery_status)
    VALUES (tenant, 'platform@member.test', repeat('e6', 32), 'admin', 'invited', now() + interval '1 day',
        owner, 'pending') RETURNING invitation_id INTO late;
    PERFORM member_fixture.expect_error(format(
        'SELECT public.b05_reserve_invitation(%L, %L, %L, %L, NULL, NULL)', 'institution', late, repeat('e6', 32),
        '0f000000-0000-4000-8000-00000000f103'), '42501', 'super admin invitation sent by an institution admin');
    -- ...and a real platform super admin's invitation still reserves.
    INSERT INTO public.user_roles (user_id, role_id, scope_type)
    SELECT member_fixture.id('s1'), id, 'platform' FROM public.roles WHERE name = 'super_admin';
    UPDATE public.users SET status = 'active' WHERE id = member_fixture.id('s1');
    INSERT INTO public.platform_admin_invitations (institution_id, email, token_hash, role_name, status,
        expires_at, created_by, email_delivery_status)
    VALUES (tenant, 'platform2@member.test', repeat('e7', 32), 'admin', 'invited', now() + interval '1 day',
        member_fixture.id('s1'), 'pending') RETURNING invitation_id INTO late;
    IF public.b05_reserve_invitation('institution', late, repeat('e7', 32),
        '0f000000-0000-4000-8000-00000000f104', NULL, NULL) IS NULL THEN
        RAISE EXCEPTION 'A super admin invitation could no longer be reserved';
    END IF;

    IF has_function_privilege('authenticated', 'public.revoke_institution_admin(uuid,uuid,uuid)', 'EXECUTE')
       OR has_function_privilege('service_role', 'public.institution_owner_assert(uuid,uuid)', 'EXECUTE')
       OR NOT has_function_privilege('service_role',
           'public.create_admin_invitation(uuid,uuid,text,text,text,timestamptz,text,text[],jsonb)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Unexpected owner function privileges';
    END IF;
    RAISE NOTICE 'owner contracts passed';
END;
$$;

ROLLBACK;
