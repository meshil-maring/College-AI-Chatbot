-- Staff/Faculty invitation contracts: profile validation at creation and the
-- real reserve -> finalize acceptance for a new and an existing account.
-- Run against a LOCAL database only (see profile_contracts.sql); rolled back.
\set ON_ERROR_STOP 1
BEGIN;
\ir profile_fixture.sql

CREATE FUNCTION member_fixture.invite(p_email text, p_role text, p_profile jsonb, p_hash text)
RETURNS uuid LANGUAGE sql AS $$
    SELECT (public.create_member_invitation(member_fixture.id('admin'), member_fixture.id('tenant'),
        p_email, 'Invited Person', p_role, member_fixture.id('cse'), p_hash,
        now() + interval '7 days', repeat('p', 96), p_profile) ->> 'invitation_id')::uuid;
$$;

DO $$
DECLARE
    tenant uuid := member_fixture.id('tenant');
    hash_a text := repeat('a1', 32);
    hash_b text := repeat('b2', 32);
    new_auth uuid := '0f000000-0000-4000-8000-00000000e001';
    accept_a uuid := '0f000000-0000-4000-8000-00000000f001';
    accept_b uuid := '0f000000-0000-4000-8000-00000000f002';
    accept_c uuid := '0f000000-0000-4000-8000-00000000f003';
    profile jsonb;
    invitation_a uuid;
    invitation_b uuid;
    invitation_c uuid;
    new_user uuid;
    op jsonb;
