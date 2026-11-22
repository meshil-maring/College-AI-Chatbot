-- Teaching assignment contracts. LOCAL database only:
--   psql -f tests/member_management/sql/teaching_contracts.sql   (rolled back)
-- F1's primary department is CSE. F2 heads Mechanical. Civil has no head.
\set ON_ERROR_STOP 1
BEGIN;
\ir profile_fixture.sql

-- Offerings without the whole academic chain: FK checks and structure triggers
-- are paused only while inserting these fixture rows.
SET LOCAL session_replication_role = replica;
INSERT INTO public.academic_sections (academic_section_id, institution_id, admission_cohort_id,
    program_semester_id, semester_id, name, code)
VALUES ('0f000000-0000-4000-8000-0000000a0001', member_fixture.id('tenant'), gen_random_uuid(),
        gen_random_uuid(), gen_random_uuid(), 'CSE Year 2 A', 'CSE-2A');
INSERT INTO public.courses (course_id, department_id, name, code)
SELECT ('0f000000-0000-4000-8000-0000000b000' || n)::uuid, member_fixture.id(dept), title, code
FROM (VALUES (1, 'cse', 'Databases', 'CS201'), (2, 'mech', 'Thermodynamics', 'ME201'),
             (3, 'mech', 'Machine Design', 'ME202'), (4, 'civil', 'Surveying', 'CE201'),
             (5, 'b_dept', 'Other college', 'OC101')) v(n, dept, title, code);
INSERT INTO public.curriculum_subjects (curriculum_subject_id, institution_id, curriculum_version_id,
    program_semester_id, course_id, subject_code, subject_name, course_type)
SELECT ('0f000000-0000-4000-8000-0000000c000' || n)::uuid,
       member_fixture.id(CASE WHEN n = 5 THEN 'tenant_b' ELSE 'tenant' END), gen_random_uuid(),
       gen_random_uuid(), ('0f000000-0000-4000-8000-0000000b000' || n)::uuid, 'S' || n, 'Subject ' || n, 'core'
FROM generate_series(1, 5) n;
INSERT INTO public.academic_offerings (academic_offering_id, institution_id, academic_section_id,
    curriculum_subject_id)
SELECT ('0f000000-0000-4000-8000-0000000e000' || n)::uuid,
       member_fixture.id(CASE WHEN n = 5 THEN 'tenant_b' ELSE 'tenant' END),
       '0f000000-0000-4000-8000-0000000a0001', ('0f000000-0000-4000-8000-0000000c000' || n)::uuid
FROM generate_series(1, 5) n;
SET LOCAL session_replication_role = origin;
INSERT INTO public.department_heads (institution_id, department_id, faculty_user_id, assigned_by)
VALUES (member_fixture.id('tenant'), member_fixture.id('mech'), member_fixture.id('f2'), member_fixture.id('admin'));

CREATE FUNCTION member_fixture.offering(n int) RETURNS uuid LANGUAGE sql IMMUTABLE AS $$
    SELECT ('0f000000-0000-4000-8000-0000000e000' || n)::uuid;
$$;

DO $$
DECLARE
    admin uuid := member_fixture.id('admin');
    tenant uuid := member_fixture.id('tenant');
    f1 uuid := member_fixture.id('f1');
    f2 uuid := member_fixture.id('f2');
    home jsonb; cross_row jsonb; own_row jsonb; civil_row jsonb; result jsonb; listed jsonb;
