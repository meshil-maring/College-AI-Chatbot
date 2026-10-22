SET request.jwt.claim.role = 'service_role';
DO $$
#variable_conflict use_variable
DECLARE tenant uuid := academic_package_fixture.id('tenant'); admin uuid := academic_package_fixture.id('admin');
    faculty uuid := academic_package_fixture.id('faculty'); label text; item jsonb; curriculum uuid; package_id uuid;
    year_id uuid; term uuid; class_id uuid; subject uuid; offering uuid; section_id uuid; members uuid[] := '{}';
    registration uuid; placement uuid; pending_user uuid := gen_random_uuid(); pending_auth uuid := gen_random_uuid();
    pending_student uuid; pending_roster uuid; main_roster uuid; main_student uuid; test_id uuid; version bigint;
    row_id uuid; pending_mark uuid; rows jsonb; roster_context jsonb; responsibility uuid;
    import_id uuid; import_time timestamptz; import_rows jsonb; overlap_term uuid;
BEGIN
    INSERT INTO public.semesters(academic_year_id, name, code, semester_number, start_date, end_date)
    VALUES (academic_package_fixture.id('year'), 'Overlapping calendar term', 'OVERLAP', 2,
        current_date - 10, current_date + 80) RETURNING semester_id INTO overlap_term;
    item := academic_package_fixture.command('save_class', jsonb_build_object('program_id', academic_package_fixture.id('program'),
        'batch_id', academic_package_fixture.id('batch'), 'semester_id', overlap_term, 'study_semester', 3,
        'section_code', 'OVERLAP', 'curriculum_id', academic_package_fixture.id('curriculum'), 'student_choice_enabled', false));
    PERFORM academic_package_fixture.expect_error('place_student', jsonb_build_object('class_id', item->>'class_id',
        'registration_id', academic_package_fixture.id('registration')), 'admin', '23514');
    INSERT INTO public.academic_years(institution_id, name, code, start_date, end_date)
    VALUES (tenant, 'Later academic year', 'LATER', current_date + 201, current_date + 600) RETURNING academic_year_id INTO year_id;
    INSERT INTO public.semesters(academic_year_id, name, code, semester_number, start_date, end_date)
    VALUES (year_id, 'Later Calendar Term 1', 'LATER-T1', 1, current_date + 201, current_date + 300) RETURNING semester_id INTO term;
    item := academic_package_fixture.command('save_curriculum', jsonb_build_object('program_id', academic_package_fixture.id('program'),
        'name', 'CSE Curriculum', 'code', 'CSE-PLAN', 'version', 2));
    curriculum := (item->>'curriculum_id')::uuid;
    PERFORM academic_package_fixture.expect_error('save_class', jsonb_build_object('program_id', academic_package_fixture.id('program'),
        'batch_id', academic_package_fixture.id('batch'), 'semester_id', term, 'study_semester', 5,
        'section_code', 'EMPTY', 'curriculum_id', curriculum, 'student_choice_enabled', false), 'admin', '23514');
    FOREACH label IN ARRAY ARRAY['DSA','ML','A','B','C'] LOOP
        SELECT course_id INTO subject FROM public.academic_curriculum_subjects WHERE curriculum_subject_id = academic_package_fixture.id('subject_' || label);
        item := academic_package_fixture.command('set_curriculum_subject', jsonb_build_object('curriculum_id', curriculum,
            'course_id', subject, 'study_semester', 5, 'course_type', CASE WHEN label IN ('DSA','ML') THEN 'core' ELSE 'elective' END,
            'is_core', label IN ('DSA','ML')));
        row_id := (item->>'curriculum_subject_id')::uuid;
        INSERT INTO academic_package_fixture.ids VALUES ('later_subject_' || label, row_id);
        IF label IN ('A','B','C') THEN members := array_append(members, row_id); END IF;
        INSERT INTO public.course_offerings(course_id, program_id, academic_year_id, semester_id, capacity)
        VALUES (subject, academic_package_fixture.id('program'), year_id, term, 10) RETURNING course_offering_id INTO offering;
        INSERT INTO public.sections(course_offering_id, name, code, capacity) VALUES (offering, 'Later ' || label, 'NEXT-A', 10)
        RETURNING public.sections.section_id INTO section_id;
        INSERT INTO academic_package_fixture.ids VALUES ('later_section_' || label, section_id);
        INSERT INTO public.faculty_section_assignments(institution_id, faculty_user_id, section_id, assigned_by)
        VALUES (tenant, faculty, section_id, admin);
    END LOOP;
    item := academic_package_fixture.command('save_package', jsonb_build_object('curriculum_id', curriculum,
        'study_semester', 5, 'name', 'Later ABC', 'code', 'ABC', 'curriculum_subject_ids', to_jsonb(members)));
    package_id := (item->>'package_id')::uuid;
    item := academic_package_fixture.command('save_class', jsonb_build_object('program_id', academic_package_fixture.id('program'),
        'batch_id', academic_package_fixture.id('batch'), 'semester_id', term, 'study_semester', 5,
        'section_code', 'LATER', 'curriculum_id', curriculum, 'student_choice_enabled', false));
    class_id := (item->>'class_id')::uuid;
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id, 'package_id', package_id, 'enabled', true));
    FOREACH label IN ARRAY ARRAY['DSA','ML','A','B','C'] LOOP
        PERFORM academic_package_fixture.command('set_class_subject', jsonb_build_object('class_id', class_id,
            'curriculum_subject_id', academic_package_fixture.id('later_subject_' || label), 'section_id', academic_package_fixture.id('later_section_' || label)));
    END LOOP;
    INSERT INTO public.faculty_responsibilities(institution_id, faculty_user_id, responsibility_code, scope_type, scope_id, start_at, created_by)
    VALUES (tenant, faculty, 'class_in_charge', 'section', academic_package_fixture.id('later_section_DSA'), clock_timestamp() - interval '1 hour', admin)
    RETURNING responsibility_id INTO responsibility;
    PERFORM academic_package_fixture.command('set_class_responsibility', jsonb_build_object('class_id', class_id,
        'responsibility_id', responsibility, 'enabled', true));
    PERFORM academic_package_fixture.check(public.academic_package_allowed(faculty, tenant, 'academic.package.assign', class_id),
        'explicit class bridge permits differently coded mapped teaching group');
    item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id,
        'registration_id', academic_package_fixture.id('registration')));
    placement := (item->>'placement_id')::uuid;
    PERFORM academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', package_id));
    SELECT sp.roster_id INTO main_roster FROM public.academic_subject_participation sp
    WHERE sp.placement_id = placement AND sp.curriculum_subject_id = academic_package_fixture.id('later_subject_DSA');
    SELECT student_id INTO main_student FROM public.students WHERE user_id = academic_package_fixture.id('student');
    INSERT INTO auth.users(id, email) VALUES (pending_auth, pending_user || '@example.invalid');
    INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
    VALUES (pending_user, pending_auth, pending_user || '@example.invalid', 'Pending', 'Progression');
    INSERT INTO public.student_registrations(institution_id, program_id, academic_year_id, semester_id, section_code,
        batch_id, batch_start_year, batch_end_year, register_number, university_roll_number, student_name, email, created_by)
    SELECT tenant, b.program_id, academic_package_fixture.id('year'), academic_package_fixture.id('term'), 'A', b.batch_id,
        b.start_year, b.end_year, 'PKG-PENDING-LATER', 'ROLL-PENDING-LATER', 'Pending Progression', pending_user || '@example.invalid', admin
    FROM public.academic_batches b WHERE b.batch_id = academic_package_fixture.id('batch') RETURNING registration_id INTO registration;
    item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id, 'registration_id', registration));
    placement := (item->>'placement_id')::uuid;
    PERFORM academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', package_id));
    SELECT sp.roster_id INTO pending_roster FROM public.academic_subject_participation sp
    WHERE sp.placement_id = placement AND sp.curriculum_subject_id = academic_package_fixture.id('later_subject_DSA');
    roster_context := public.academic_package_roster_context(tenant, ARRAY[main_roster, pending_roster]);
    PERFORM academic_package_fixture.check((roster_context->main_roster::text->>'academic_year_id')::uuid = year_id,
        'approved later-year context derives exact placement without changing admission');
    PERFORM academic_package_fixture.check((roster_context->pending_roster::text->>'study_semester')::integer = 5,
        'unregistered managed context exposes study progression');
    item := public.save_faculty_test(faculty, tenant, academic_package_fixture.id('later_section_DSA'), jsonb_build_object(
        'title', 'Later year placement assessment', 'test_type', 'quiz', 'max_marks', 100,
        'scheduled_date', current_date + 210, 'passing_marks', 40));
    test_id := (item->>'test_id')::uuid; version := (item->>'version')::bigint;
    FOREACH label IN ARRAY ARRAY['schedule','start','complete'] LOOP
        item := public.transition_faculty_test(faculty, tenant, test_id, version, label); version := (item->>'version')::bigint;
    END LOOP;
    rows := jsonb_build_array(jsonb_build_object('roster_id', main_roster, 'mark_status', 'present', 'scored_marks', 82),
        jsonb_build_object('roster_id', pending_roster, 'mark_status', 'present', 'scored_marks', 74));
    item := public.save_faculty_test_marks(faculty, tenant, test_id, version, rows); version := (item->>'version')::bigint;
    INSERT INTO public.students(user_id, institution_id, student_number, register_number, university_roll_number, email,
        program_id, academic_year_id, enrollment_date, approval_status)
    VALUES (pending_user, tenant, 'PKG-PENDING-LATER', 'PKG-PENDING-LATER', 'ROLL-PENDING-LATER', pending_user || '@example.invalid',
        academic_package_fixture.id('program'), academic_package_fixture.id('year'), current_date, 'pending') RETURNING student_id INTO pending_student;
    item := public.save_faculty_test_marks(faculty, tenant, test_id, version, rows); version := (item->>'version')::bigint;
    FOREACH label IN ARRAY ARRAY['submit','publish'] LOOP
        item := public.transition_faculty_test(faculty, tenant, test_id, version, label); version := (item->>'version')::bigint;
    END LOOP;
    SELECT m.test_result_id INTO pending_mark FROM public.test_results m WHERE m.test_id = test_id AND m.roster_id = pending_roster;
    PERFORM academic_package_fixture.check((SELECT status = 'draft' AND student_id IS NULL FROM public.test_results WHERE test_result_id = pending_mark),
        'published test keeps unapproved preserved marks private');
    PERFORM academic_package_fixture.check((SELECT status = 'published' AND student_id = main_student FROM public.test_results m
        WHERE m.test_id = test_id AND m.roster_id = main_roster), 'approved later-year marks publish');
    PERFORM public.b05_approve_student(pending_student, tenant, admin, (SELECT auth_user_id FROM public.users WHERE id = admin));
    PERFORM academic_package_fixture.check((SELECT status = 'published' AND student_id = pending_student AND scored_marks = 74
        FROM public.test_results WHERE test_result_id = pending_mark), 'approval reconciles the same preserved marks into later-year publication');
    PERFORM academic_package_fixture.check((SELECT academic_year_id = academic_package_fixture.id('year')
        FROM public.students WHERE student_id = pending_student), 'approval never rewrites admission year to make progression work');
    PERFORM academic_package_fixture.check((SELECT academic_year_id = academic_package_fixture.id('year')
        FROM public.student_registrations WHERE registration_id = registration), 'placement never rewrites admission registration');
    import_rows := jsonb_build_array(jsonb_build_object('row_number', 2, 'raw_data', jsonb_build_object('register_number', 'PKG-REG'),
        'normalized_data', jsonb_build_object('register_number', 'PKG-REG', 'university_roll_number', 'PKG-ROLL',
            'student_name', 'Student Contract imported evidence'), 'validation_status', 'UPDATE', 'errors', '[]'::jsonb, 'warnings', '[]'::jsonb));
    item := public.stage_faculty_attendance_import(faculty, tenant, academic_package_fixture.id('later_section_DSA'), term,
        'progression.csv', 'csv', 'CSV', false, '{}'::jsonb, import_rows);
    import_id := (item->>'import_id')::uuid;
    SELECT i.updated_at INTO import_time FROM public.faculty_attendance_imports i WHERE i.import_id = import_id;
    item := public.commit_faculty_attendance_import(faculty, tenant, import_id, import_time, import_rows);
    PERFORM academic_package_fixture.check((item->>'imported_rows')::integer = 1, 'managed later-year import updates existing evidence');
    PERFORM academic_package_fixture.check((SELECT count(*) = 2 FROM public.faculty_attendance_rosters r
        WHERE r.section_id = academic_package_fixture.id('later_section_DSA')), 'managed import does not create or duplicate subject membership');
END;
$$;
SELECT 'PASS: empty-curriculum readiness, exact class bridge and later-year unregistered/pending/approved assessment reconciliation' AS result;
