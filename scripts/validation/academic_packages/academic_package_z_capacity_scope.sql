SET request.jwt.claim.role = 'service_role';
DO $$
#variable_conflict use_variable
DECLARE tenant uuid := academic_package_fixture.id('tenant'); admin uuid := academic_package_fixture.id('admin');
    faculty uuid := academic_package_fixture.id('faculty'); class_id uuid := academic_package_fixture.id('class');
    abc uuid := academic_package_fixture.id('package_abc'); efg uuid := academic_package_fixture.id('package_efg');
    registration uuid; placement uuid; item jsonb; before_count integer; label text; reason text; observed text;
    hod uuid; incharge uuid; faculty_user uuid := gen_random_uuid(); auth_id uuid := gen_random_uuid(); org uuid;
    late_student uuid := gen_random_uuid(); late_auth uuid := gen_random_uuid(); policy jsonb;
BEGIN
    UPDATE public.sections SET capacity = 1 WHERE section_id = academic_package_fixture.id('section_E');
    FOREACH label IN ARRAY ARRAY['SECOND','THIRD'] LOOP
        INSERT INTO public.student_registrations(institution_id, program_id, academic_year_id, semester_id, section_code,
            batch_id, batch_start_year, batch_end_year, register_number, university_roll_number, student_name, email, created_by)
        SELECT tenant, b.program_id, academic_package_fixture.id('year'), academic_package_fixture.id('term'), 'A',
            b.batch_id, b.start_year, b.end_year, 'PKG-' || label, 'ROLL-' || label,
            label || ' Contract', lower(label) || '@example.invalid', admin
        FROM public.academic_batches b WHERE b.batch_id = academic_package_fixture.id('batch') RETURNING registration_id INTO registration;
        item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id, 'registration_id', registration));
        placement := (item->>'placement_id')::uuid;
        INSERT INTO academic_package_fixture.ids VALUES ('placement_' || label, placement);
        IF label = 'SECOND' THEN
            item := academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', efg));
            PERFORM academic_package_fixture.check((item->>'revision')::integer = 1, 'late initial assignment remains permitted');
        ELSE
            SELECT count(*) INTO before_count FROM public.faculty_attendance_rosters WHERE institution_id = tenant;
            PERFORM academic_package_fixture.expect_error('assign_package', jsonb_build_object('placement_id', placement, 'package_id', efg), 'admin', '23514');
            PERFORM academic_package_fixture.check((SELECT count(*) = before_count FROM public.faculty_attendance_rosters WHERE institution_id = tenant), 'capacity failure rolls back every target roster');
            PERFORM academic_package_fixture.check(NOT EXISTS (SELECT 1 FROM public.academic_package_assignments WHERE placement_id = placement), 'capacity failure leaves no assignment');
        END IF;
    END LOOP;
    PERFORM public.phase81_manage_staff_permission_grants(admin, tenant, academic_package_fixture.id('staff'), ARRAY['academic.package.assign'], false);
    PERFORM academic_package_fixture.expect_error('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc), 'staff', '42501');
    INSERT INTO public.faculty_responsibilities(institution_id, faculty_user_id, responsibility_code, scope_type, scope_id, start_at, created_by)
    VALUES (tenant, faculty, 'hod', 'department', academic_package_fixture.id('department'), clock_timestamp() - interval '1 hour', admin)
    RETURNING responsibility_id INTO hod;
    item := academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc), 'faculty');
    PERFORM academic_package_fixture.check((item->>'revision')::integer = 1, 'HOD can assign within the program department');
    PERFORM academic_package_fixture.check((SELECT count(DISTINCT a.package_id) = 2 FROM public.academic_package_assignments a
        JOIN public.academic_class_placements cp USING(placement_id) WHERE cp.class_id = class_id), 'one shared class supports different complete packages');
    SELECT organization_id INTO org FROM public.institutions WHERE institution_id = tenant;
    INSERT INTO auth.users(id, email) VALUES (auth_id, faculty_user || '@example.invalid');
    INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
    VALUES (faculty_user, auth_id, faculty_user || '@example.invalid', 'Class', 'Incharge');
    INSERT INTO public.user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
    SELECT faculty_user, id, 'institution', tenant, org FROM public.roles WHERE name = 'faculty';
    INSERT INTO public.faculty_responsibilities(institution_id, faculty_user_id, responsibility_code, scope_type, scope_id, start_at, created_by)
    VALUES (tenant, faculty_user, 'class_in_charge', 'section', academic_package_fixture.id('section_DSA'), clock_timestamp() - interval '1 hour', admin)
    RETURNING responsibility_id INTO incharge;
    PERFORM academic_package_fixture.check(NOT public.academic_package_allowed(faculty_user, tenant,
        'academic.package.assign', class_id), 'section tuple alone does not grant batch-specific class authority');
    PERFORM academic_package_fixture.command('set_class_responsibility', jsonb_build_object('class_id', class_id, 'responsibility_id', incharge, 'enabled', true));
    PERFORM academic_package_fixture.check(public.academic_package_allowed(faculty_user, tenant,
        'academic.package.assign', class_id), 'explicit bridge enables scoped class-incharge authority');
    UPDATE public.faculty_responsibilities SET revoked_at = clock_timestamp(), revoked_by = admin WHERE responsibility_id = incharge;
    PERFORM academic_package_fixture.check(NOT public.academic_package_allowed(faculty_user, tenant,
        'academic.package.assign', class_id), 'revoked class responsibility is ineffective immediately');
    item := public.academic_package_catalogue(academic_package_fixture.id('student'), tenant);
    PERFORM academic_package_fixture.check(jsonb_array_length(item->'records'->'placements') = 1, 'student cannot see classmates placements');
    PERFORM academic_package_fixture.check(jsonb_array_length(item->'options'->'registrations') = 1, 'student cannot see classmates registration details');
    BEGIN
        PERFORM public.academic_package_catalogue(admin, gen_random_uuid());
    EXCEPTION WHEN OTHERS THEN observed := SQLSTATE;
    END;
    PERFORM academic_package_fixture.check(observed = '42501', 'foreign institution context rejected');
    INSERT INTO auth.users(id, email) VALUES (late_auth, late_student || '@example.invalid');
    INSERT INTO public.users(id, auth_user_id, email, first_name, last_name)
    VALUES (late_student, late_auth, late_student || '@example.invalid', 'Late', 'Student');
    INSERT INTO public.user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
    SELECT late_student, id, 'institution', tenant, org FROM public.roles WHERE name = 'student';
    INSERT INTO public.students(user_id, institution_id, student_number, register_number, university_roll_number,
        email, program_id, academic_year_id, enrollment_date, approval_status)
    VALUES (late_student, tenant, 'PKG-LATE', 'PKG-LATE', 'ROLL-LATE', late_student || '@example.invalid',
        academic_package_fixture.id('program'), academic_package_fixture.id('year'), current_date, 'approved');
    INSERT INTO public.student_registrations(institution_id, program_id, academic_year_id, semester_id, section_code,
        batch_id, batch_start_year, batch_end_year, register_number, university_roll_number, student_name, email, created_by)
    SELECT tenant, b.program_id, academic_package_fixture.id('year'), academic_package_fixture.id('term'), 'A',
        b.batch_id, b.start_year, b.end_year, 'PKG-LATE', 'ROLL-LATE', 'Late Student', late_student || '@example.invalid', admin
    FROM public.academic_batches b WHERE b.batch_id = academic_package_fixture.id('batch') RETURNING registration_id INTO registration;
    item := academic_package_fixture.command('place_student', jsonb_build_object('class_id', class_id, 'registration_id', registration));
    placement := (item->>'placement_id')::uuid;
    INSERT INTO academic_package_fixture.ids VALUES ('late_student', late_student);
    SELECT to_jsonb(c) || jsonb_build_object('program_id', academic_package_fixture.id('program'), 'student_choice_enabled', true)
    INTO policy FROM public.academic_classes c WHERE c.class_id = class_id;
    PERFORM academic_package_fixture.command('save_class', policy);
    item := academic_package_fixture.command('assign_package', jsonb_build_object('placement_id', placement, 'package_id', abc), 'late_student');
    PERFORM academic_package_fixture.check((item->>'revision')::integer = 1, 'enabled own initial selection works independently of later-change cutoff');
    PERFORM academic_package_fixture.expect_error('assign_package', jsonb_build_object('placement_id', placement, 'package_id', efg), 'late_student', '42501');
    PERFORM academic_package_fixture.expect_error('request_change', jsonb_build_object('assignment_id', item->>'assignment_id',
        'package_id', efg, 'reason', 'Initial choice flag cannot reopen changes'), 'late_student', '23514');
END;
$$;
SELECT 'PASS: late initial assignment, capacity rollback, staff revocation, scoped HOD/class-incharge and student privacy' AS result;
