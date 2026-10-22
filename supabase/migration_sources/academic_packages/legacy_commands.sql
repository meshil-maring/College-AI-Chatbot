CREATE FUNCTION public.academic_legacy_section_authorize(p_actor uuid, p_tenant uuid, p_section uuid, p_permission text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE role_name text; context jsonb;
BEGIN
    role_name := public.academic_package_actor(p_actor, p_tenant);
    IF role_name = 'faculty' AND p_permission = 'attendance.manage' THEN
        RETURN public.assert_faculty_attendance_mutation(p_actor, p_tenant, p_section);
    END IF;
    IF role_name NOT IN ('admin','staff') OR p_permission NOT IN ('students.create','attendance.manage') THEN
        RAISE EXCEPTION 'Legacy membership mutation denied' USING ERRCODE = '42501';
    END IF;
    PERFORM public.academic_package_require(p_actor, p_tenant, p_permission);
    SELECT jsonb_build_object('course_offering_id', o.course_offering_id, 'program_id', o.program_id,
        'academic_year_id', o.academic_year_id, 'semester_id', o.semester_id,
        'section_code', sec.code, 'semester_number', s.semester_number) INTO context
    FROM public.sections sec JOIN public.course_offerings o USING(course_offering_id)
    JOIN public.courses c USING(course_id) JOIN public.departments d USING(department_id)
    JOIN public.programs p ON p.program_id = o.program_id
    JOIN public.departments pd ON pd.department_id = p.department_id
    JOIN public.semesters s ON s.semester_id = o.semester_id JOIN public.academic_years y ON y.academic_year_id = o.academic_year_id
    WHERE sec.section_id = p_section AND d.institution_id = p_tenant AND pd.institution_id = p_tenant
      AND y.institution_id = p_tenant AND s.academic_year_id = y.academic_year_id
      AND sec.is_active AND o.is_active AND c.is_active AND d.is_active AND p.is_active AND pd.is_active AND s.is_active AND y.is_active
    FOR SHARE OF sec, o, c, d, p, pd, s, y;
    IF context IS NULL THEN RAISE EXCEPTION 'Active teaching section required' USING ERRCODE = '42501'; END IF;
    RETURN context;
END;
$$;

CREATE FUNCTION public.assign_student_subject(p_actor_user_id uuid, p_institution_id uuid,
    p_section_id uuid, p_registration_id uuid, p_permission text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE context jsonb; registration public.student_registrations; identity jsonb;
    roster public.faculty_attendance_rosters; linked uuid; state text; result jsonb; semester_number integer;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('attendance:' || p_institution_id::text, 0));
    context := public.academic_legacy_section_authorize(p_actor_user_id, p_institution_id, p_section_id, p_permission);
    IF EXISTS (SELECT 1 FROM public.academic_class_subjects WHERE section_id = p_section_id) THEN
        RAISE EXCEPTION 'Use complete package assignment for this teaching group' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO registration FROM public.student_registrations
    WHERE registration_id = p_registration_id AND institution_id = p_institution_id
      AND program_id = (context->>'program_id')::uuid AND academic_year_id = (context->>'academic_year_id')::uuid
      AND semester_id = (context->>'semester_id')::uuid
      AND section_code = (SELECT code FROM public.sections WHERE section_id = p_section_id) FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Student registration unavailable in this class' USING ERRCODE = 'P0002'; END IF;
    identity := public.faculty_attendance_identity(p_institution_id, registration.register_number, registration.university_roll_number);
    IF COALESCE((identity->>'conflict')::boolean, true)
        OR (identity->>'program_id' IS NOT NULL AND identity->>'program_id' <> context->>'program_id')
        OR (identity->>'academic_year_id' IS NOT NULL AND identity->>'academic_year_id' <> context->>'academic_year_id') THEN
        RAISE EXCEPTION 'Student academic identity conflicts with this class' USING ERRCODE = '23514';
    END IF;
    SELECT s.semester_number INTO semester_number FROM public.semesters s WHERE s.semester_id = (context->>'semester_id')::uuid;
    IF semester_number <> 1 AND registration.university_roll_number IS NULL THEN
        RAISE EXCEPTION 'University roll number required after first semester' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO roster FROM public.faculty_attendance_rosters
    WHERE institution_id = p_institution_id AND section_id = p_section_id
      AND (register_number = registration.register_number
        OR (registration.university_roll_number IS NOT NULL AND university_roll_number = registration.university_roll_number))
    ORDER BY roster_id LIMIT 1 FOR UPDATE;
    IF roster.roster_id IS NOT NULL THEN
        IF roster.register_number <> registration.register_number OR roster.reconciliation_state = 'CONFLICT'
            OR (roster.university_roll_number IS NOT NULL AND registration.university_roll_number IS NOT NULL
                AND roster.university_roll_number <> registration.university_roll_number)
            OR (roster.linked_student_id IS NOT NULL AND roster.linked_student_id IS DISTINCT FROM (identity->>'student_id')::uuid)
            OR EXISTS (SELECT 1 FROM public.faculty_attendance_rosters r
                WHERE r.section_id = p_section_id AND r.roster_id <> roster.roster_id
                  AND (r.register_number = registration.register_number
                    OR (registration.university_roll_number IS NOT NULL AND r.university_roll_number = registration.university_roll_number))) THEN
            RAISE EXCEPTION 'Existing subject identity conflict' USING ERRCODE = '23514';
        END IF;
        RETURN jsonb_build_object('registration_id', p_registration_id, 'roster_id', roster.roster_id, 'status', 'already_assigned');
    END IF;
    linked := CASE WHEN identity->>'approval_status' = 'approved' THEN (identity->>'student_id')::uuid END;
    state := CASE WHEN identity->>'student_id' IS NULL THEN 'UNREGISTERED' WHEN linked IS NULL THEN 'PENDING_APPROVAL'
        WHEN (identity->>'is_active')::boolean AND identity->>'status' = 'active' THEN 'ACTIVE' ELSE 'INACTIVE' END;
    INSERT INTO public.faculty_attendance_rosters(institution_id, section_id, course_offering_id, semester_id,
        register_number, university_roll_number, student_name, email, created_by, linked_student_id, roster_status, reconciliation_state)
    VALUES (p_institution_id, p_section_id, (context->>'course_offering_id')::uuid, (context->>'semester_id')::uuid,
        registration.register_number, registration.university_roll_number, registration.student_name, registration.email,
        p_actor_user_id, linked, state, CASE WHEN linked IS NOT NULL THEN 'LINKED'
            WHEN identity->>'student_id' IS NOT NULL THEN 'PENDING' ELSE 'NONE' END) RETURNING * INTO roster;
    result := jsonb_build_object('registration_id', p_registration_id, 'roster_id', roster.roster_id, 'status', 'assigned');
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor_user_id, p_institution_id, 'students.subject.assign', 'faculty_attendance_rosters',
        roster.roster_id::text, to_jsonb(roster) || result);
    RETURN result;
