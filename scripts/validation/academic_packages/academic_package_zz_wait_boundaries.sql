SET request.jwt.claim.role = 'service_role';
CREATE SEQUENCE academic_package_fixture.wait_calls;
CREATE FUNCTION academic_package_fixture.delay_target_roster() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.register_number LIKE 'PKG-WAIT-%'
        AND NEW.section_id = academic_package_fixture.id('section_E') THEN
        PERFORM nextval('academic_package_fixture.wait_calls');
        PERFORM pg_sleep(1);
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER zz_package_fixture_delay BEFORE INSERT ON public.faculty_attendance_rosters
    FOR EACH ROW EXECUTE FUNCTION academic_package_fixture.delay_target_roster();

DO $$
#variable_conflict use_variable
DECLARE tenant uuid := academic_package_fixture.id('tenant'); admin uuid := academic_package_fixture.id('admin');
    abc uuid := academic_package_fixture.id('package_abc'); efg uuid := academic_package_fixture.id('package_efg');
    code text; label text; item jsonb; policy jsonb; class_id uuid; registration uuid; placement uuid;
    assignment uuid; calls_before bigint := 0; calls_after bigint; rows_before integer;
BEGIN
    UPDATE public.sections SET capacity = 100 WHERE section_id = academic_package_fixture.id('section_E');
    FOREACH code IN ARRAY ARRAY['WAIT-CUTOFF','WAIT-AUTHORITY'] LOOP
        item := academic_package_fixture.command('save_class', jsonb_build_object('program_id', academic_package_fixture.id('program'),
            'batch_id', academic_package_fixture.id('batch'), 'semester_id', academic_package_fixture.id('term'),
            'study_semester', 3, 'section_code', code, 'curriculum_id', academic_package_fixture.id('curriculum'), 'student_choice_enabled', false));
        class_id := (item->>'class_id')::uuid;
        PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id, 'package_id', abc, 'enabled', true));
        PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id, 'package_id', efg, 'enabled', true));
        FOREACH label IN ARRAY ARRAY['DSA','ML','A','B','C','E','F','G'] LOOP
            PERFORM academic_package_fixture.command('set_class_subject', jsonb_build_object('class_id', class_id,
                'curriculum_subject_id', academic_package_fixture.id('subject_' || label), 'section_id', academic_package_fixture.id('section_' || label)));
        END LOOP;
        INSERT INTO public.student_registrations(institution_id, program_id, academic_year_id, semester_id, section_code,
            batch_id, batch_start_year, batch_end_year, register_number, university_roll_number, student_name, email, created_by)
        SELECT tenant, b.program_id, academic_package_fixture.id('year'), academic_package_fixture.id('term'), code,
            b.batch_id, b.start_year, b.end_year, 'PKG-' || code, 'ROLL-' || code,
            code, lower(code) || '@example.invalid', admin
        FROM public.academic_batches b WHERE b.batch_id = academic_package_fixture.id('batch') RETURNING registration_id INTO registration;
        item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id, 'registration_id', registration));
        placement := (item->>'placement_id')::uuid;
        item := academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc));
        assignment := (item->>'assignment_id')::uuid;
        SELECT count(*) INTO rows_before FROM public.faculty_attendance_rosters WHERE institution_id = tenant;
        IF code = 'WAIT-CUTOFF' THEN
            SELECT to_jsonb(c) || jsonb_build_object('program_id', academic_package_fixture.id('program'),
                'change_cutoff', clock_timestamp() + interval '0.5 seconds') INTO policy
            FROM public.academic_classes c WHERE c.class_id = class_id;
            PERFORM academic_package_fixture.command('save_class', policy);
            PERFORM academic_package_fixture.expect_error('change_package', jsonb_build_object('assignment_id', assignment,
                'package_id', efg, 'expected_revision', 1, 'reason', 'Deadline expires while preparing target subjects'), 'admin', '23514');
        ELSE
            UPDATE public.faculty_responsibilities SET end_at = clock_timestamp() + interval '0.5 seconds'
            WHERE faculty_user_id = academic_package_fixture.id('faculty') AND responsibility_code = 'hod' AND institution_id = tenant;
            PERFORM academic_package_fixture.expect_error('change_package', jsonb_build_object('assignment_id', assignment,
                'package_id', efg, 'expected_revision', 1, 'reason', 'Authority expires while preparing target subjects'), 'faculty', '42501');
        END IF;
        SELECT last_value INTO calls_after FROM academic_package_fixture.wait_calls;
        PERFORM academic_package_fixture.check(calls_after > calls_before, 'target preparation actually waited');
        calls_before := calls_after;
        PERFORM academic_package_fixture.check((SELECT package_id = abc AND revision = 1
            FROM public.academic_package_assignments WHERE assignment_id = assignment), 'wait failure retains old revision');
        PERFORM academic_package_fixture.check((SELECT count(*) = rows_before
            FROM public.faculty_attendance_rosters WHERE institution_id = tenant), 'wait failure rolls back prepared target rosters');
    END LOOP;
END;
$$;
DROP TRIGGER zz_package_fixture_delay ON public.faculty_attendance_rosters;
SELECT 'PASS: cutoff and scoped responsibility are rechecked after target preparation waits' AS result;
