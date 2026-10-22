CREATE FUNCTION public.academic_package_prepare_teaching(p_actor uuid, p_tenant uuid, p_class uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE class_row public.academic_classes; batch public.academic_batches; term public.semesters;
    subject record; offering public.course_offerings; section public.sections; mapping uuid;
    created_offerings integer := 0; created_sections integer := 0; mapped_subjects integer := 0;
    prepared_subjects integer := 0; result jsonb; created jsonb; section_code text;
BEGIN
    PERFORM public.academic_package_require(p_actor, p_tenant, 'academic.class.manage');
    PERFORM public.academic_package_require(p_actor, p_tenant, 'courses.manage');
    -- Preserve the existing academic-master creation authority as well as its
    -- audits, tenant checks and validation. No new faculty/staff authority.
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:' || p_tenant::text, 0));
    SELECT * INTO class_row FROM public.academic_classes
    WHERE class_id = p_class AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Class not found' USING ERRCODE = 'P0002'; END IF;
    SELECT b.* INTO batch FROM public.academic_batches b
    JOIN public.programs p USING(program_id) JOIN public.departments d USING(department_id)
    JOIN public.academic_curricula c ON c.curriculum_id = class_row.curriculum_id
    WHERE b.batch_id = class_row.batch_id AND b.institution_id = p_tenant AND b.is_active
      AND p.is_active AND d.is_active AND d.institution_id = p_tenant
      AND c.institution_id = p_tenant AND c.program_id = b.program_id FOR SHARE OF b, p, d, c;
    IF NOT FOUND THEN RAISE EXCEPTION 'Active matching class ancestry required' USING ERRCODE = '23514'; END IF;
    SELECT s.* INTO term FROM public.semesters s JOIN public.academic_years y USING(academic_year_id)
    WHERE s.semester_id = class_row.semester_id AND y.institution_id = p_tenant
      AND s.is_active AND y.is_active FOR SHARE OF s, y;
    IF NOT FOUND THEN RAISE EXCEPTION 'Active class calendar required' USING ERRCODE = '23514'; END IF;
    section_code := 'CLASS-' || class_row.class_id::text;
    FOR subject IN
        SELECT cs.curriculum_subject_id, cs.course_id, course.name
        FROM public.academic_curriculum_subjects cs JOIN public.courses course USING(course_id)
        WHERE cs.curriculum_id = class_row.curriculum_id AND cs.study_semester = class_row.study_semester
          AND (cs.is_core OR EXISTS (SELECT 1 FROM public.academic_class_packages cp
            JOIN public.academic_package_subjects ps USING(package_id)
            WHERE cp.class_id = p_class AND cp.enabled AND ps.curriculum_subject_id = cs.curriculum_subject_id))
        ORDER BY cs.curriculum_subject_id
    LOOP
        PERFORM 1 FROM public.courses course JOIN public.departments d USING(department_id)
        WHERE course.course_id = subject.course_id AND course.is_active AND d.is_active
          AND d.institution_id = p_tenant FOR SHARE OF course, d;
        IF NOT FOUND THEN RAISE EXCEPTION 'Active class subject required' USING ERRCODE = '23514'; END IF;
        SELECT cs.section_id INTO mapping FROM public.academic_class_subjects cs
        WHERE cs.class_id = p_class AND cs.curriculum_subject_id = subject.curriculum_subject_id;
        IF mapping IS NOT NULL THEN
            -- Manual mappings remain authoritative. Validate without replacing
            -- them with generated groups or changing existing capacity limits.
            SELECT sec.* INTO section FROM public.sections sec WHERE sec.section_id = mapping FOR UPDATE;
            SELECT o.* INTO offering FROM public.course_offerings o
            WHERE o.course_offering_id = section.course_offering_id FOR UPDATE;
        ELSE
            SELECT o.* INTO offering FROM public.course_offerings o WHERE o.program_id = batch.program_id
              AND o.course_id = subject.course_id AND o.semester_id = term.semester_id FOR UPDATE;
            IF NOT FOUND THEN
                created := public.manage_academic_master_record(p_actor, p_tenant, 'course_offerings', NULL,
                    jsonb_build_object('program_id', batch.program_id, 'course_id', subject.course_id,
                        'academic_year_id', term.academic_year_id, 'semester_id', term.semester_id));
                SELECT o.* INTO offering FROM public.course_offerings o
                WHERE o.course_offering_id = (created->>'course_offering_id')::uuid;
                created_offerings := created_offerings + 1;
            END IF;
            IF NOT offering.is_active OR offering.academic_year_id IS DISTINCT FROM term.academic_year_id THEN
                RAISE EXCEPTION 'Existing subject offering is unavailable' USING ERRCODE = '23514';
            END IF;
            SELECT sec.* INTO section FROM public.sections sec
            WHERE sec.course_offering_id = offering.course_offering_id AND sec.code = section_code FOR UPDATE;
            IF NOT FOUND THEN
                created := public.manage_academic_master_record(p_actor, p_tenant, 'sections', NULL,
                    jsonb_build_object('course_offering_id', offering.course_offering_id,
                        'name', class_row.section_code || ' - ' || subject.name, 'code', section_code));
                SELECT sec.* INTO section FROM public.sections sec WHERE sec.section_id = (created->>'section_id')::uuid;
                created_sections := created_sections + 1;
            END IF;
            IF EXISTS (SELECT 1 FROM public.academic_class_subjects cs
                WHERE cs.section_id = section.section_id AND cs.class_id <> p_class) THEN
                RAISE EXCEPTION 'Generated teaching section is already mapped to another class' USING ERRCODE = '23514';
            END IF;
        END IF;
        IF section.section_id IS NULL OR NOT section.is_active OR NOT offering.is_active
            OR offering.course_id IS DISTINCT FROM subject.course_id OR offering.program_id IS DISTINCT FROM batch.program_id
            OR offering.semester_id IS DISTINCT FROM term.semester_id OR offering.academic_year_id IS DISTINCT FROM term.academic_year_id THEN
            RAISE EXCEPTION 'Existing teaching mapping is invalid or inactive' USING ERRCODE = '23514';
        END IF;
        IF (section.capacity IS NOT NULL AND section.capacity < (SELECT count(*)
                FROM public.faculty_attendance_rosters r WHERE r.section_id = section.section_id
                  AND public.academic_package_roster_active(r.roster_id)))
            OR (offering.capacity IS NOT NULL AND offering.capacity < (SELECT count(*)
                FROM public.faculty_attendance_rosters r WHERE r.course_offering_id = offering.course_offering_id
                  AND public.academic_package_roster_active(r.roster_id))) THEN
            RAISE EXCEPTION 'Existing teaching occupancy exceeds configured capacity' USING ERRCODE = '23514';
        END IF;
        IF mapping IS NULL THEN
            PERFORM public.academic_package_class_command(p_actor, p_tenant, 'set_class_subject',
                jsonb_build_object('class_id', p_class, 'curriculum_subject_id', subject.curriculum_subject_id,
                    'section_id', section.section_id));
            mapped_subjects := mapped_subjects + 1;
        END IF;
        prepared_subjects := prepared_subjects + 1;
    END LOOP;
    IF prepared_subjects = 0 THEN
        RAISE EXCEPTION 'Enable a class package before preparing its teaching subjects' USING ERRCODE = '23514';
    END IF;
    PERFORM public.academic_package_require(p_actor, p_tenant, 'academic.class.manage');
    PERFORM public.academic_package_require(p_actor, p_tenant, 'courses.manage');
    result := jsonb_build_object('class_id', p_class, 'prepared_subjects', prepared_subjects,
        'created_offerings', created_offerings, 'created_sections', created_sections, 'mapped_subjects', mapped_subjects);
    PERFORM public.academic_package_audit(p_actor, p_tenant, 'prepare_class_teaching', 'academic_classes', p_class, NULL, result);
    RETURN result;
END;
$$;
