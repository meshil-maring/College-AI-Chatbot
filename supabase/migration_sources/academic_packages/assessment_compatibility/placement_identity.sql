-- Admission profile year is not current class enrollment. A later-term roster
-- may use its exact, verified placement without rewriting admission identity.
CREATE FUNCTION public.academic_package_roster_has_placement(p_tenant uuid, p_roster uuid, p_student uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.academic_subject_participation sp
        JOIN public.academic_class_placements cp USING(placement_id)
        JOIN public.academic_classes cl USING(class_id)
        JOIN public.academic_batches batch USING(batch_id)
        JOIN public.student_registrations registration USING(registration_id)
        JOIN public.academic_class_subjects mapping ON mapping.class_id = cl.class_id
            AND mapping.curriculum_subject_id = sp.curriculum_subject_id
        JOIN public.academic_curriculum_subjects subject ON subject.curriculum_subject_id = sp.curriculum_subject_id
        JOIN public.faculty_attendance_rosters roster ON roster.roster_id = sp.roster_id
        JOIN public.sections section ON section.section_id = roster.section_id
        JOIN public.course_offerings offering ON offering.course_offering_id = section.course_offering_id
        JOIN public.students student ON student.student_id = p_student
        WHERE sp.roster_id = p_roster AND cl.institution_id = p_tenant
          AND registration.institution_id = p_tenant AND batch.institution_id = p_tenant
          AND registration.batch_id = cl.batch_id AND registration.program_id = batch.program_id
          AND roster.institution_id = p_tenant AND student.institution_id = p_tenant
          AND (roster.linked_student_id IS NULL OR roster.linked_student_id = p_student)
          AND student.register_number = registration.register_number
          AND roster.register_number = registration.register_number
          AND (registration.university_roll_number IS NULL OR student.university_roll_number = registration.university_roll_number)
          AND (roster.university_roll_number IS NULL OR student.university_roll_number = roster.university_roll_number)
          AND mapping.section_id = roster.section_id AND offering.program_id = batch.program_id
          AND offering.semester_id = cl.semester_id AND subject.course_id = offering.course_id
          AND subject.curriculum_id = cl.curriculum_id AND subject.study_semester = cl.study_semester
          AND (student.program_id IS NULL OR student.program_id = offering.program_id)
    );
$$;

CREATE FUNCTION public.academic_package_roster_context(p_tenant uuid, p_roster_ids uuid[])
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE item record; identity jsonb; result jsonb := '{}'::jsonb;
BEGIN
    IF COALESCE(auth.role(), '') <> 'service_role' THEN
        RAISE EXCEPTION 'Service role required' USING ERRCODE = '42501';
    END IF;
    IF COALESCE(cardinality(p_roster_ids), 0) > 500 THEN
        RAISE EXCEPTION 'At most 500 roster contexts may be read' USING ERRCODE = '22023';
    END IF;
    FOR item IN
        SELECT DISTINCT ON (roster.roster_id) roster.roster_id, roster.register_number, roster.university_roll_number,
            roster.linked_student_id, batch.program_id, offering.academic_year_id, cl.semester_id,
            cl.study_semester, cp.placement_id
        FROM public.academic_subject_participation sp
        JOIN public.academic_class_placements cp USING(placement_id)
        JOIN public.academic_classes cl USING(class_id)
        JOIN public.academic_batches batch USING(batch_id)
        JOIN public.student_registrations registration USING(registration_id)
        JOIN public.academic_class_subjects mapping ON mapping.class_id = cl.class_id
            AND mapping.curriculum_subject_id = sp.curriculum_subject_id
        JOIN public.academic_curriculum_subjects subject ON subject.curriculum_subject_id = sp.curriculum_subject_id
        JOIN public.faculty_attendance_rosters roster ON roster.roster_id = sp.roster_id
        JOIN public.course_offerings offering ON offering.course_offering_id = roster.course_offering_id
        WHERE roster.roster_id = ANY(p_roster_ids) AND cl.institution_id = p_tenant
          AND registration.institution_id = p_tenant AND batch.institution_id = p_tenant
          AND registration.batch_id = cl.batch_id AND registration.program_id = batch.program_id
          AND roster.institution_id = p_tenant AND roster.register_number = registration.register_number
          AND (registration.university_roll_number IS NULL OR roster.university_roll_number = registration.university_roll_number)
          AND mapping.section_id = roster.section_id AND offering.program_id = batch.program_id
          AND offering.semester_id = cl.semester_id AND subject.course_id = offering.course_id
          AND subject.curriculum_id = cl.curriculum_id AND subject.study_semester = cl.study_semester
        ORDER BY roster.roster_id, sp.started_at DESC
    LOOP
        identity := public.faculty_attendance_identity(p_tenant, item.register_number, item.university_roll_number);
        IF COALESCE((identity->>'conflict')::boolean, true)
            OR (identity->>'program_id' IS NOT NULL AND (identity->>'program_id')::uuid <> item.program_id)
            OR (item.linked_student_id IS NOT NULL AND item.linked_student_id IS DISTINCT FROM (identity->>'student_id')::uuid) THEN
            CONTINUE;
        END IF;
        result := result || jsonb_build_object(item.roster_id::text, identity || jsonb_build_object(
            'placement_id', item.placement_id, 'program_id', item.program_id, 'academic_year_id', item.academic_year_id,
            'semester_id', item.semester_id, 'study_semester', item.study_semester));
    END LOOP;
    RETURN result;
END;
$$;

CREATE FUNCTION public.academic_package_identity_for_roster(p_tenant uuid, p_roster uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE roster public.faculty_attendance_rosters; identity jsonb; year_id uuid;
BEGIN
    SELECT * INTO roster FROM public.faculty_attendance_rosters
    WHERE roster_id = p_roster AND institution_id = p_tenant;
    IF NOT FOUND THEN RETURN '{"conflict":true}'::jsonb; END IF;
    identity := public.faculty_attendance_identity(p_tenant, roster.register_number, roster.university_roll_number);
    IF NOT COALESCE((identity->>'conflict')::boolean, true)
        AND public.academic_package_roster_has_placement(p_tenant, p_roster, (identity->>'student_id')::uuid) THEN
        SELECT academic_year_id INTO year_id FROM public.course_offerings
        WHERE course_offering_id = roster.course_offering_id;
        identity := identity || jsonb_build_object('academic_year_id', year_id);
    END IF;
    RETURN identity;
END;
$$;
