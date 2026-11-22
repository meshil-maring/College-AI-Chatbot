-- Member profile and department contracts. Run against a LOCAL database only:
--   docker exec -i supabase_db_CollegeAIChatbot psql -U postgres -v ON_ERROR_STOP=1 \
--     < backend/tests/member_management/sql/profile_contracts.sql
-- (\ir needs the file path, so from backend/: psql -f tests/member_management/sql/profile_contracts.sql)
-- Everything runs in one transaction and is rolled back.
\set ON_ERROR_STOP 1
BEGIN;
\ir profile_fixture.sql

DO $$
DECLARE
    actor uuid := member_fixture.id('admin');
    tenant uuid := member_fixture.id('tenant');
    f1 uuid := member_fixture.id('f1');
    s1 uuid := member_fixture.id('s1');
    audit_before bigint;
    result jsonb;
BEGIN
    -- 1. An administrator saves a Faculty profile; the save is audited once.
    SELECT count(*) INTO audit_before FROM public.admin_audit_log;
    result := public.save_member_profile(actor, tenant, f1, member_fixture.faculty('EMP-001'));
    IF result ->> 'role' <> 'faculty' THEN RAISE EXCEPTION 'Saved role is wrong: %', result; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.institution_member_profiles
                   WHERE institution_id = tenant AND user_id = f1 AND employee_id = 'EMP-001'
                     AND designation = 'Assistant Professor' AND created_by = actor)
       OR NOT EXISTS (SELECT 1 FROM public.faculty_profiles
                      WHERE user_id = f1 AND employment_type = 'permanent' AND experience_years = 6.5) THEN
        RAISE EXCEPTION 'Faculty profile was not written';
    END IF;
    IF (SELECT count(*) FROM public.admin_audit_log WHERE action = 'member.profile.saved') <> 1
       OR (SELECT count(*) FROM public.admin_audit_log) <> audit_before + 1 THEN
        RAISE EXCEPTION 'Profile save was not audited exactly once';
    END IF;

    -- 2. Saving again updates in place and keeps the creator.
    PERFORM public.save_member_profile(actor, tenant, f1,
        jsonb_set(member_fixture.faculty('EMP-001'), '{common,designation}', '"Associate Professor"'));
    IF (SELECT count(*) FROM public.institution_member_profiles WHERE user_id = f1) <> 1
       OR (SELECT designation FROM public.institution_member_profiles WHERE user_id = f1) <> 'Associate Professor' THEN
        RAISE EXCEPTION 'Profile update did not replace the row';
    END IF;

    -- 3. Staff profile with responsibilities and a contract end date.
    PERFORM public.save_member_profile(actor, tenant, s1, member_fixture.staff('STF-001'));
    IF (SELECT responsibilities FROM public.staff_profiles WHERE user_id = s1) <> ARRAY['Admissions desk'] THEN
        RAISE EXCEPTION 'Staff responsibilities were not written';
    END IF;

    -- 4. Employee IDs are unique per institution, ignoring case.
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, member_fixture.faculty(%L))',
        actor, tenant, member_fixture.id('f2'), 'emp-001'), 'P1204', 'duplicate employee ID');

    -- 5. The profile must match the member's role and include an employee ID.
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, member_fixture.staff(%L))',
        actor, tenant, f1, 'EMP-777'), '22023', 'staff details for a faculty member');
    -- 6. Non-permanent employment requires a contract end date.
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, %L::jsonb)', actor, tenant, f1,
        jsonb_set(member_fixture.faculty('EMP-001'), '{faculty,employment_type}', '"temporary"')),
        '23514', 'temporary faculty without contract end');

    -- 7. Only members of the institution, and only its administrators.
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, member_fixture.faculty(%L))',
        actor, tenant, member_fixture.id('invitee'), 'EMP-900'), 'P1205', 'non-member');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, member_fixture.faculty(%L))',
        member_fixture.id('admin_b'), tenant, f1, 'EMP-901'), '42501', 'other institution admin');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, member_fixture.faculty(%L))',
        f1, tenant, member_fixture.id('f2'), 'EMP-902'), '42501', 'faculty actor');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, member_fixture.faculty(%L))',
        member_fixture.id('admin_b'), member_fixture.id('tenant_b'), f1, 'EMP-903'),
        'P1205', 'member of another institution');

    -- 8. Additional departments: set, replace, and validate.
    PERFORM public.set_member_additional_departments(actor, tenant, f1,
        ARRAY[member_fixture.id('mech'), member_fixture.id('civil')]);
    PERFORM public.set_member_additional_departments(actor, tenant, f1, ARRAY[member_fixture.id('mech')]);
    IF ARRAY(SELECT department_id FROM public.institution_member_additional_departments WHERE user_id = f1)
       <> ARRAY[member_fixture.id('mech')] THEN
        RAISE EXCEPTION 'Additional departments were not replaced';
    END IF;
    PERFORM member_fixture.expect_error(format(
        'SELECT public.set_member_additional_departments(%L, %L, %L, ARRAY[%L]::uuid[])',
        actor, tenant, f1, member_fixture.id('cse')), '22023', 'primary repeated as additional');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.set_member_additional_departments(%L, %L, %L, ARRAY[%L]::uuid[])',
        actor, tenant, f1, member_fixture.id('retired')), 'P1201', 'inactive department');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.set_member_additional_departments(%L, %L, %L, ARRAY[%L]::uuid[])',
        actor, tenant, f1, member_fixture.id('b_dept')), 'P1201', 'other institution department');

    -- 9. Making an additional department primary removes it from the additional list.
    UPDATE public.institution_member_departments SET department_id = member_fixture.id('mech')
    WHERE institution_id = tenant AND user_id = f1;
    IF EXISTS (SELECT 1 FROM public.institution_member_additional_departments
               WHERE user_id = f1 AND department_id = member_fixture.id('mech')) THEN
        RAISE EXCEPTION 'New primary department is still listed as additional';
    END IF;

    -- 10. A department in use cannot be deleted.
    PERFORM public.set_member_additional_departments(actor, tenant, f1, ARRAY[member_fixture.id('civil')]);
    PERFORM member_fixture.expect_error(format('DELETE FROM public.departments WHERE department_id = %L',
        member_fixture.id('civil')), '23503', 'deleting an additional department in use');

    -- 11. Suspended is an account status that is not active.
    UPDATE public.users SET status = 'suspended' WHERE id = s1;
    PERFORM member_fixture.expect_error(format(
        'SELECT public.save_member_profile(%L, %L, %L, member_fixture.staff(%L))',
        s1, tenant, f1, 'X'), '42501', 'suspended account cannot act');
    PERFORM member_fixture.expect_error(format('UPDATE public.users SET status = %L WHERE id = %L',
        'paused', s1), '23514', 'unknown account status');
