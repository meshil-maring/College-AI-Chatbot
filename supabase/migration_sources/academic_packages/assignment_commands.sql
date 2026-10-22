CREATE FUNCTION public.academic_package_apply(
    p_actor uuid, p_tenant uuid, p_placement uuid, p_package uuid,
    p_expected integer DEFAULT NULL, p_reason text DEFAULT 'Initial package assignment', p_review boolean DEFAULT false
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE placement public.academic_class_placements; class_row public.academic_classes;
    assignment public.academic_package_assignments; previous jsonb; result jsonb;
    subject uuid; subjects uuid[]; roster uuid; revision_id uuid; instant timestamptz; is_owner boolean;
    preexisting uuid[]; episode_start timestamptz;
BEGIN
    SELECT cp.* INTO placement FROM public.academic_class_placements cp
    JOIN public.academic_classes c USING(class_id)
    WHERE cp.placement_id = p_placement AND c.institution_id = p_tenant FOR UPDATE OF cp;
    IF NOT FOUND THEN RAISE EXCEPTION 'Placement not found' USING ERRCODE = 'P0002'; END IF;
    SELECT * INTO class_row FROM public.academic_classes WHERE class_id = placement.class_id FOR UPDATE;
    SELECT * INTO assignment FROM public.academic_package_assignments WHERE placement_id = p_placement FOR UPDATE;
    previous := CASE WHEN assignment.assignment_id IS NOT NULL THEN to_jsonb(assignment) END;
    is_owner := public.academic_package_owns(p_actor, p_tenant, p_placement);
    IF assignment.assignment_id IS NOT NULL AND p_expected IS NULL THEN
        IF assignment.package_id = p_package AND (
            public.academic_package_allowed(p_actor, p_tenant, 'academic.package.assign', class_row.class_id)
            OR (is_owner AND public.academic_package_allowed(p_actor, p_tenant, 'academic.package.own.select'))) THEN
            RETURN to_jsonb(assignment);
        END IF;
        RAISE EXCEPTION 'An assigned package requires an authorized change' USING ERRCODE = '42501';
    END IF;
    IF assignment.assignment_id IS NULL THEN
        IF NOT public.academic_package_allowed(p_actor, p_tenant, 'academic.package.assign', class_row.class_id) THEN
            PERFORM public.academic_package_require(p_actor, p_tenant, 'academic.package.own.select');
            IF NOT is_owner OR NOT class_row.student_choice_enabled THEN
                RAISE EXCEPTION 'Initial student package selection is disabled' USING ERRCODE = '42501';
            END IF;
        END IF;
        IF p_expected IS NOT NULL THEN RAISE EXCEPTION 'Assignment changed' USING ERRCODE = 'P0001'; END IF;
    ELSE
        PERFORM public.academic_package_require(p_actor, p_tenant,
            CASE WHEN p_review THEN 'academic.package.requests.review' ELSE 'academic.package.change' END,
            class_row.class_id);
        IF p_expected IS NULL OR assignment.revision <> p_expected THEN
            RAISE EXCEPTION 'Assignment revision is stale' USING ERRCODE = 'P0001';
        END IF;
        IF assignment.package_id = p_package THEN
            RAISE EXCEPTION 'Package is already assigned' USING ERRCODE = '23514';
        END IF;
    END IF;
    PERFORM 1 FROM public.academic_classes c JOIN public.academic_batches b USING(batch_id)
    JOIN public.programs p ON p.program_id = b.program_id JOIN public.departments d USING(department_id)
    JOIN public.semesters s ON s.semester_id = c.semester_id JOIN public.academic_years y USING(academic_year_id)
    WHERE c.class_id = class_row.class_id AND b.is_active AND p.is_active AND d.is_active
      AND s.is_active AND y.is_active AND y.institution_id = p_tenant FOR SHARE OF b, p, d, s, y;
    IF NOT FOUND THEN RAISE EXCEPTION 'Class academic context is unavailable' USING ERRCODE = '23514'; END IF;
    PERFORM 1 FROM public.academic_class_packages cp JOIN public.academic_subject_packages p USING(package_id)
    WHERE cp.class_id = class_row.class_id AND cp.package_id = p_package AND cp.enabled
      AND p.curriculum_id = class_row.curriculum_id AND p.study_semester = class_row.study_semester FOR SHARE OF cp, p;
    IF NOT FOUND THEN RAISE EXCEPTION 'Package is unavailable in this class' USING ERRCODE = '23514'; END IF;
    SELECT array_agg(s.curriculum_subject_id ORDER BY s.curriculum_subject_id) INTO subjects
    FROM public.academic_curriculum_subjects s
    WHERE s.curriculum_id = class_row.curriculum_id AND s.study_semester = class_row.study_semester
      AND (s.is_core OR EXISTS (SELECT 1 FROM public.academic_package_subjects ps
          WHERE ps.package_id = p_package AND ps.curriculum_subject_id = s.curriculum_subject_id));
    IF COALESCE(cardinality(subjects), 0) = 0 THEN
        RAISE EXCEPTION 'Package has no subjects' USING ERRCODE = '23514';
    END IF;
    IF assignment.assignment_id IS NULL AND EXISTS (
        SELECT 1 FROM public.faculty_attendance_rosters r
        JOIN public.academic_class_subjects cs USING(section_id)
        JOIN public.student_registrations sr ON sr.registration_id = placement.registration_id
        WHERE cs.class_id = class_row.class_id AND r.institution_id = p_tenant
          AND r.register_number = sr.register_number AND r.participation_active
          AND NOT (cs.curriculum_subject_id = ANY(subjects))
    ) THEN
        RAISE EXCEPTION 'Legacy subject membership outside this package requires review' USING ERRCODE = '23514';
    END IF;
    -- All old roster rows are locked before any episode ends; attendance writers
    -- lock these same rows, so a change cannot race marking into a withdrawn set.
    PERFORM r.roster_id FROM public.faculty_attendance_rosters r
    JOIN public.academic_subject_participation sp USING(roster_id)
    WHERE sp.placement_id = p_placement ORDER BY r.roster_id FOR UPDATE OF r;
    SELECT array_agg(r.roster_id) INTO preexisting FROM public.faculty_attendance_rosters r
    JOIN public.academic_class_subjects cs USING(section_id)
    JOIN public.student_registrations sr ON sr.registration_id = placement.registration_id
    WHERE cs.class_id = class_row.class_id AND r.institution_id = p_tenant AND r.register_number = sr.register_number;
    -- Prepare every target roster before publishing the new assignment revision.
    -- Missing mapping, identity conflict or capacity failure rolls back all work.
    FOREACH subject IN ARRAY subjects LOOP
        roster := public.academic_package_subject_roster(p_actor, p_tenant, p_placement, subject);
    END LOOP;
    -- Recheck live responsibility validity and wall-clock time AFTER lock waits.
    IF assignment.assignment_id IS NOT NULL THEN
        PERFORM public.academic_package_require(p_actor, p_tenant,
            CASE WHEN p_review THEN 'academic.package.requests.review' ELSE 'academic.package.change' END,
            class_row.class_id);
        instant := clock_timestamp();
        IF instant >= class_row.change_cutoff THEN
            RAISE EXCEPTION 'Package changes are closed for this class' USING ERRCODE = '23514';
        END IF;
    ELSE
        IF NOT public.academic_package_allowed(p_actor, p_tenant, 'academic.package.assign', class_row.class_id)
            AND (NOT class_row.student_choice_enabled OR NOT public.academic_package_owns(p_actor, p_tenant, p_placement)
                OR NOT public.academic_package_allowed(p_actor, p_tenant, 'academic.package.own.select')) THEN
            RAISE EXCEPTION 'Package assignment authority changed' USING ERRCODE = '42501';
        END IF;
        instant := clock_timestamp();
    END IF;
    IF assignment.assignment_id IS NULL THEN
        INSERT INTO public.academic_package_assignments(placement_id, package_id, assigned_by, assigned_at, updated_at)
        VALUES (p_placement, p_package, p_actor, instant, instant) RETURNING * INTO assignment;
    ELSE
        UPDATE public.academic_package_assignments SET package_id = p_package, revision = revision + 1, updated_at = instant
        WHERE assignment_id = assignment.assignment_id RETURNING * INTO assignment;
    END IF;
    INSERT INTO public.academic_package_revisions(assignment_id, revision, package_id, actor_user_id, reason, applied_at)
    VALUES (assignment.assignment_id, assignment.revision, p_package, p_actor, btrim(p_reason), instant)
    RETURNING academic_package_revisions.revision_id INTO revision_id;
    UPDATE public.academic_subject_participation SET ended_at = instant
    WHERE placement_id = p_placement AND ended_at IS NULL AND NOT (curriculum_subject_id = ANY(subjects));
    FOREACH subject IN ARRAY subjects LOOP
        IF NOT EXISTS (SELECT 1 FROM public.academic_subject_participation
            WHERE placement_id = p_placement AND curriculum_subject_id = subject AND ended_at IS NULL) THEN
            SELECT r.roster_id INTO roster FROM public.academic_class_subjects cs
            JOIN public.faculty_attendance_rosters r USING(section_id)
            JOIN public.student_registrations sr ON sr.registration_id = placement.registration_id
            WHERE cs.class_id = class_row.class_id AND cs.curriculum_subject_id = subject
              AND r.institution_id = p_tenant AND r.register_number = sr.register_number;
            episode_start := instant;
            IF assignment.revision = 1 THEN
                -- Explicitly adopting an established membership must retain its
                -- older attendance/marks eligibility. The package itself still
                -- begins now; this records existing subject participation only.
                SELECT LEAST(instant, CASE WHEN r.roster_id = ANY(preexisting) THEN r.created_at END,
                    (SELECT min(s.session_date)::timestamp AT TIME ZONE 'UTC'
                        FROM public.faculty_attendance_records ar JOIN public.faculty_attendance_sessions s USING(session_id)
                        WHERE ar.roster_id = r.roster_id),
                    (SELECT min(COALESCE(t.scheduled_date, (m.conducted_at AT TIME ZONE 'UTC')::date))::timestamp AT TIME ZONE 'UTC'
                        FROM public.test_results m LEFT JOIN public.faculty_tests t USING(test_id) WHERE m.roster_id = r.roster_id),
                    (SELECT min(a.date)::timestamp AT TIME ZONE 'UTC' FROM public.student_attendance a
                        WHERE a.student_id = r.linked_student_id AND a.section_id = r.section_id))
                INTO episode_start FROM public.faculty_attendance_rosters r WHERE r.roster_id = roster;
            END IF;
            INSERT INTO public.academic_subject_participation(placement_id, curriculum_subject_id, roster_id, started_at, revision_id)
            VALUES (p_placement, subject, roster, episode_start, revision_id);
        END IF;
    END LOOP;
    UPDATE public.faculty_attendance_rosters r SET participation_active = public.academic_package_roster_active(r.roster_id),
        participation_ended_at = CASE WHEN public.academic_package_roster_active(r.roster_id) THEN NULL ELSE instant END
    WHERE EXISTS (SELECT 1 FROM public.academic_subject_participation sp
        WHERE sp.placement_id = p_placement AND sp.roster_id = r.roster_id);
    UPDATE public.academic_package_requests SET status = 'superseded', reviewed_at = instant
    WHERE assignment_id = assignment.assignment_id AND status = 'pending';
    result := to_jsonb(assignment);
    PERFORM public.academic_package_audit(p_actor, p_tenant, 'apply', 'academic_package_assignments',
        assignment.assignment_id, previous, result);
    RETURN result;
END;
$$;
