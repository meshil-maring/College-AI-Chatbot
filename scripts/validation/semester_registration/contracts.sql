BEGIN;
SET LOCAL request.jwt.claim.role='service_role';
DO $$
DECLARE actor uuid:=workspace_fixture.id('admin'); tenant uuid:=workspace_fixture.id('tenant');
    reg1 uuid:=workspace_fixture.id('reg_assignment_1'); reg2 uuid:=workspace_fixture.id('reg_assignment_2');
    option1 uuid:=workspace_fixture.id('reg_option_1'); option2 uuid:=workspace_fixture.id('reg_option_2');
    response jsonb; before_count integer;
BEGIN
    response:=public.read_student_semesters(workspace_fixture.id('reg_user_1'),tenant);
    IF jsonb_array_length(response->'items')<>1 OR jsonb_array_length(response->'items'->0->'groups')<>1 THEN
        RAISE EXCEPTION 'Student read did not expose the assigned semester and options';
    END IF;
    BEGIN
        PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_4'),workspace_fixture.id('foreign_tenant'),reg1,ARRAY[option1]);
        RAISE EXCEPTION 'Cross-tenant registration accepted';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
        PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_1'),tenant,reg1,ARRAY[option1,option2]);
        RAISE EXCEPTION 'Both options accepted';
    EXCEPTION WHEN SQLSTATE 'P1003' THEN NULL; END;
    BEGIN
        PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_1'),tenant,reg1,'{}');
        RAISE EXCEPTION 'Missing option accepted';
    EXCEPTION WHEN SQLSTATE 'P1003' THEN NULL; END;
    BEGIN
        PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_1'),tenant,reg2,ARRAY[option1]);
        RAISE EXCEPTION 'Another student assignment accepted';
    EXCEPTION WHEN no_data_found THEN NULL; END;
    BEGIN
        PERFORM public.manage_curriculum_choice_group(actor,tenant,workspace_fixture.id('reg_group'),'{}',true);
        RAISE EXCEPTION 'Published options were changed';
    EXCEPTION WHEN check_violation THEN NULL; END;
    PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_1'),tenant,reg1,ARRAY[option1]);
    IF (SELECT count(*) FROM public.student_offering_enrollments WHERE semester_registration_id=reg1)<>5 THEN
        RAISE EXCEPTION 'Option 1 did not enroll exactly two common and three option subjects';
    END IF;
    IF EXISTS(SELECT 1 FROM public.student_offering_enrollments WHERE semester_registration_id=reg1
        AND academic_offering_id IN (workspace_fixture.id('reg_offering_6'),workspace_fixture.id('reg_offering_7'),workspace_fixture.id('reg_offering_8'))) THEN
        RAISE EXCEPTION 'Subjects from the other option leaked into enrollment';
    END IF;
    PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_1'),tenant,reg1,ARRAY[option1]);
    IF (SELECT count(*) FROM public.student_offering_enrollments WHERE semester_registration_id=reg1)<>5 THEN
        RAISE EXCEPTION 'Retry created duplicate enrollments';
    END IF;
    PERFORM public.manage_academic_structure_record(actor,tenant,'academic_offerings',workspace_fixture.id('reg_offering_8'),'{"is_active":false}');
    BEGIN
        PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_2'),tenant,reg2,ARRAY[option2]);
        RAISE EXCEPTION 'Incomplete offering set accepted';
    EXCEPTION WHEN SQLSTATE 'P1001' THEN NULL; END;
    IF EXISTS(SELECT 1 FROM public.student_offering_enrollments WHERE semester_registration_id=reg2) THEN
        RAISE EXCEPTION 'Failed registration left partial enrollments';
    END IF;
    PERFORM public.manage_academic_structure_record(actor,tenant,'academic_offerings',workspace_fixture.id('reg_offering_8'),'{"is_active":true}');
    PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_2'),tenant,reg2,ARRAY[option2]);
    IF (SELECT count(*) FROM public.student_offering_enrollments WHERE semester_registration_id=reg2)<>5 THEN
        RAISE EXCEPTION 'Option 2 did not enroll exactly five subjects';
    END IF;
    BEGIN
        PERFORM public.complete_student_semester(workspace_fixture.id('reg_user_3'),tenant,workspace_fixture.id('reg_assignment_3'),ARRAY[option2]);
        RAISE EXCEPTION 'Capacity exceeded';
    EXCEPTION WHEN SQLSTATE 'P1002' THEN NULL; END;
    IF EXISTS(SELECT 1 FROM public.student_offering_enrollments WHERE semester_registration_id=workspace_fixture.id('reg_assignment_3')) THEN
        RAISE EXCEPTION 'Capacity failure left partial enrollments';
    END IF;
    BEGIN
        PERFORM public.manage_academic_structure_record(actor,tenant,'academic_offerings',workspace_fixture.id('reg_offering_1'),'{"capacity":1}');
        RAISE EXCEPTION 'Capacity reduced below enrolled count';
    EXCEPTION WHEN check_violation THEN NULL; END;
    PERFORM public.manage_academic_master_record(actor,tenant,'courses',workspace_fixture.id('reg_course_1'),'{"credits":5}');
    IF EXISTS(SELECT 1 FROM public.student_offering_enrollments WHERE academic_offering_id=workspace_fixture.id('reg_offering_1')
        AND (subject_snapshot->>'credits')::numeric<>3) THEN
        RAISE EXCEPTION 'Historical credit snapshots changed';
    END IF;
    response:=public.read_student_semesters(workspace_fixture.id('reg_user_1'),tenant);
    IF jsonb_array_length(response->'items'->0->'enrolled_subjects')<>5 THEN
        RAISE EXCEPTION 'Confirmation does not show all five enrolled subjects';
    END IF;
END;
$$;
ROLLBACK;
SELECT 'PASS: option exclusivity, five-subject enrollment, tenant and ownership checks, atomic rollback, capacity, idempotency and snapshots';
