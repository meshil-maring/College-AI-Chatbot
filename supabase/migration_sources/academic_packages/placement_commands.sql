CREATE FUNCTION public.academic_package_place(p_actor uuid, p_tenant uuid, p_payload jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE class_row public.academic_classes; registration public.student_registrations;
    batch public.academic_batches; identity jsonb; item uuid; result jsonb;
BEGIN
    SELECT * INTO class_row FROM public.academic_classes
    WHERE class_id = (p_payload->>'class_id')::uuid AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Class not found' USING ERRCODE = 'P0002'; END IF;
    PERFORM public.academic_package_require(p_actor, p_tenant, 'academic.package.assign', class_row.class_id);
    PERFORM 1 FROM public.academic_classes c JOIN public.academic_batches b USING(batch_id)
    JOIN public.programs p USING(program_id) JOIN public.departments d USING(department_id)
    JOIN public.semesters s ON s.semester_id = c.semester_id JOIN public.academic_years y USING(academic_year_id)
    WHERE c.class_id = class_row.class_id AND b.is_active AND p.is_active AND d.is_active
      AND s.is_active AND y.is_active AND y.institution_id = p_tenant FOR SHARE OF b, p, d, s, y;
    IF NOT FOUND THEN RAISE EXCEPTION 'Active class academic context required' USING ERRCODE = '23514'; END IF;
    SELECT * INTO batch FROM public.academic_batches WHERE batch_id = class_row.batch_id AND is_active FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Class batch unavailable' USING ERRCODE = '23514'; END IF;
    SELECT * INTO registration FROM public.student_registrations
    WHERE registration_id = (p_payload->>'registration_id')::uuid AND institution_id = p_tenant
      AND batch_id = batch.batch_id AND program_id = batch.program_id FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Matching batch registration required' USING ERRCODE = '23514'; END IF;
    IF EXISTS (SELECT 1 FROM public.academic_class_placements cp JOIN public.academic_classes c USING(class_id)
        WHERE cp.registration_id = registration.registration_id
          AND tstzrange(c.teaching_start, c.teaching_end, '[)')
              && tstzrange(class_row.teaching_start, class_row.teaching_end, '[)')
          AND c.class_id <> class_row.class_id) THEN
        RAISE EXCEPTION 'Student already placed in an overlapping teaching period' USING ERRCODE = '23514';
    END IF;
    identity := public.faculty_attendance_identity(p_tenant, registration.register_number, registration.university_roll_number);
    IF COALESCE((identity->>'conflict')::boolean, true)
        OR (identity->>'program_id' IS NOT NULL AND (identity->>'program_id')::uuid <> batch.program_id) THEN
        RAISE EXCEPTION 'Registration identity requires review' USING ERRCODE = '23514';
    END IF;
    INSERT INTO public.academic_class_placements(class_id, registration_id, created_by)
    VALUES (class_row.class_id, registration.registration_id, p_actor)
    ON CONFLICT (registration_id, class_id) DO NOTHING RETURNING placement_id INTO item;
    IF item IS NULL THEN
        SELECT placement_id INTO item FROM public.academic_class_placements
        WHERE registration_id = registration.registration_id AND class_id = class_row.class_id;
    END IF;
    SELECT to_jsonb(cp) INTO result FROM public.academic_class_placements cp WHERE placement_id = item;
    PERFORM public.academic_package_audit(p_actor, p_tenant, 'place_student', 'academic_class_placements', item, NULL, result);
    RETURN result;
END;
$$;

CREATE FUNCTION public.academic_package_roster_active(p_roster uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT NOT EXISTS (SELECT 1 FROM public.academic_subject_participation WHERE roster_id = p_roster)
        OR EXISTS (SELECT 1 FROM public.academic_subject_participation WHERE roster_id = p_roster AND ended_at IS NULL);
$$;

CREATE FUNCTION public.academic_package_subject_roster(
    p_actor uuid, p_tenant uuid, p_placement uuid, p_subject uuid
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE registration public.student_registrations; class_row public.academic_classes;
    section_row public.sections; offering public.course_offerings; identity jsonb;
    roster public.faculty_attendance_rosters; matches integer; occupied integer; linked uuid; state text;
BEGIN
    SELECT c.* INTO class_row FROM public.academic_class_placements cp
    JOIN public.academic_classes c USING(class_id) JOIN public.student_registrations r USING(registration_id)
    WHERE cp.placement_id = p_placement;
    SELECT r.* INTO registration FROM public.academic_class_placements cp
    JOIN public.student_registrations r USING(registration_id) WHERE cp.placement_id = p_placement;
    SELECT sec.* INTO section_row FROM public.academic_class_subjects cs
    JOIN public.sections sec USING(section_id) JOIN public.academic_curriculum_subjects s USING(curriculum_subject_id)
    JOIN public.courses course ON course.course_id = s.course_id
    JOIN public.departments d ON d.department_id = course.department_id
    WHERE cs.class_id = class_row.class_id AND cs.curriculum_subject_id = p_subject
      AND sec.is_active AND course.is_active AND d.is_active AND d.institution_id = p_tenant FOR UPDATE OF sec;
    IF NOT FOUND THEN RAISE EXCEPTION 'Every package subject needs an active teaching mapping' USING ERRCODE = '23514'; END IF;
    SELECT * INTO offering FROM public.course_offerings
    WHERE course_offering_id = section_row.course_offering_id AND is_active FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Subject offering unavailable' USING ERRCODE = '23514'; END IF;
    identity := public.faculty_attendance_identity(p_tenant, registration.register_number, registration.university_roll_number);
    IF COALESCE((identity->>'conflict')::boolean, true)
        OR (identity->>'program_id' IS NOT NULL AND (identity->>'program_id')::uuid <> offering.program_id) THEN
        RAISE EXCEPTION 'Subject identity requires reconciliation' USING ERRCODE = '23514';
    END IF;
    IF class_row.study_semester <> 1 AND registration.university_roll_number IS NULL THEN
        RAISE EXCEPTION 'University roll number required after first study semester' USING ERRCODE = '23514';
    END IF;
    SELECT count(*) INTO matches FROM public.faculty_attendance_rosters r
    WHERE r.institution_id = p_tenant AND r.section_id = section_row.section_id
      AND (r.register_number = registration.register_number
        OR (registration.university_roll_number IS NOT NULL AND r.university_roll_number = registration.university_roll_number));
    IF matches > 1 THEN RAISE EXCEPTION 'Conflicting existing subject identities' USING ERRCODE = '23514'; END IF;
    SELECT * INTO roster FROM public.faculty_attendance_rosters r
    WHERE r.institution_id = p_tenant AND r.section_id = section_row.section_id
      AND (r.register_number = registration.register_number
        OR (registration.university_roll_number IS NOT NULL AND r.university_roll_number = registration.university_roll_number)) FOR UPDATE;
    IF roster.roster_id IS NOT NULL AND (roster.register_number <> registration.register_number
        OR (roster.university_roll_number IS NOT NULL AND registration.university_roll_number IS NOT NULL
            AND roster.university_roll_number <> registration.university_roll_number)
        OR roster.reconciliation_state = 'CONFLICT'
        OR (roster.linked_student_id IS NOT NULL AND roster.linked_student_id IS DISTINCT FROM (identity->>'student_id')::uuid)) THEN
        RAISE EXCEPTION 'Existing subject identity conflict' USING ERRCODE = '23514';
    END IF;
    IF roster.roster_id IS NULL OR NOT public.academic_package_roster_active(roster.roster_id) THEN
        SELECT count(*) INTO occupied FROM public.faculty_attendance_rosters r
        WHERE r.section_id = section_row.section_id
          AND public.academic_package_roster_active(r.roster_id);
        IF section_row.capacity IS NOT NULL AND occupied >= section_row.capacity THEN
            RAISE EXCEPTION 'Subject teaching group is full' USING ERRCODE = '23514';
        END IF;
        SELECT count(*) INTO occupied FROM public.faculty_attendance_rosters r
        WHERE r.course_offering_id = offering.course_offering_id
          AND public.academic_package_roster_active(r.roster_id);
        IF offering.capacity IS NOT NULL AND occupied >= offering.capacity THEN
            RAISE EXCEPTION 'Subject offering is full' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF roster.roster_id IS NOT NULL THEN RETURN roster.roster_id; END IF;
    linked := CASE WHEN identity->>'approval_status' = 'approved' THEN (identity->>'student_id')::uuid END;
    state := CASE WHEN identity->>'student_id' IS NULL THEN 'UNREGISTERED'
        WHEN linked IS NULL THEN 'PENDING_APPROVAL'
        WHEN (identity->>'is_active')::boolean AND identity->>'status' = 'active' THEN 'ACTIVE' ELSE 'INACTIVE' END;
    INSERT INTO public.faculty_attendance_rosters(institution_id, section_id, course_offering_id, semester_id,
        register_number, university_roll_number, student_name, email, created_by, linked_student_id, roster_status, reconciliation_state)
    VALUES (p_tenant, section_row.section_id, offering.course_offering_id, offering.semester_id,
        registration.register_number, registration.university_roll_number, registration.student_name, registration.email,
        p_actor, linked, state, CASE WHEN linked IS NOT NULL THEN 'LINKED'
            WHEN identity->>'student_id' IS NOT NULL THEN 'PENDING' ELSE 'NONE' END)
    RETURNING roster_id INTO roster.roster_id;
    RETURN roster.roster_id;
END;
$$;
