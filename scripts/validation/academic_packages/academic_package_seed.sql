-- Disposable PostgreSQL contract fixtures only; never a deployment migration.
SET request.jwt.claim.role = 'service_role';
CREATE SCHEMA academic_package_fixture;
CREATE TABLE academic_package_fixture.ids (name text PRIMARY KEY, value uuid NOT NULL);
CREATE FUNCTION academic_package_fixture.id(p_name text) RETURNS uuid LANGUAGE sql AS $$
    SELECT value FROM academic_package_fixture.ids WHERE name = p_name;
$$;
CREATE FUNCTION academic_package_fixture.check(p_condition boolean, p_message text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    IF p_condition IS DISTINCT FROM true THEN RAISE EXCEPTION 'Contract failed: %', p_message; END IF;
END;
$$;
CREATE FUNCTION academic_package_fixture.command(p_operation text, p_payload jsonb, p_actor text DEFAULT 'admin')
RETURNS jsonb LANGUAGE sql AS $$
    SELECT public.academic_package_command(academic_package_fixture.id(p_actor),
        academic_package_fixture.id('tenant'), p_operation, p_payload);
$$;
CREATE FUNCTION academic_package_fixture.expect_error(p_operation text, p_payload jsonb, p_actor text, p_state text)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE observed text;
BEGIN
    BEGIN
        PERFORM academic_package_fixture.command(p_operation, p_payload, p_actor);
    EXCEPTION WHEN OTHERS THEN observed := SQLSTATE;
    END;
    PERFORM academic_package_fixture.check(observed = p_state,
        p_operation || ' expected ' || p_state || ', observed ' || COALESCE(observed, 'success'));
END;
$$;

DO $$
DECLARE tenant uuid := gen_random_uuid(); actor uuid; auth_id uuid; org uuid; department uuid;
    program uuid; year_id uuid; term uuid; batch uuid; subject uuid; offering uuid; section_id uuid;
    curriculum uuid; package_abc uuid; package_efg uuid; class_id uuid; registration uuid; placement uuid;
    item jsonb; members_abc uuid[] := '{}'; members_efg uuid[] := '{}'; subject_link uuid;
    label text; student_user uuid; faculty_user uuid;
BEGIN
    SELECT organization_id INTO org FROM public.organizations WHERE organization_code = 'COLLEGE-AI-PLATFORM';
    INSERT INTO public.institutions(institution_id, organization_id, name, code, status)
    VALUES (tenant, org, 'Package contract institution', 'PKG-' || upper(left(tenant::text, 8)), 'active');
    INSERT INTO academic_package_fixture.ids VALUES ('tenant', tenant);
    FOREACH label IN ARRAY ARRAY['admin','student','faculty','staff'] LOOP
        auth_id := gen_random_uuid(); actor := gen_random_uuid();
        INSERT INTO auth.users(id, email) VALUES (auth_id, label || '-' || actor || '@example.invalid');
        INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
        VALUES (actor, auth_id, label || '-' || actor || '@example.invalid', label, 'Contract');
        INSERT INTO public.user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
        SELECT actor, id, 'institution', tenant, org FROM public.roles WHERE name = label;
        INSERT INTO academic_package_fixture.ids VALUES (label, actor);
        IF label = 'student' THEN student_user := actor; END IF;
        IF label = 'faculty' THEN faculty_user := actor; END IF;
    END LOOP;
    actor := academic_package_fixture.id('admin');
    INSERT INTO public.departments(institution_id, name, code) VALUES (tenant, 'Computer Science', 'CSE') RETURNING department_id INTO department;
    INSERT INTO public.programs(department_id, name, code, degree_type, duration_years)
    VALUES (department, 'Computer Science Engineering', 'CSE', 'B.Tech', 4) RETURNING program_id INTO program;
    INSERT INTO public.academic_years(institution_id, name, code, start_date, end_date)
    VALUES (tenant, 'Contract academic year', 'CONTRACT', current_date - 50, current_date + 200) RETURNING academic_year_id INTO year_id;
    INSERT INTO public.semesters(academic_year_id, name, code, semester_number, start_date, end_date)
    VALUES (year_id, 'Calendar Term 1', 'T1', 1, current_date - 14, current_date + 85) RETURNING semester_id INTO term;
    INSERT INTO public.academic_batches(institution_id, program_id, start_year, end_year)
    VALUES (tenant, program, extract(year FROM current_date)::integer, extract(year FROM current_date)::integer + 4) RETURNING batch_id INTO batch;
    INSERT INTO academic_package_fixture.ids VALUES ('program', program), ('department', department), ('year', year_id), ('term', term), ('batch', batch);
    INSERT INTO public.students(user_id, institution_id, student_number, register_number, university_roll_number,
        email, program_id, academic_year_id, enrollment_date, approval_status)
    SELECT student_user, tenant, 'PKG-REG', 'PKG-REG', 'PKG-ROLL', email, program, year_id, current_date, 'approved'
    FROM public.users WHERE id = student_user;
    INSERT INTO public.student_registrations(institution_id, program_id, academic_year_id, semester_id, section_code,
        batch_id, batch_start_year, batch_end_year, register_number, university_roll_number, student_name, email, created_by)
    SELECT tenant, program, year_id, term, 'A', batch, start_year, end_year,
        'PKG-REG', 'PKG-ROLL', 'Student Contract', u.email, actor
    FROM public.academic_batches b CROSS JOIN public.users u WHERE b.batch_id = batch AND u.id = student_user
    RETURNING registration_id INTO registration;
    INSERT INTO academic_package_fixture.ids VALUES ('registration', registration);
    item := academic_package_fixture.command('save_curriculum', jsonb_build_object('program_id', program,
        'name', 'CSE Curriculum', 'code', 'CSE-PLAN', 'version', 1));
    curriculum := (item->>'curriculum_id')::uuid;
    INSERT INTO academic_package_fixture.ids VALUES ('curriculum', curriculum);
    FOREACH label IN ARRAY ARRAY['DSA','ML','A','B','C','E','F','G'] LOOP
        INSERT INTO public.courses(department_id, name, code) VALUES (department, label, label) RETURNING course_id INTO subject;
        INSERT INTO public.program_courses(program_id, course_id, course_type) VALUES (program, subject, 'core');
        INSERT INTO public.course_offerings(course_id, program_id, academic_year_id, semester_id, capacity)
        VALUES (subject, program, year_id, term, 10) RETURNING course_offering_id INTO offering;
        INSERT INTO public.sections(course_offering_id, name, code, capacity) VALUES (offering, label || ' teaching group', 'A', 10)
        RETURNING public.sections.section_id INTO section_id;
        INSERT INTO academic_package_fixture.ids VALUES ('section_' || label, section_id);
        INSERT INTO public.faculty_section_assignments(institution_id, faculty_user_id, section_id, assigned_by)
        VALUES (tenant, faculty_user, section_id, actor);
        item := academic_package_fixture.command('set_curriculum_subject', jsonb_build_object('curriculum_id', curriculum,
            'course_id', subject, 'study_semester', 3, 'course_type', CASE WHEN label IN ('DSA','ML') THEN 'core' ELSE 'elective' END,
            'is_core', label IN ('DSA','ML')));
        subject_link := (item->>'curriculum_subject_id')::uuid;
        INSERT INTO academic_package_fixture.ids VALUES ('subject_' || label, subject_link);
        IF label IN ('A','B','C') THEN members_abc := array_append(members_abc, subject_link); END IF;
        IF label IN ('E','F','G') THEN members_efg := array_append(members_efg, subject_link); END IF;
    END LOOP;
    item := academic_package_fixture.command('save_package', jsonb_build_object('curriculum_id', curriculum,
        'study_semester', 3, 'name', 'ABC Package', 'code', 'ABC', 'curriculum_subject_ids', to_jsonb(members_abc)));
    package_abc := (item->>'package_id')::uuid;
    item := academic_package_fixture.command('save_package', jsonb_build_object('curriculum_id', curriculum,
        'study_semester', 3, 'name', 'EFG Package', 'code', 'EFG', 'curriculum_subject_ids', to_jsonb(members_efg)));
    package_efg := (item->>'package_id')::uuid;
    INSERT INTO academic_package_fixture.ids VALUES ('package_abc', package_abc), ('package_efg', package_efg);
    item := academic_package_fixture.command('save_class', jsonb_build_object('program_id', program, 'batch_id', batch,
        'semester_id', term, 'study_semester', 3, 'section_code', 'A', 'curriculum_id', curriculum, 'student_choice_enabled', false));
    class_id := (item->>'class_id')::uuid;
    INSERT INTO academic_package_fixture.ids VALUES ('class', class_id);
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id, 'package_id', package_abc, 'enabled', true));
    PERFORM academic_package_fixture.command('set_class_package', jsonb_build_object('class_id', class_id, 'package_id', package_efg, 'enabled', true));
    FOREACH label IN ARRAY ARRAY['DSA','ML','A','B','C','E','F','G'] LOOP
        PERFORM academic_package_fixture.command('set_class_subject', jsonb_build_object('class_id', class_id,
            'curriculum_subject_id', academic_package_fixture.id('subject_' || label), 'section_id', academic_package_fixture.id('section_' || label)));
    END LOOP;
    item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id, 'registration_id', registration));
    placement := (item->>'placement_id')::uuid;
    INSERT INTO academic_package_fixture.ids VALUES ('placement', placement);
END;
$$;
SELECT 'PASS: fixture prerequisites use ordinary guarded identities and academic masters' AS result;