BEGIN
    -- 1. Teaching in the teacher's own department is active at once and idempotent.
    home := public.request_teaching_assignment(admin, tenant, member_fixture.offering(1), f1);
    result := public.request_teaching_assignment(admin, tenant, member_fixture.offering(1), f1);
    IF home ->> 'status' <> 'active' OR (home ->> 'needs_approval')::boolean
       OR NOT (result ->> 'already_applied')::boolean THEN
        RAISE EXCEPTION 'Home-department assignment: % then %', home, result;
    END IF;

    -- 2. Cross-department waits for the receiving HOD; an admin cannot skip a head.
    cross_row := public.request_teaching_assignment(admin, tenant, member_fixture.offering(2), f1);
    IF cross_row ->> 'status' <> 'pending' THEN RAISE EXCEPTION 'Cross-department was not pending'; END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.decide_teaching_assignment(%L, %L, %L, true)',
        admin, tenant, cross_row ->> 'assignment_id'), 'P1503', 'admin approving while a head exists');
    PERFORM member_fixture.expect_error(format('SELECT public.decide_teaching_assignment(%L, %L, %L, false, %L)',
        f2, tenant, cross_row ->> 'assignment_id', '  '), 'P1506', 'rejection without a reason');
    result := public.decide_teaching_assignment(f2, tenant, (cross_row ->> 'assignment_id')::uuid, true);
    IF result ->> 'status' <> 'active' OR (result ->> 'decided_by')::uuid <> f2 THEN
        RAISE EXCEPTION 'HOD approval failed: %', result;
    END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.decide_teaching_assignment(%L, %L, %L, false, %L)',
        f2, tenant, cross_row ->> 'assignment_id', 'Too late'), 'P1504', 'deciding twice');

    -- 3. The receiving HOD's own assignment needs no approval; outside their scope is refused.
    result := public.request_teaching_assignment(f2, tenant, member_fixture.offering(3), f1);
    IF result ->> 'status' <> 'active' THEN RAISE EXCEPTION 'Receiving HOD assignment was not active'; END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.request_teaching_assignment(%L, %L, %L, %L)',
        f2, tenant, member_fixture.offering(4), f1), 'P1503', 'HOD assigning outside their departments');

    -- 4. A head never approves their own teaching; with no other head an admin may.
    own_row := public.request_teaching_assignment(admin, tenant, member_fixture.offering(2), f2);
    PERFORM member_fixture.expect_error(format('SELECT public.decide_teaching_assignment(%L, %L, %L, true)',
        f2, tenant, own_row ->> 'assignment_id'), 'P1503', 'head approving own teaching');
    result := public.decide_teaching_assignment(admin, tenant, (own_row ->> 'assignment_id')::uuid, false, 'Timetable clash');
    IF result ->> 'status' <> 'rejected' OR result ->> 'decision_note' <> 'Timetable clash' THEN
        RAISE EXCEPTION 'Admin rejection failed: %', result;
    END IF;
    civil_row := public.request_teaching_assignment(admin, tenant, member_fixture.offering(4), f1);
    result := public.decide_teaching_assignment(admin, tenant, (civil_row ->> 'assignment_id')::uuid, true);
    IF result ->> 'status' <> 'active' THEN RAISE EXCEPTION 'Admin approval without a head failed'; END IF;

    -- 5. Inputs are checked.
    PERFORM member_fixture.expect_error(format('SELECT public.request_teaching_assignment(%L, %L, %L, %L)',
        admin, tenant, member_fixture.offering(5), f1), 'P1501', 'offering of another institution');
    PERFORM member_fixture.expect_error(format('SELECT public.request_teaching_assignment(%L, %L, %L, %L)',
        admin, tenant, member_fixture.offering(1), member_fixture.id('s1')), 'P1502', 'staff member');
    PERFORM member_fixture.expect_error(format('SELECT public.request_teaching_assignment(%L, %L, %L, %L, NULL, %L)',
        admin, tenant, member_fixture.offering(1), f2, current_date - 1), 'P1505', 'planned end in the past');
    PERFORM member_fixture.expect_error(format('SELECT public.read_teaching_assignments(%L, %L)',
        f1, tenant), '42501', 'faculty who is not a head');
    PERFORM member_fixture.expect_error(format('SELECT public.read_teaching_assignments(%L, %L)',
        member_fixture.id('admin_b'), tenant), '42501', 'other institution admin');

    -- 6. A head sees their department and their requests, not other departments.
    listed := public.read_teaching_assignments(f2, tenant) -> 'assignments';
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(listed) e WHERE e ->> 'subject_code' IN ('S1', 'S4'))
       OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(listed) e WHERE e ->> 'subject_code' = 'S2') THEN
        RAISE EXCEPTION 'HOD listing has the wrong scope: %', listed;
    END IF;
    listed := public.read_teaching_assignments(admin, tenant) -> 'assignments';
    IF jsonb_array_length(listed) <> 5 THEN RAISE EXCEPTION 'Admin listing: %', listed; END IF;
    IF jsonb_array_length(public.read_teaching_options(f2, tenant) -> 'offerings') <> 4 THEN
        RAISE EXCEPTION 'Options must list this institution''s four offerings';
    END IF;

    -- 7. Ending keeps the row, is idempotent and tenant-pinned.
    result := public.end_teaching_assignment(admin, tenant, (home ->> 'assignment_id')::uuid);
    IF result ->> 'status' <> 'ended' THEN RAISE EXCEPTION 'End failed: %', result; END IF;
    result := public.end_teaching_assignment(admin, tenant, (home ->> 'assignment_id')::uuid);
    IF NOT (result ->> 'already_applied')::boolean THEN RAISE EXCEPTION 'Ending twice was not idempotent'; END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.end_teaching_assignment(%L, %L, %L)',
        f2, tenant, civil_row ->> 'assignment_id'), 'P1503', 'HOD ending another department''s teaching');
    PERFORM member_fixture.expect_error(format('SELECT public.end_teaching_assignment(%L, %L, %L)',
        member_fixture.id('admin_b'), member_fixture.id('tenant_b'), home ->> 'assignment_id'),
        'P0002', 'ending another institution''s record');
    result := public.request_teaching_assignment(admin, tenant, member_fixture.offering(1), f1);
    IF result ->> 'status' <> 'active' OR (result ->> 'already_applied')::boolean THEN
        RAISE EXCEPTION 'Reassigning after an end failed: %', result;
    END IF;

    -- 8. Audit and privileges.
    IF (SELECT count(*) FROM public.admin_audit_log WHERE action LIKE 'teaching.assignment.%'
        AND record_data ->> 'faculty_user_id' = f1::text) < 7 THEN
        RAISE EXCEPTION 'Teaching changes were not audited against the teacher';
    END IF;
    IF has_table_privilege('service_role', 'public.teaching_assignments', 'SELECT')
       OR has_function_privilege('service_role', 'public.teaching_actor(uuid,uuid)', 'EXECUTE')
       OR has_function_privilege('authenticated', 'public.read_teaching_assignments(uuid,uuid)', 'EXECUTE')
       OR NOT has_function_privilege('service_role',
           'public.request_teaching_assignment(uuid,uuid,uuid,uuid,date,date)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Unexpected teaching privileges';
    END IF;
    RAISE NOTICE 'teaching contracts passed';
END;
$$;

ROLLBACK;