BEGIN
    PERFORM public.save_member_profile(member_fixture.id('admin'), tenant, member_fixture.id('f1'),
        member_fixture.faculty('EMP-001'));

    -- 1. Creation rejects an employee ID used by a member, and repeated departments.
    PERFORM member_fixture.expect_error(format('SELECT member_fixture.invite(%L, %L, member_fixture.faculty(%L), %L)',
        'dup@member.test', 'faculty', 'emp-001', hash_a), 'P1204', 'employee ID of a member');
    PERFORM member_fixture.expect_error(format('SELECT member_fixture.invite(%L, %L, %L::jsonb, %L)',
        'dup@member.test', 'faculty', member_fixture.faculty('EMP-100')
            || jsonb_build_object('additional_department_ids', jsonb_build_array(member_fixture.id('cse'))),
        hash_a), '22023', 'primary repeated as additional');
    PERFORM member_fixture.expect_error(format('SELECT member_fixture.invite(%L, %L, member_fixture.staff(%L), %L)',
        'dup@member.test', 'faculty', 'EMP-100', hash_a), '22023', 'profile for another role');

    -- 2. A new person: profile with two additional departments, one later retired.
    profile := member_fixture.faculty('EMP-100') || jsonb_build_object('additional_department_ids',
        jsonb_build_array(member_fixture.id('mech'), member_fixture.id('civil')));
    invitation_a := member_fixture.invite('NewHire@member.test', 'faculty', profile, hash_a);
    IF (SELECT invited_profile FROM public.platform_admin_invitations WHERE invitation_id = invitation_a) <> profile THEN
        RAISE EXCEPTION 'Invited profile was not stored';
    END IF;
    PERFORM member_fixture.expect_error(format(
        'UPDATE public.platform_admin_invitations SET invited_profile = NULL WHERE invitation_id = %L',
        invitation_a), '23514', 'invited profile is immutable');
    -- A pending invitation reserves its employee ID too.
    PERFORM member_fixture.expect_error(format('SELECT member_fixture.invite(%L, %L, member_fixture.staff(%L), %L)',
        'other@member.test', 'staff', 'emp-100', hash_b), 'P1204', 'employee ID of a pending invitation');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, member_fixture.faculty(%L))',
        member_fixture.id('admin'), tenant, member_fixture.id('f2'), 'EMP-100'),
        'P1204', 'member profile reusing a pending invitation employee ID');
    UPDATE public.departments SET is_active = false WHERE department_id = member_fixture.id('civil');

    -- 3. Accept as a new account through the real reserve/advance/finalize flow.
    INSERT INTO auth.users (id, email, instance_id, aud, role)
    VALUES (new_auth, 'newhire@member.test', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated');
    op := public.b05_reserve_invitation('institution', invitation_a, hash_a, accept_a, NULL, NULL);
    IF op IS NULL OR op ->> 'stage' <> 'reserved' THEN RAISE EXCEPTION 'Reservation failed: %', op; END IF;
    PERFORM public.b05_advance_invitation_operation(accept_a, 'reserved', 'provider_started', NULL, NULL, NULL, NULL);
    PERFORM public.b05_advance_invitation_operation(accept_a, 'provider_started', 'provider_created', new_auth, NULL, NULL, NULL);
    op := public.b05_advance_invitation_operation(accept_a, 'provider_created', 'user_created', new_auth, NULL, 'New', 'Hire');
    new_user := (op ->> 'user_id')::uuid;
    op := public.b05_finalize_invitation('institution', invitation_a, hash_a, accept_a, new_user);
    IF op IS NULL OR NOT (op ->> 'accepted')::boolean THEN RAISE EXCEPTION 'Finalization failed: %', op; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.institution_member_profiles
                   WHERE institution_id = tenant AND user_id = new_user AND employee_id = 'EMP-100')
       OR NOT EXISTS (SELECT 1 FROM public.faculty_profiles WHERE user_id = new_user)
       OR NOT EXISTS (SELECT 1 FROM public.institution_member_departments
                      WHERE user_id = new_user AND department_id = member_fixture.id('cse'))
       OR ARRAY(SELECT department_id FROM public.institution_member_additional_departments WHERE user_id = new_user)
          <> ARRAY[member_fixture.id('mech')]
       OR public.member_profile_role(tenant, new_user) <> 'faculty' THEN
        RAISE EXCEPTION 'Acceptance did not apply the role, departments and profile';
    END IF;
    -- Finalizing again is idempotent and writes nothing more.
    op := public.b05_finalize_invitation('institution', invitation_a, hash_a, accept_a, new_user);
    IF NOT (op ->> 'already_applied')::boolean THEN RAISE EXCEPTION 'Repeat finalization was not idempotent'; END IF;

    -- 4. An existing account (registered elsewhere) accepts a Staff invitation.
    invitation_b := member_fixture.invite('invitee@member.test', 'staff', member_fixture.staff('STF-200'), hash_b);
    op := public.b05_reserve_invitation('institution', invitation_b, hash_b, accept_b,
        member_fixture.id('invitee'), member_fixture.id('invitee'));
    IF op IS NULL OR op ->> 'stage' <> 'user_created' THEN RAISE EXCEPTION 'Existing-account reservation failed'; END IF;
    PERFORM public.b05_finalize_invitation('institution', invitation_b, hash_b, accept_b, member_fixture.id('invitee'));
    IF (SELECT responsibilities FROM public.staff_profiles WHERE user_id = member_fixture.id('invitee'))
       <> ARRAY['Admissions desk'] THEN
        RAISE EXCEPTION 'Existing account did not receive the staff profile';
    END IF;

    -- 5. An invitation without a profile still works and creates no profile.
    UPDATE public.users SET email = 'plain@member.test' WHERE id = member_fixture.id('f2');
    DELETE FROM public.user_roles WHERE user_id = member_fixture.id('f2');
    invitation_c := member_fixture.invite('plain@member.test', 'faculty', NULL, repeat('c3', 32));
    PERFORM public.b05_reserve_invitation('institution', invitation_c, repeat('c3', 32), accept_c,
        member_fixture.id('f2'), member_fixture.id('f2'));
    PERFORM public.b05_finalize_invitation('institution', invitation_c, repeat('c3', 32), accept_c, member_fixture.id('f2'));
    IF public.member_profile_role(tenant, member_fixture.id('f2')) <> 'faculty'
       OR EXISTS (SELECT 1 FROM public.institution_member_profiles WHERE user_id = member_fixture.id('f2')) THEN
        RAISE EXCEPTION 'Invitation without a profile changed behavior';
    END IF;
END;
$$;

-- 6. Self-service invitations (not admin_invited) still need an approved request.
DO $$
DECLARE invitation uuid;
BEGIN
    INSERT INTO public.platform_admin_invitations (institution_id, email, token_hash, role_name, status,
        expires_at, created_by, email_delivery_status)
    VALUES (member_fixture.id('tenant'), 'selfservice@member.test', repeat('d4', 32), 'staff', 'invited',
        now() + interval '1 day', member_fixture.id('admin'), 'pending')
    RETURNING invitation_id INTO invitation;
    IF public.b05_reserve_invitation('institution', invitation, repeat('d4', 32),
        '0f000000-0000-4000-8000-00000000f004', NULL, NULL) IS NOT NULL THEN
        RAISE EXCEPTION 'Self-service invitation was reserved without an approved request';
    END IF;
    RAISE NOTICE 'member invitation contracts passed';
END;
$$;

ROLLBACK;