END;
$$;

CREATE FUNCTION public.delete_academic_roster(p_actor_user_id uuid, p_institution_id uuid, p_roster_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE roster public.faculty_attendance_rosters;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('attendance:' || p_institution_id::text, 0));
    SELECT * INTO roster FROM public.faculty_attendance_rosters
    WHERE roster_id = p_roster_id AND institution_id = p_institution_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Roster not found' USING ERRCODE = 'P0002'; END IF;
    PERFORM public.academic_legacy_section_authorize(p_actor_user_id, p_institution_id, roster.section_id, 'attendance.manage');
    IF EXISTS (SELECT 1 FROM public.academic_class_subjects WHERE section_id = roster.section_id)
        OR EXISTS (SELECT 1 FROM public.academic_subject_participation WHERE roster_id = p_roster_id)
        OR EXISTS (SELECT 1 FROM public.faculty_attendance_records WHERE roster_id = p_roster_id)
        OR EXISTS (SELECT 1 FROM public.test_results WHERE roster_id = p_roster_id) THEN
        RAISE EXCEPTION 'Roster has academic history or package membership' USING ERRCODE = '23514';
    END IF;
    DELETE FROM public.faculty_attendance_rosters WHERE roster_id = p_roster_id;
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor_user_id, p_institution_id, 'attendance.roster.delete', 'faculty_attendance_rosters',
        p_roster_id::text, to_jsonb(roster));
    RETURN jsonb_build_object('roster_id', p_roster_id, 'deleted', true);
END;
$$;
