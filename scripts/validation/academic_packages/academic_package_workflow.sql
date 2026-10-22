SET request.jwt.claim.role = 'service_role';
DO $$
#variable_conflict use_variable
DECLARE tenant uuid := academic_package_fixture.id('tenant'); admin uuid := academic_package_fixture.id('admin');
    student uuid := academic_package_fixture.id('student'); faculty uuid := academic_package_fixture.id('faculty');
    class_id uuid := academic_package_fixture.id('class'); placement uuid := academic_package_fixture.id('placement');
    abc uuid := academic_package_fixture.id('package_abc'); efg uuid := academic_package_fixture.id('package_efg');
    item jsonb; assignment uuid; request uuid; core_roster uuid; a_roster uuid; catalogue jsonb; before_count integer;
    policy jsonb; error_state text; registration uuid; second_placement uuid; canonical_student uuid;
BEGIN
    PERFORM academic_package_fixture.check(NOT has_table_privilege('authenticated', 'public.academic_package_assignments', 'SELECT'), 'browser table access revoked');
    PERFORM academic_package_fixture.check(NOT has_function_privilege('authenticated',
        'public.academic_package_command(uuid,uuid,text,jsonb)', 'EXECUTE'), 'browser command access revoked');
    PERFORM academic_package_fixture.expect_error('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc), 'student', '42501');
    PERFORM academic_package_fixture.expect_error('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc), 'faculty', '42501');
    PERFORM academic_package_fixture.expect_error('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc), 'staff', '42501');
    PERFORM academic_package_fixture.check(public.phase81_manage_staff_permission_grants(admin, tenant,
        academic_package_fixture.id('staff'), ARRAY['academic.package.assign','academic.class.read'], true) = 2, 'new staff capabilities delegate through audited RPC');
    item := academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc), 'staff');
    assignment := (item->>'assignment_id')::uuid;
    INSERT INTO academic_package_fixture.ids VALUES ('assignment', assignment);
    PERFORM academic_package_fixture.check((item->>'revision')::integer = 1, 'initial revision');
    PERFORM academic_package_fixture.check((SELECT count(*) = 5 FROM public.academic_subject_participation
        WHERE placement_id = placement AND ended_at IS NULL), 'core DSA ML plus complete ABC');
    item := academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc), 'staff');
    PERFORM academic_package_fixture.check((item->>'revision')::integer = 1, 'retry does not duplicate assignment');
    SELECT roster_id INTO core_roster FROM public.academic_subject_participation
    WHERE placement_id = placement AND curriculum_subject_id = academic_package_fixture.id('subject_DSA');
    SELECT roster_id INTO a_roster FROM public.academic_subject_participation
    WHERE placement_id = placement AND curriculum_subject_id = academic_package_fixture.id('subject_A');
    INSERT INTO academic_package_fixture.ids VALUES ('core_roster', core_roster), ('a_roster', a_roster);
    PERFORM public.mark_faculty_attendance(faculty, tenant, academic_package_fixture.id('section_A'), current_date,
        jsonb_build_object(a_roster::text, 'present'), 'Package history contract');
    SELECT count(*) INTO before_count FROM public.faculty_attendance_rosters WHERE institution_id = tenant;
    UPDATE public.sections SET is_active = false WHERE section_id = academic_package_fixture.id('section_E');
    PERFORM academic_package_fixture.expect_error('change_package', jsonb_build_object('assignment_id', assignment,
        'package_id', efg, 'expected_revision', 1, 'reason', 'Missing offering must roll back'), 'admin', '23514');
    PERFORM academic_package_fixture.check((SELECT count(*) = before_count FROM public.faculty_attendance_rosters WHERE institution_id = tenant), 'failed package leaves no partial rosters');
    PERFORM academic_package_fixture.check((SELECT package_id = abc AND revision = 1 FROM public.academic_package_assignments
        WHERE assignment_id = assignment), 'failed package leaves assignment intact');
    UPDATE public.sections SET is_active = true WHERE section_id = academic_package_fixture.id('section_E');
    item := academic_package_fixture.command('request_change', jsonb_build_object('assignment_id', assignment,
        'package_id', efg, 'reason', 'Prefer the EFG package'), 'student');
    request := (item->>'request_id')::uuid;
    PERFORM academic_package_fixture.check((SELECT package_id = abc FROM public.academic_package_assignments
        WHERE assignment_id = assignment), 'pending request does not change subjects');
    PERFORM academic_package_fixture.expect_error('change_package', jsonb_build_object('assignment_id', assignment,
        'package_id', efg, 'expected_revision', 1, 'reason', 'Student cannot apply'), 'student', '42501');
    item := academic_package_fixture.command('review_request', jsonb_build_object('request_id', request, 'approve', true, 'reason', 'Approved before cutoff'));
    PERFORM academic_package_fixture.check(item->>'status' = 'approved', 'review applies complete requested package');
    PERFORM academic_package_fixture.check((SELECT count(*) = 5 FROM public.academic_subject_participation
        WHERE placement_id = placement AND ended_at IS NULL), 'new package has exact complete set');
    PERFORM academic_package_fixture.check((SELECT roster_id = core_roster FROM public.academic_subject_participation
        WHERE placement_id = placement AND curriculum_subject_id = academic_package_fixture.id('subject_DSA') AND ended_at IS NULL), 'core roster identity retained');
    PERFORM academic_package_fixture.check((SELECT NOT participation_active FROM public.faculty_attendance_rosters WHERE roster_id = a_roster), 'removed subject ends independent participation');
    PERFORM academic_package_fixture.check((SELECT count(*) = 1 FROM public.faculty_attendance_records WHERE roster_id = a_roster), 'old attendance preserved');
    SELECT student_id INTO canonical_student FROM public.students WHERE user_id = student;
    BEGIN
        INSERT INTO public.student_attendance(student_id, section_id, academic_year_id, semester_id, date, status)
        VALUES (canonical_student, academic_package_fixture.id('section_A'), academic_package_fixture.id('year'),
            academic_package_fixture.id('term'), current_date + 1, 'present');
    EXCEPTION WHEN OTHERS THEN error_state := SQLSTATE;
    END;
    PERFORM academic_package_fixture.check(error_state = '23514', 'legacy attendance cannot bypass ended participation by omitting institution');
    error_state := NULL;
    BEGIN
        INSERT INTO public.test_results(student_id, course_id, section_id, academic_year_id, semester_id,
            test_name, test_type, max_marks, scored_marks, conducted_at, institution_id)
        SELECT canonical_student, subject.course_id, academic_package_fixture.id('section_A'),
            academic_package_fixture.id('year'), academic_package_fixture.id('term'), 'Ended legacy test', 'quiz', 100, 85,
            (current_date + 1)::timestamp AT TIME ZONE 'UTC', gen_random_uuid()
        FROM public.academic_curriculum_subjects subject WHERE curriculum_subject_id = academic_package_fixture.id('subject_A');
    EXCEPTION WHEN OTHERS THEN error_state := SQLSTATE;
    END;
    PERFORM academic_package_fixture.check(error_state = '23514', 'legacy marks cannot bypass ended participation with forged institution');
    error_state := NULL;
    UPDATE public.student_attendance SET notes = 'Historical administrative correction'
    WHERE student_id = canonical_student AND section_id = academic_package_fixture.id('section_A') AND date = current_date;
    PERFORM academic_package_fixture.check(FOUND, 'legacy attendance permits historical corrections after subject ends');
    INSERT INTO public.test_results(student_id, course_id, section_id, academic_year_id, semester_id,
        test_name, test_type, max_marks, scored_marks, conducted_at)
    SELECT canonical_student, subject.course_id, academic_package_fixture.id('section_A'),
        academic_package_fixture.id('year'), academic_package_fixture.id('term'), 'Historical legacy test', 'quiz', 100, 85,
        current_date::timestamp AT TIME ZONE 'UTC'
    FROM public.academic_curriculum_subjects subject WHERE curriculum_subject_id = academic_package_fixture.id('subject_A');
    BEGIN
        DELETE FROM public.faculty_attendance_rosters WHERE roster_id = a_roster;
    EXCEPTION WHEN OTHERS THEN error_state := SQLSTATE;
    END;
    PERFORM academic_package_fixture.check(error_state = '23514', 'direct delete cannot erase participation history');
    error_state := NULL;
    item := academic_package_fixture.command('request_change', jsonb_build_object('assignment_id', assignment,
        'package_id', abc, 'reason', 'Request ABC again'), 'student');
    request := (item->>'request_id')::uuid;
    item := academic_package_fixture.command('change_package', jsonb_build_object('assignment_id', assignment,
        'package_id', abc, 'expected_revision', 2, 'reason', 'Authorized return to ABC'));
    PERFORM academic_package_fixture.check((item->>'revision')::integer = 3, 'administrative change increments revision');
    PERFORM academic_package_fixture.check((SELECT status = 'superseded' FROM public.academic_package_requests WHERE request_id = request), 'stale request superseded');
    PERFORM academic_package_fixture.check((SELECT count(*) = 2 FROM public.academic_subject_participation
        WHERE placement_id = placement AND curriculum_subject_id = academic_package_fixture.id('subject_A')), 'rejoin creates new episode');
    PERFORM academic_package_fixture.check((SELECT count(DISTINCT roster_id) = 1 FROM public.academic_subject_participation
        WHERE placement_id = placement AND curriculum_subject_id = academic_package_fixture.id('subject_A')), 'rejoin reuses historical roster');
    PERFORM academic_package_fixture.expect_error('change_package', jsonb_build_object('assignment_id', assignment,
        'package_id', efg, 'expected_revision', 1, 'reason', 'Stale write'), 'admin', 'P0001');
    PERFORM academic_package_fixture.expect_error('set_curriculum_subject', jsonb_build_object('curriculum_id', academic_package_fixture.id('curriculum'),
        'course_id', (SELECT course_id FROM public.academic_curriculum_subjects WHERE curriculum_subject_id = academic_package_fixture.id('subject_A')),
        'study_semester', 3, 'course_type', 'core', 'is_core', true), 'admin', '23514');
    item := academic_package_fixture.command('request_change', jsonb_build_object('assignment_id', assignment,
        'package_id', efg, 'reason', 'Pending when deadline closes'), 'student');
    request := (item->>'request_id')::uuid;
    SELECT to_jsonb(c) || jsonb_build_object('program_id', academic_package_fixture.id('program'),
        'change_cutoff', clock_timestamp() - interval '1 second') INTO policy FROM public.academic_classes c WHERE c.class_id = class_id;
    PERFORM academic_package_fixture.command('save_class', policy);
    PERFORM academic_package_fixture.expect_error('change_package', jsonb_build_object('assignment_id', assignment,
        'package_id', efg, 'expected_revision', 3, 'reason', 'No admin late override'), 'admin', '23514');
    PERFORM academic_package_fixture.expect_error('request_change', jsonb_build_object('assignment_id', assignment,
        'package_id', efg, 'reason', 'Late request'), 'student', '23514');
    item := academic_package_fixture.command('review_request', jsonb_build_object('request_id', request, 'approve', true, 'reason', 'Earlier request is still late'));
    PERFORM academic_package_fixture.check(item->>'status' = 'expired', 'pending request cannot approve after cutoff');
    policy := policy || jsonb_build_object('change_cutoff', clock_timestamp() + interval '1 day');
    PERFORM academic_package_fixture.expect_error('save_class', policy, 'admin', '23514');
    catalogue := public.academic_package_catalogue(student, tenant);
    PERFORM academic_package_fixture.check(jsonb_array_length(catalogue->'records'->'placements') = 1, 'student catalogue contains own placement');
    PERFORM academic_package_fixture.check((catalogue->'records'->'classes'->0->>'changes_locked')::boolean, 'student sees locked class');
    PERFORM academic_package_fixture.check((SELECT count(*) = 3 FROM public.academic_package_revisions WHERE assignment_id = assignment), 'one immutable history row per successful revision');
    PERFORM academic_package_fixture.check((SELECT count(*) = 3 FROM public.admin_audit_log
        WHERE institution_id = tenant AND action = 'academic.package.apply'), 'one atomic audit per successful assignment');
END;
$$;
SELECT 'PASS: complete packages, permission gates, retries, rollback, requests, shared core, rejoin history and hard cutoff' AS result;
