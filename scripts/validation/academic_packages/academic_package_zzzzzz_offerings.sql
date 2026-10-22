SET request.jwt.claim.role = 'service_role';
DO $$
#variable_conflict use_variable
DECLARE tenant uuid := academic_package_fixture.id('tenant'); admin uuid := academic_package_fixture.id('admin');
    program uuid := academic_package_fixture.id('program'); year_id uuid; term uuid; unrelated_term uuid;
    named_subject uuid; pinned_subject uuid; outside_subject uuid; subject uuid; curriculum uuid; package_id uuid;
    class_id uuid; section_id uuid; offering uuid; placement uuid; named_link uuid; pinned_link uuid;
    item jsonb; eligibility jsonb; payload jsonb; observed text; label text;
BEGIN
    INSERT INTO public.academic_years(institution_id, name, code, start_date, end_date)
    VALUES (tenant, 'Named-only academic year', 'NAMED-YEAR', current_date + 601, current_date + 1000)
    RETURNING academic_year_id INTO year_id;
    INSERT INTO public.semesters(academic_year_id, name, code, semester_number, start_date, end_date)
    VALUES (year_id, 'Named curriculum term', 'NAMED-T1', 1, current_date + 601, current_date + 700)
    RETURNING semester_id INTO term;
    INSERT INTO public.semesters(academic_year_id, name, code, semester_number, start_date, end_date)
    VALUES (year_id, 'Unrelated calendar term', 'NAMED-T2', 2, current_date + 701, current_date + 800)
    RETURNING semester_id INTO unrelated_term;
    INSERT INTO public.courses(department_id, name, code)
    VALUES (academic_package_fixture.id('department'), 'Named-only core subject', 'NAMED-ONLY') RETURNING course_id INTO named_subject;
    INSERT INTO public.courses(department_id, name, code)
    VALUES (academic_package_fixture.id('department'), 'Legacy pinned elective', 'LEGACY-PINNED') RETURNING course_id INTO pinned_subject;
    INSERT INTO public.courses(department_id, name, code)
    VALUES (academic_package_fixture.id('department'), 'Subject outside either curriculum', 'OUTSIDE') RETURNING course_id INTO outside_subject;
    INSERT INTO public.program_courses(program_id, course_id, semester_id, course_type)
    VALUES (program, pinned_subject, academic_package_fixture.id('term'), 'elective');
    item := academic_package_fixture.command('save_curriculum', jsonb_build_object('program_id', program,
        'name', 'CSE Named-only Curriculum', 'code', 'CSE-PLAN', 'version', 3));
    curriculum := (item->>'curriculum_id')::uuid;
    item := academic_package_fixture.command('set_curriculum_subject', jsonb_build_object('curriculum_id', curriculum,
        'course_id', named_subject, 'study_semester', 7, 'course_type', 'core', 'is_core', true));
    named_link := (item->>'curriculum_subject_id')::uuid;
    item := academic_package_fixture.command('set_curriculum_subject', jsonb_build_object('curriculum_id', curriculum,
        'course_id', pinned_subject, 'study_semester', 7, 'course_type', 'elective', 'is_core', false));
    pinned_link := (item->>'curriculum_subject_id')::uuid;
    item := academic_package_fixture.command('save_package', jsonb_build_object('curriculum_id', curriculum,
        'study_semester', 7, 'name', 'Named package', 'code', 'NAMED', 'curriculum_subject_ids', jsonb_build_array(pinned_link)));
    package_id := (item->>'package_id')::uuid;
    payload := jsonb_build_object('course_id', named_subject, 'program_id', program,
        'academic_year_id', year_id, 'semester_id', term, 'capacity', 10);
    BEGIN
        PERFORM public.manage_academic_master_record(admin, tenant, 'course_offerings', NULL, payload);
    EXCEPTION WHEN OTHERS THEN observed := SQLSTATE;
    END;
    PERFORM academic_package_fixture.check(observed = '23514', 'named curriculum requires exact saved class applicability before offering creation');
    item := academic_package_fixture.command('save_class', jsonb_build_object('program_id', program,
        'batch_id', academic_package_fixture.id('batch'), 'semester_id', term, 'study_semester', 7,
        'section_code', 'NAMED', 'curriculum_id', curriculum, 'student_choice_enabled', false));
    class_id := (item->>'class_id')::uuid;
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id, 'package_id', package_id, 'enabled', true));
    eligibility := public.academic_package_offering_eligibility(admin, tenant);
    PERFORM academic_package_fixture.check(eligibility @> jsonb_build_array(jsonb_build_object('program_id', program,
        'course_id', named_subject, 'semester_id', term, 'source', 'named_curriculum')), 'metadata includes named-only exact offering triple');
    PERFORM academic_package_fixture.check(eligibility @> jsonb_build_array(jsonb_build_object('program_id', program,
        'course_id', pinned_subject, 'semester_id', term, 'source', 'named_curriculum')), 'named authority supports legacy subject pinned to older term');
    PERFORM academic_package_fixture.check(NOT eligibility @> jsonb_build_array(jsonb_build_object('program_id', program,
        'course_id', named_subject, 'semester_id', unrelated_term)), 'metadata never widens named subject into unrelated dated terms');
    PERFORM academic_package_fixture.check(NOT has_function_privilege('authenticated',
        'public.academic_package_offering_eligibility(uuid,uuid)', 'EXECUTE'), 'offering metadata remains service-only');
    observed := NULL;
    BEGIN
        PERFORM public.academic_package_offering_eligibility(gen_random_uuid(), tenant);
    EXCEPTION WHEN OTHERS THEN observed := SQLSTATE;
    END;
    PERFORM academic_package_fixture.check(observed = '42501', 'offering metadata rechecks active tenant actor');
    FOREACH label IN ARRAY ARRAY['NAMED','PINNED'] LOOP
        subject := CASE WHEN label = 'NAMED' THEN named_subject ELSE pinned_subject END;
        item := public.manage_academic_master_record(admin, tenant, 'course_offerings', NULL,
            payload || jsonb_build_object('course_id', subject));
        offering := (item->>'course_offering_id')::uuid;
        PERFORM academic_package_fixture.check(offering IS NOT NULL, 'existing master RPC creates named curriculum offering');
        item := public.manage_academic_master_record(admin, tenant, 'sections', NULL,
            jsonb_build_object('course_offering_id', offering, 'name', label || ' named teaching group', 'code', 'NAMED', 'capacity', 10));
        section_id := (item->>'section_id')::uuid;
        PERFORM academic_package_fixture.command('set_class_subject', jsonb_build_object('class_id', class_id,
            'curriculum_subject_id', CASE WHEN label = 'NAMED' THEN named_link ELSE pinned_link END, 'section_id', section_id));
    END LOOP;
    item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id,
        'registration_id', academic_package_fixture.id('registration')));
    placement := (item->>'placement_id')::uuid;
    PERFORM academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', package_id));
    PERFORM academic_package_fixture.check((SELECT count(*) = 2 FROM public.academic_subject_participation
        WHERE placement_id = placement AND ended_at IS NULL), 'named-only setup completes through atomic core plus package assignment');
    PERFORM academic_package_fixture.check(NOT EXISTS (SELECT 1 FROM public.program_courses
        WHERE program_id = program AND course_id = named_subject), 'named curriculum does not fabricate duplicate legacy program-subject rows');
    PERFORM academic_package_fixture.check((SELECT semester_id = academic_package_fixture.id('term') FROM public.program_courses
        WHERE program_id = program AND course_id = pinned_subject), 'pinned legacy applicability remains unchanged');
    FOREACH subject IN ARRAY ARRAY[named_subject, pinned_subject, outside_subject] LOOP
        observed := NULL;
        BEGIN
            PERFORM public.manage_academic_master_record(admin, tenant, 'course_offerings', NULL,
                payload || jsonb_build_object('course_id', subject, 'semester_id', unrelated_term));
        EXCEPTION WHEN OTHERS THEN observed := SQLSTATE;
        END;
        PERFORM academic_package_fixture.check(observed = '23514', 'unrelated dated term cannot borrow named or pinned-old-term applicability');
    END LOOP;
    observed := NULL;
    BEGIN
        PERFORM public.manage_academic_master_record(admin, tenant, 'course_offerings', NULL,
            payload || jsonb_build_object('course_id', outside_subject));
    EXCEPTION WHEN OTHERS THEN observed := SQLSTATE;
    END;
    PERFORM academic_package_fixture.check(observed = '23514', 'unlisted subject remains ineligible in otherwise valid class term');
    PERFORM academic_package_fixture.check(EXISTS (SELECT 1 FROM pg_catalog.pg_constraint
        WHERE conrelid = 'public.course_offerings'::regclass AND confrelid = 'public.programs'::regclass AND contype = 'f')
        AND EXISTS (SELECT 1 FROM pg_catalog.pg_constraint WHERE conrelid = 'public.course_offerings'::regclass
            AND confrelid = 'public.courses'::regclass AND contype = 'f'), 'independent subject and program foreign keys remain intact');
END;
$$;
SELECT 'PASS: named-only curriculum offerings and pinned-old-term reuse without duplicate legacy links or widened authority' AS result;