END;
$$;

-- 12. Only the backend service role reaches the tables and commands.
DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY['institution_member_profiles', 'faculty_profiles',
        'staff_profiles', 'institution_member_additional_departments'] LOOP
        IF has_table_privilege('anon', 'public.' || relation_name, 'SELECT')
           OR has_table_privilege('authenticated', 'public.' || relation_name, 'SELECT')
           OR has_table_privilege('service_role', 'public.' || relation_name, 'INSERT')
           OR NOT has_table_privilege('service_role', 'public.' || relation_name, 'SELECT') THEN
            RAISE EXCEPTION 'Unexpected table privileges on %', relation_name;
        END IF;
    END LOOP;
    IF has_function_privilege('authenticated', 'public.save_member_profile(uuid,uuid,uuid,jsonb)', 'EXECUTE')
       OR has_function_privilege('anon', 'public.set_member_additional_departments(uuid,uuid,uuid,uuid[])', 'EXECUTE')
       OR has_function_privilege('service_role', 'public.member_profile_apply(uuid,uuid,text,jsonb,uuid,uuid)', 'EXECUTE')
       OR NOT has_function_privilege('service_role', 'public.save_member_profile(uuid,uuid,uuid,jsonb)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Unexpected function privileges';
    END IF;
    RAISE NOTICE 'member profile contracts passed';
END;
$$;

ROLLBACK;
