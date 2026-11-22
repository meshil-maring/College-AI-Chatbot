-- Class In-Charge and Subject Coordinator contracts. LOCAL database only:
--   psql -f tests/member_management/sql/responsibility_contracts.sql   (rolled back)
\set ON_ERROR_STOP 1
BEGIN;
\ir profile_fixture.sql

-- A class section and courses without building the whole academic chain: FK
-- checks are paused only while inserting these fixture rows.
SET LOCAL session_replication_role = replica;
INSERT INTO public.academic_sections (academic_section_id, institution_id, admission_cohort_id,
    program_semester_id, semester_id, name, code)
VALUES ('0f000000-0000-4000-8000-0000000a0001', member_fixture.id('tenant'), gen_random_uuid(),
        gen_random_uuid(), gen_random_uuid(), 'CSE Year 2 A', 'CSE-2A');
INSERT INTO public.courses (course_id, department_id, name, code)
VALUES ('0f000000-0000-4000-8000-0000000b0001', member_fixture.id('cse'), 'Databases', 'CS201'),
       ('0f000000-0000-4000-8000-0000000b0002', member_fixture.id('b_dept'), 'Other college course', 'OC101');
SET LOCAL session_replication_role = origin;

DO $$
DECLARE
    actor uuid := member_fixture.id('admin');
    tenant uuid := member_fixture.id('tenant');
    section uuid := '0f000000-0000-4000-8000-0000000a0001';
    course uuid := '0f000000-0000-4000-8000-0000000b0001';
    f1 uuid := member_fixture.id('f1');
    f2 uuid := member_fixture.id('f2');
    first_row jsonb;
    result jsonb;
    listed jsonb;
BEGIN
    -- 1. Appoint a Class In-Charge; repeating it changes nothing.
    first_row := public.assign_member_responsibility(actor, tenant, f1, 'class_in_charge', section);
    result := public.assign_member_responsibility(actor, tenant, f1, 'class_in_charge', section);
    IF NOT (result ->> 'already_applied')::boolean
       OR (SELECT count(*) FROM public.member_responsibilities) <> 1 THEN
        RAISE EXCEPTION 'Repeated appointment was not idempotent';
    END IF;

    -- 2. Appointing someone else hands over and keeps the history.
    PERFORM public.assign_member_responsibility(actor, tenant, f2, 'class_in_charge', section,
        current_date - 2, current_date + 90);
    IF (SELECT ended_at IS NULL FROM public.member_responsibilities
        WHERE responsibility_id = (first_row ->> 'responsibility_id')::uuid)
       OR (SELECT faculty_user_id FROM public.member_responsibilities
           WHERE academic_section_id = section AND ended_at IS NULL) <> f2 THEN
        RAISE EXCEPTION 'Handover did not end the earlier Class In-Charge';
    END IF;

    -- 3. Subject Coordinator for a catalogue course of this institution only.
    result := public.assign_member_responsibility(actor, tenant, f1, 'subject_coordinator', course);
    PERFORM member_fixture.expect_error(format(
        'SELECT public.assign_member_responsibility(%L, %L, %L, %L, %L)', actor, tenant, f1,
        'subject_coordinator', '0f000000-0000-4000-8000-0000000b0002'), 'P1301', 'course of another institution');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.assign_member_responsibility(%L, %L, %L, %L, %L)', actor, tenant, f1,
        'class_in_charge', course), 'P1301', 'course used as a section');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.assign_member_responsibility(%L, %L, %L, %L, %L)', actor, tenant,
        member_fixture.id('s1'), 'subject_coordinator', course), 'P1302', 'staff member');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.assign_member_responsibility(%L, %L, %L, %L, %L)', actor, tenant, f1,
        'hod', course), '22023', 'unknown responsibility');
    PERFORM member_fixture.expect_error(format(
        'SELECT public.assign_member_responsibility(%L, %L, %L, %L, %L, %L)', actor, tenant, f1,
        'subject_coordinator', course, current_date + 3), '22023', 'future start');

    -- 4. An expired coordinator is closed when the course is next assigned.
    SET LOCAL session_replication_role = replica;
    UPDATE public.member_responsibilities SET starts_on = current_date - 40, planned_end_on = current_date - 1
    WHERE responsibility_id = (result ->> 'responsibility_id')::uuid;
    SET LOCAL session_replication_role = origin;
    listed := public.read_member_responsibilities(actor, tenant);
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(listed) e
               WHERE e ->> 'course_id' = course::text AND (e ->> 'is_current')::boolean) THEN
        RAISE EXCEPTION 'An expired coordinator is still listed as current';
    END IF;
    PERFORM public.assign_member_responsibility(actor, tenant, f1, 'subject_coordinator', course);
    IF (SELECT count(*) FROM public.member_responsibilities WHERE course_id = course AND ended_at IS NULL) <> 1 THEN
        RAISE EXCEPTION 'Expired coordinator was not closed before reappointment';
    END IF;

    -- 5. Ending is idempotent and tenant-pinned.
    result := public.end_member_responsibility(actor, tenant, (first_row ->> 'responsibility_id')::uuid);
    IF NOT (result ->> 'already_applied')::boolean THEN RAISE EXCEPTION 'Ending twice was not idempotent'; END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.end_member_responsibility(%L, %L, %L)',
        member_fixture.id('admin_b'), member_fixture.id('tenant_b'), first_row ->> 'responsibility_id'),
        'P0002', 'ending another institution''s record');

    -- 6. Labels, audit and access.
    listed := public.read_member_responsibilities(actor, tenant);
    IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(listed) e
                   WHERE e ->> 'target_code' = 'CSE-2A' AND e ->> 'faculty_user_id' = f2::text
                     AND (e ->> 'is_current')::boolean) THEN
        RAISE EXCEPTION 'Listing is missing the current Class In-Charge: %', listed;
    END IF;
    IF (SELECT count(*) FROM public.admin_audit_log WHERE action = 'member.responsibility.assign') < 4 THEN
        RAISE EXCEPTION 'Appointments were not audited';
    END IF;
    PERFORM member_fixture.expect_error(format('SELECT public.read_member_responsibilities(%L, %L)',
        member_fixture.id('admin_b'), tenant), '42501', 'other institution admin');
    IF has_table_privilege('service_role', 'public.member_responsibilities', 'SELECT')
       OR has_function_privilege('authenticated', 'public.read_member_responsibilities(uuid,uuid)', 'EXECUTE')
       OR NOT has_function_privilege('service_role',
           'public.assign_member_responsibility(uuid,uuid,uuid,text,uuid,date,date)', 'EXECUTE') THEN
        RAISE EXCEPTION 'Unexpected responsibility privileges';
    END IF;
    RAISE NOTICE 'responsibility contracts passed';
END;
$$;

ROLLBACK;
