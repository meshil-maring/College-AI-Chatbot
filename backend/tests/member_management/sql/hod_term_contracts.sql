-- Head of Department terms and the multi-department policy. LOCAL database only:
--   psql -f tests/member_management/sql/hod_term_contracts.sql   (rolled back)
\set ON_ERROR_STOP 1
BEGIN;
\ir profile_fixture.sql

-- Simulate time passing: move a term into the past without the insert guard.
CREATE FUNCTION member_fixture.expire_head(p_faculty uuid, p_department uuid) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    SET LOCAL session_replication_role = replica;
    UPDATE public.department_heads SET starts_on = current_date - 30, planned_end_on = current_date - 1
    WHERE faculty_user_id = p_faculty AND department_id = p_department AND ended_at IS NULL;
    SET LOCAL session_replication_role = origin;
END;
$$;

DO $$
DECLARE
    actor uuid := member_fixture.id('admin');
    tenant uuid := member_fixture.id('tenant');
    cse uuid := member_fixture.id('cse');
    mech uuid := member_fixture.id('mech');
    f1 uuid := member_fixture.id('f1');
    f2 uuid := member_fixture.id('f2');
    heads jsonb;
BEGIN
    -- 1. An appointment with a backdated start and a planned end is current.
    PERFORM public.add_department_head(actor, tenant, cse, f1, current_date - 10, current_date + 30);
    heads := public.read_department_heads(actor, tenant);
    IF heads -> 'heads' -> 0 ->> 'starts_on' <> (current_date - 10)::text
       OR heads -> 'heads' -> 0 ->> 'planned_end_on' <> (current_date + 30)::text
       OR NOT (heads ->> 'allow_multi_department_hod')::boolean THEN
        RAISE EXCEPTION 'Term or policy missing from the heads view: %', heads;
    END IF;
    IF NOT cse = ANY (public.transfer_hod_departments(f1, tenant)) THEN
        RAISE EXCEPTION 'A current head has no HOD authority';
    END IF;

    -- 2. Terms are validated.
    PERFORM member_fixture.expect_error(format('SELECT public.add_department_head(%L, %L, %L, %L, %L)',
        actor, tenant, mech, f2, current_date + 1), 'P1115', 'future start');
    PERFORM member_fixture.expect_error(format('SELECT public.add_department_head(%L, %L, %L, %L, %L, %L)',
        actor, tenant, mech, f2, current_date - 5, current_date - 1), 'P1115', 'planned end already passed');

    -- 3. A term that ran out grants no authority and is closed on the next change.
    PERFORM member_fixture.expire_head(f1, cse);
    IF cse = ANY (public.transfer_hod_departments(f1, tenant))
       OR cardinality(public.department_head_ids(tenant, cse)) <> 0
       OR jsonb_array_length(public.read_department_heads(actor, tenant) -> 'heads') <> 0 THEN
        RAISE EXCEPTION 'An expired appointment still counts as current';
    END IF;
    PERFORM public.add_department_head(actor, tenant, cse, f1);
    IF (SELECT count(*) FROM public.department_heads WHERE department_id = cse AND faculty_user_id = f1) <> 2
       OR (SELECT count(*) FROM public.department_heads
           WHERE department_id = cse AND faculty_user_id = f1 AND ended_at IS NULL) <> 1
       OR NOT EXISTS (SELECT 1 FROM public.admin_audit_log WHERE action = 'academic.department.head.expired') THEN
        RAISE EXCEPTION 'Re-appointment did not close the expired term and keep history';
    END IF;

    -- 4. Changing the term of a current head is audited; non-heads are rejected.
    PERFORM public.set_department_head_term(actor, tenant, cse, f1, current_date - 3, current_date + 60);
    IF (SELECT planned_end_on FROM public.department_heads
        WHERE department_id = cse AND faculty_user_id = f1 AND ended_at IS NULL) <> current_date + 60
       OR NOT EXISTS (SELECT 1 FROM public.admin_audit_log WHERE action = 'academic.department.head.term') THEN
        RAISE EXCEPTION 'Term change was not saved and audited';
    END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.set_department_head_term(%L, %L, %L, %L, %L, NULL)',
        actor, tenant, mech, f1, current_date), 'P1110', 'term of a non-head');

    -- 5. With the policy off, a head cannot take another department; existing ones stay.
    PERFORM public.add_department_head(actor, tenant, mech, f2);
    PERFORM public.add_department_head(actor, tenant, cse, f2);
    PERFORM public.set_department_head_policy(actor, tenant, false);
    IF NOT f2 = ANY (public.department_head_ids(tenant, mech))
       OR NOT f2 = ANY (public.department_head_ids(tenant, cse)) THEN
        RAISE EXCEPTION 'Switching the policy off removed an existing appointment';
    END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.add_department_head(%L, %L, %L, %L)',
        actor, tenant, mech, f1), 'P1114', 'second department with the policy off');
    PERFORM member_fixture.expect_error(format('SELECT public.assign_department_head(%L, %L, %L, %L)',
        actor, tenant, mech, f1), 'P1114', 'single-head command with the policy off');
    PERFORM public.set_department_head_policy(actor, tenant, true);
    PERFORM public.add_department_head(actor, tenant, mech, f1);
    IF NOT f1 = ANY (public.department_head_ids(tenant, mech)) THEN
        RAISE EXCEPTION 'Policy could not be switched back on';
    END IF;

    -- 6. Only the institution's administrators manage terms and the policy.
    PERFORM member_fixture.expect_error(format('SELECT public.set_department_head_policy(%L, %L, false)',
        member_fixture.id('admin_b'), tenant), '42501', 'other institution admin');
    PERFORM member_fixture.expect_error(format('SELECT public.set_department_head_term(%L, %L, %L, %L, %L, NULL)',
        f1, tenant, cse, f1, current_date), '42501', 'faculty changing a term');
    IF has_function_privilege('authenticated', 'public.set_department_head_policy(uuid,uuid,boolean)', 'EXECUTE')
       OR has_function_privilege('service_role', 'public.department_head_in_effect(timestamptz,date)', 'EXECUTE')
       OR NOT has_function_privilege('service_role',
           'public.add_department_head(uuid,uuid,uuid,uuid,date,date)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Unexpected HOD function privileges';
    END IF;
    RAISE NOTICE 'hod term contracts passed';
END;
$$;

ROLLBACK;
