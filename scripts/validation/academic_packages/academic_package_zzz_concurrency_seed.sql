SET request.jwt.claim.role = 'service_role';
DO $$
DECLARE tenant uuid := academic_package_fixture.id('tenant'); admin uuid := academic_package_fixture.id('admin');
    class_id uuid; label text; item jsonb; registration uuid;
BEGIN
    item := academic_package_fixture.command('save_class', jsonb_build_object('program_id', academic_package_fixture.id('program'),
        'batch_id', academic_package_fixture.id('batch'), 'semester_id', academic_package_fixture.id('term'),
        'study_semester', 3, 'section_code', 'CONCURRENT', 'curriculum_id', academic_package_fixture.id('curriculum'), 'student_choice_enabled', false));
    class_id := (item->>'class_id')::uuid;
    INSERT INTO academic_package_fixture.ids VALUES ('race_class', class_id);
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id,
        'package_id', academic_package_fixture.id('package_abc'), 'enabled', true));
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id,
        'package_id', academic_package_fixture.id('package_efg'), 'enabled', true));
    FOREACH label IN ARRAY ARRAY['DSA','ML','A','B','C','E','F','G'] LOOP
        PERFORM academic_package_fixture.command('set_class_subject', jsonb_build_object('class_id', class_id,
            'curriculum_subject_id', academic_package_fixture.id('subject_' || label), 'section_id', academic_package_fixture.id('section_' || label)));
    END LOOP;
    FOREACH label IN ARRAY ARRAY['RACE_INITIAL','RACE_CAP_A','RACE_CAP_B'] LOOP
        INSERT INTO public.student_registrations(institution_id, program_id, academic_year_id, semester_id, section_code,
            batch_id, batch_start_year, batch_end_year, register_number, university_roll_number, student_name, email, created_by)
        SELECT tenant, b.program_id, academic_package_fixture.id('year'), academic_package_fixture.id('term'), 'CONCURRENT',
            b.batch_id, b.start_year, b.end_year, label, 'ROLL-' || label, label, lower(label) || '@example.invalid', admin
        FROM public.academic_batches b WHERE b.batch_id = academic_package_fixture.id('batch') RETURNING registration_id INTO registration;
        item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id, 'registration_id', registration));
        INSERT INTO academic_package_fixture.ids VALUES (label, (item->>'placement_id')::uuid);
    END LOOP;
END;
$$;
SELECT 'PASS: independent placements ready for competing initial selections and last-seat capacity races' AS result;
