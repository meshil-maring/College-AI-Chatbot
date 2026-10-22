SET request.jwt.claim.role = 'service_role';
DO $$
#variable_conflict use_variable
DECLARE tenant uuid := academic_package_fixture.id('tenant'); admin uuid := academic_package_fixture.id('admin');
    faculty uuid := academic_package_fixture.id('faculty'); actor uuid := gen_random_uuid(); auth_id uuid := gen_random_uuid();
    class_id uuid; label text; section_id uuid; offering uuid; subject uuid; registration uuid; placement uuid; assignment uuid;
    roster uuid; student uuid; item jsonb; test_id uuid; version bigint; mark uuid; episode_start timestamptz;
BEGIN
    INSERT INTO auth.users(id, email) VALUES (auth_id, actor || '@example.invalid');
    INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
    VALUES (actor, auth_id, actor || '@example.invalid', 'Historical', 'Adoption');
    INSERT INTO public.student_registrations(institution_id, program_id, academic_year_id, semester_id, section_code,
        batch_id, batch_start_year, batch_end_year, register_number, university_roll_number, student_name, email, created_by)
    SELECT tenant, b.program_id, academic_package_fixture.id('year'), academic_package_fixture.id('term'), 'ADOPT', b.batch_id,
        b.start_year, b.end_year, 'PKG-ADOPT', 'ROLL-ADOPT', 'Historical Adoption', actor || '@example.invalid', admin
    FROM public.academic_batches b WHERE b.batch_id = academic_package_fixture.id('batch') RETURNING registration_id INTO registration;
    FOREACH label IN ARRAY ARRAY['DSA','ML','A','B','C'] LOOP
        SELECT course_id INTO subject FROM public.academic_curriculum_subjects
        WHERE curriculum_subject_id = academic_package_fixture.id('subject_' || label);
        SELECT o.course_offering_id INTO offering FROM public.course_offerings o WHERE o.course_id = subject
          AND o.program_id = academic_package_fixture.id('program') AND o.semester_id = academic_package_fixture.id('term');
        INSERT INTO public.sections(course_offering_id, name, code, capacity)
        VALUES (offering, 'Historical adoption ' || label, 'ADOPT', 10) RETURNING public.sections.section_id INTO section_id;
        INSERT INTO academic_package_fixture.ids VALUES ('adopt_section_' || label, section_id);
        INSERT INTO public.faculty_section_assignments(institution_id, faculty_user_id, section_id, assigned_by)
        VALUES (tenant, faculty, section_id, admin);
    END LOOP;
    -- This is a normal unmanaged pre-account membership before class mapping.
    INSERT INTO public.faculty_attendance_rosters(institution_id, section_id, course_offering_id, semester_id,
        register_number, university_roll_number, student_name, email, created_by)
    SELECT tenant, sec.section_id, sec.course_offering_id, academic_package_fixture.id('term'), 'PKG-ADOPT', 'ROLL-ADOPT',
        'Historical Adoption', actor || '@example.invalid', faculty FROM public.sections sec
    WHERE sec.section_id = academic_package_fixture.id('adopt_section_DSA') RETURNING roster_id INTO roster;
    PERFORM public.mark_faculty_attendance(faculty, tenant, academic_package_fixture.id('adopt_section_DSA'),
        current_date - 7, jsonb_build_object(roster::text, 'present'), 'Established historical participation');
    item := public.save_faculty_test(faculty, tenant, academic_package_fixture.id('adopt_section_DSA'),
        jsonb_build_object('title', 'Pre-package assessment', 'test_type', 'quiz', 'max_marks', 100, 'scheduled_date', current_date - 5));
    test_id := (item->>'test_id')::uuid; version := (item->>'version')::bigint;
    FOREACH label IN ARRAY ARRAY['schedule','start','complete'] LOOP
        item := public.transition_faculty_test(faculty, tenant, test_id, version, label); version := (item->>'version')::bigint;
    END LOOP;
    item := public.save_faculty_test_marks(faculty, tenant, test_id, version,
        jsonb_build_array(jsonb_build_object('roster_id', roster, 'mark_status', 'present', 'scored_marks', 89)));
    version := (item->>'version')::bigint;
    FOREACH label IN ARRAY ARRAY['submit','publish'] LOOP
        item := public.transition_faculty_test(faculty, tenant, test_id, version, label); version := (item->>'version')::bigint;
    END LOOP;
    SELECT m.test_result_id INTO mark FROM public.test_results m WHERE m.test_id = test_id AND m.roster_id = roster;
    item := academic_package_fixture.command('save_class', jsonb_build_object('program_id', academic_package_fixture.id('program'),
        'batch_id', academic_package_fixture.id('batch'), 'semester_id', academic_package_fixture.id('term'),
        'study_semester', 3, 'section_code', 'ADOPT', 'curriculum_id', academic_package_fixture.id('curriculum'), 'student_choice_enabled', false));
    class_id := (item->>'class_id')::uuid;
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id,
        'package_id', academic_package_fixture.id('package_abc'), 'enabled', true));
    FOREACH label IN ARRAY ARRAY['DSA','ML','A','B','C'] LOOP
        PERFORM academic_package_fixture.command('set_class_subject', jsonb_build_object('class_id', class_id,
            'curriculum_subject_id', academic_package_fixture.id('subject_' || label), 'section_id', academic_package_fixture.id('adopt_section_' || label)));
    END LOOP;
    item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id, 'registration_id', registration));
    placement := (item->>'placement_id')::uuid;
    item := academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement,
        'package_id', academic_package_fixture.id('package_abc')));
    assignment := (item->>'assignment_id')::uuid;
    SELECT sp.started_at INTO episode_start FROM public.academic_subject_participation sp
    WHERE sp.placement_id = placement AND sp.roster_id = roster;
    PERFORM academic_package_fixture.check((episode_start AT TIME ZONE 'UTC')::date <= current_date - 7,
        'explicit adoption preserves earliest established participation facts');
    PERFORM academic_package_fixture.check((item->>'assigned_at')::timestamptz > episode_start,
        'package assignment is recorded now rather than invented in the past');
    INSERT INTO public.students(user_id, institution_id, student_number, register_number, university_roll_number, email,
        program_id, academic_year_id, enrollment_date, approval_status)
    VALUES (actor, tenant, 'PKG-ADOPT', 'PKG-ADOPT', 'ROLL-ADOPT', actor || '@example.invalid', academic_package_fixture.id('program'),
        academic_package_fixture.id('year'), current_date, 'pending') RETURNING student_id INTO student;
    PERFORM public.b05_approve_student(student, tenant, admin, (SELECT auth_user_id FROM public.users WHERE id = admin));
    PERFORM academic_package_fixture.check((SELECT m.student_id = student AND m.status = 'published' AND m.scored_marks = 89
        FROM public.test_results m WHERE m.test_result_id = mark), 'approval reconciles the same preserved pre-package marks');
    PERFORM academic_package_fixture.check((SELECT count(*) = 1 FROM public.student_attendance a
        WHERE a.student_id = student AND a.section_id = academic_package_fixture.id('adopt_section_DSA') AND a.date = current_date - 7),
        'approval mirrors the same historical attendance without guard false positives');
    -- Older direct attendance can exist without a faculty roster. The first
    -- explicit package adoption must preserve those exact historical facts.
    actor := gen_random_uuid(); auth_id := gen_random_uuid();
    INSERT INTO auth.users(id, email) VALUES (auth_id, actor || '@example.invalid');
    INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
    VALUES (actor, auth_id, actor || '@example.invalid', 'Direct attendance', 'Adoption');
    INSERT INTO public.students(user_id, institution_id, student_number, register_number, university_roll_number, email,
        program_id, academic_year_id, enrollment_date, approval_status)
    VALUES (actor, tenant, 'PKG-DIRECT-ADOPT', 'PKG-DIRECT-ADOPT', 'ROLL-DIRECT-ADOPT', actor || '@example.invalid',
        academic_package_fixture.id('program'), academic_package_fixture.id('year'), current_date, 'pending')
    RETURNING student_id INTO student;
    PERFORM public.b05_approve_student(student, tenant, admin, (SELECT auth_user_id FROM public.users WHERE id = admin));
    INSERT INTO public.student_registrations(institution_id, program_id, academic_year_id, semester_id, section_code,
        batch_id, batch_start_year, batch_end_year, register_number, university_roll_number, student_name, email, created_by)
    SELECT tenant, b.program_id, academic_package_fixture.id('year'), academic_package_fixture.id('term'), 'ADOPT', b.batch_id,
        b.start_year, b.end_year, 'PKG-DIRECT-ADOPT', 'ROLL-DIRECT-ADOPT', 'Direct attendance Adoption', actor || '@example.invalid', admin
    FROM public.academic_batches b WHERE b.batch_id = academic_package_fixture.id('batch') RETURNING registration_id INTO registration;
    INSERT INTO public.student_attendance(student_id, section_id, academic_year_id, semester_id, date, status)
    VALUES (student, academic_package_fixture.id('adopt_section_ML'), academic_package_fixture.id('year'),
        academic_package_fixture.id('term'), current_date - 6, 'present');
    PERFORM academic_package_fixture.check(NOT EXISTS (SELECT 1 FROM public.faculty_attendance_rosters
        WHERE register_number = 'PKG-DIRECT-ADOPT'), 'direct historical fact needs no fabricated faculty membership');
    item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id, 'registration_id', registration));
    placement := (item->>'placement_id')::uuid;
    PERFORM academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement,
        'package_id', academic_package_fixture.id('package_abc')));
    PERFORM academic_package_fixture.check((SELECT (sp.started_at AT TIME ZONE 'UTC')::date <= current_date - 6
        FROM public.academic_subject_participation sp WHERE sp.placement_id = placement
          AND sp.curriculum_subject_id = academic_package_fixture.id('subject_ML')),
        'new faculty roster adoption preserves earlier direct attendance eligibility');
    UPDATE public.student_attendance a SET notes = 'Historical direct attendance correction'
    WHERE a.student_id = student AND a.section_id = academic_package_fixture.id('adopt_section_ML') AND a.date = current_date - 6;
    PERFORM academic_package_fixture.check(FOUND, 'direct attendance remains editable at its original historical date');
END;
$$;
SELECT 'PASS: legacy roster adoption retains old participation, assignment time and pending-account academic history' AS result;
