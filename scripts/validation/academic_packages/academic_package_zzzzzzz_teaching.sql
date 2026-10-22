SET request.jwt.claim.role = 'service_role';
DO $$
#variable_conflict use_variable
DECLARE tenant uuid := academic_package_fixture.id('tenant'); admin uuid := academic_package_fixture.id('admin');
    program uuid := academic_package_fixture.id('program'); year_id uuid; term uuid; curriculum uuid; class_id uuid;
    subject uuid; link uuid; package_id uuid; disabled_package uuid; label text; item jsonb; result jsonb;
    core_link uuid; core_section uuid; core_offering uuid; reused_offering uuid; inactive_subject uuid;
    elective_links uuid[] := '{}'; target_links uuid[] := '{}'; disabled_link uuid; placement uuid;
    offering_count integer; section_count integer; audit_count integer; mappings jsonb;
BEGIN
    INSERT INTO public.academic_years(institution_id, name, code, start_date, end_date)
    VALUES (tenant, 'Automatic teaching year', 'PREP-YEAR', current_date + 1001, current_date + 1400)
    RETURNING academic_year_id INTO year_id;
    INSERT INTO public.semesters(academic_year_id, name, code, semester_number, start_date, end_date)
    VALUES (year_id, 'Automatic teaching term', 'PREP-T1', 1, current_date + 1001, current_date + 1100)
    RETURNING semester_id INTO term;
    item := academic_package_fixture.command('save_curriculum', jsonb_build_object('program_id', program,
        'name', 'Automatic Teaching Curriculum', 'code', 'AUTO-PLAN', 'version', 4));
    curriculum := (item->>'curriculum_id')::uuid;
    FOREACH label IN ARRAY ARRAY['CORE','ONE','TWO','DISABLED'] LOOP
        INSERT INTO public.courses(department_id, name, code)
        VALUES (academic_package_fixture.id('department'), 'Automatic ' || label, 'AUTO-' || label) RETURNING course_id INTO subject;
        item := academic_package_fixture.command('set_curriculum_subject', jsonb_build_object('curriculum_id', curriculum,
            'course_id', subject, 'study_semester', 7, 'course_type', CASE WHEN label = 'CORE' THEN 'core' ELSE 'elective' END,
            'is_core', label = 'CORE'));
        link := (item->>'curriculum_subject_id')::uuid;
        IF label = 'CORE' THEN core_link := link;
        ELSIF label = 'DISABLED' THEN disabled_link := link;
        ELSE elective_links := array_append(elective_links, link); END IF;
        IF label <> 'DISABLED' THEN target_links := array_append(target_links, link); END IF;
    END LOOP;
    item := academic_package_fixture.command('save_package', jsonb_build_object('curriculum_id', curriculum,
        'study_semester', 7, 'name', 'Automatic teaching package', 'code', 'AUTO', 'curriculum_subject_ids', to_jsonb(elective_links)));
    package_id := (item->>'package_id')::uuid;
    item := academic_package_fixture.command('save_package', jsonb_build_object('curriculum_id', curriculum,
        'study_semester', 7, 'name', 'Disabled package', 'code', 'DISABLED', 'curriculum_subject_ids', jsonb_build_array(disabled_link)));
    disabled_package := (item->>'package_id')::uuid;
    item := academic_package_fixture.command('save_class', jsonb_build_object('program_id', program,
        'batch_id', academic_package_fixture.id('batch'), 'semester_id', term, 'study_semester', 7,
        'section_code', 'AUTO', 'curriculum_id', curriculum, 'student_choice_enabled', false));
    class_id := (item->>'class_id')::uuid;
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id, 'package_id', package_id, 'enabled', true));
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id,
        'package_id', disabled_package, 'enabled', false));
    SELECT cs.course_id INTO subject FROM public.academic_curriculum_subjects cs WHERE cs.curriculum_subject_id = core_link;
    item := public.manage_academic_master_record(admin, tenant, 'course_offerings', NULL,
        jsonb_build_object('program_id', program, 'course_id', subject, 'academic_year_id', year_id, 'semester_id', term));
    core_offering := (item->>'course_offering_id')::uuid;
    item := public.manage_academic_master_record(admin, tenant, 'sections', NULL,
        jsonb_build_object('course_offering_id', core_offering, 'name', 'Preserved manual group', 'code', 'MANUAL'));
    core_section := (item->>'section_id')::uuid;
    PERFORM academic_package_fixture.command('set_class_subject', jsonb_build_object('class_id', class_id,
        'curriculum_subject_id', core_link, 'section_id', core_section));
    SELECT cs.course_id INTO subject FROM public.academic_curriculum_subjects cs WHERE cs.curriculum_subject_id = elective_links[1];
    item := public.manage_academic_master_record(admin, tenant, 'course_offerings', NULL,
        jsonb_build_object('program_id', program, 'course_id', subject, 'academic_year_id', year_id, 'semester_id', term));
    reused_offering := (item->>'course_offering_id')::uuid;
    FOREACH label IN ARRAY ARRAY['student','faculty','staff'] LOOP
        PERFORM academic_package_fixture.expect_error('prepare_class_teaching', jsonb_build_object('class_id', class_id), label, '42501');
    END LOOP;
    UPDATE public.permissions SET is_active = false WHERE code = 'courses.manage';
    PERFORM academic_package_fixture.expect_error('prepare_class_teaching', jsonb_build_object('class_id', class_id), 'admin', '42501');
    PERFORM academic_package_fixture.check(NOT (public.academic_package_catalogue(admin, tenant)->'capabilities' ? 'prepare_teaching'),
        'automatic teaching capability requires existing course management permission');
    UPDATE public.permissions SET is_active = true WHERE code = 'courses.manage';
    UPDATE public.permissions SET is_active = false WHERE code = 'academic.class.manage';
    PERFORM academic_package_fixture.expect_error('prepare_class_teaching', jsonb_build_object('class_id', class_id), 'admin', '42501');
    UPDATE public.permissions SET is_active = true WHERE code = 'academic.class.manage';
    SELECT count(*) INTO offering_count FROM public.course_offerings o WHERE o.program_id = program AND o.semester_id = term;
    SELECT count(*) INTO section_count FROM public.sections s JOIN public.course_offerings o USING(course_offering_id)
    WHERE o.program_id = program AND o.semester_id = term;
    SELECT count(*) INTO audit_count FROM public.admin_audit_log WHERE institution_id = tenant;
    SELECT cs.course_id INTO inactive_subject FROM public.academic_curriculum_subjects cs
    WHERE cs.curriculum_subject_id = ANY(target_links) ORDER BY cs.curriculum_subject_id DESC LIMIT 1;
    UPDATE public.courses SET is_active = false WHERE course_id = inactive_subject;
    PERFORM academic_package_fixture.expect_error('prepare_class_teaching', jsonb_build_object('class_id', class_id), 'admin', '23514');
    PERFORM academic_package_fixture.check((SELECT count(*) = offering_count FROM public.course_offerings o
        WHERE o.program_id = program AND o.semester_id = term), 'late inactive subject rolls back every newly prepared offering');
    PERFORM academic_package_fixture.check((SELECT count(*) = section_count FROM public.sections s
        JOIN public.course_offerings o USING(course_offering_id) WHERE o.program_id = program AND o.semester_id = term),
        'late failure rolls back every new teaching section');
    PERFORM academic_package_fixture.check((SELECT count(*) = audit_count FROM public.admin_audit_log WHERE institution_id = tenant),
        'failed preparation rolls back all nested master and mapping audits');
    UPDATE public.courses SET is_active = true WHERE course_id = inactive_subject;
    result := academic_package_fixture.command('prepare_class_teaching', jsonb_build_object('class_id', class_id));
    PERFORM academic_package_fixture.check((result->>'prepared_subjects')::integer = 3
        AND (result->>'created_offerings')::integer = 1 AND (result->>'created_sections')::integer = 2
        AND (result->>'mapped_subjects')::integer = 2, 'preparation reuses offerings and manual maps and creates only missing teaching');
    PERFORM academic_package_fixture.check((SELECT cs.section_id = core_section FROM public.academic_class_subjects cs
        WHERE cs.class_id = class_id AND cs.curriculum_subject_id = core_link), 'manual teaching mapping remains unchanged');
    PERFORM academic_package_fixture.check(NOT EXISTS (SELECT 1 FROM public.academic_class_subjects cs
        WHERE cs.class_id = class_id AND cs.curriculum_subject_id = disabled_link), 'disabled package subject receives no teaching mapping');
    SELECT jsonb_agg(cs ORDER BY cs.curriculum_subject_id) INTO mappings FROM public.academic_class_subjects cs WHERE cs.class_id = class_id;
    result := academic_package_fixture.command('prepare_class_teaching', jsonb_build_object('class_id', class_id));
    PERFORM academic_package_fixture.check((result->>'created_offerings')::integer = 0 AND (result->>'created_sections')::integer = 0
        AND (result->>'mapped_subjects')::integer = 0 AND (SELECT jsonb_agg(cs ORDER BY cs.curriculum_subject_id) = mappings
            FROM public.academic_class_subjects cs WHERE cs.class_id = class_id), 'retry preserves all identifiers without duplicate structure');
    PERFORM academic_package_fixture.check(public.academic_package_catalogue(admin, tenant)->'capabilities' ? 'prepare_teaching',
        'authorized administrator sees preparation capability');
    item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id,
        'registration_id', academic_package_fixture.id('registration')));
    placement := (item->>'placement_id')::uuid;
    PERFORM academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', package_id));
    PERFORM academic_package_fixture.check((SELECT count(*) = 3 FROM public.academic_subject_participation sp
        WHERE sp.placement_id = placement AND sp.ended_at IS NULL), 'prepared class supports complete atomic assignment without manual offering screens');
    UPDATE public.sections SET is_active = false WHERE public.sections.section_id = core_section;
    PERFORM academic_package_fixture.expect_error('prepare_class_teaching', jsonb_build_object('class_id', class_id), 'admin', '23514');
    UPDATE public.sections SET is_active = true WHERE public.sections.section_id = core_section;
END;
$$;
SELECT 'PASS: automatic class teaching, old/new RBAC, atomic rollback, manual mappings, idempotency and complete assignment' AS result;
