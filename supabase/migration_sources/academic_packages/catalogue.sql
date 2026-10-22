CREATE FUNCTION public.academic_package_catalogue(p_actor_user_id uuid, p_institution_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE tenant uuid := p_institution_id; actor uuid := p_actor_user_id; role_name text;
    classes uuid[]; curricula uuid[]; placements uuid[]; manager boolean; reader boolean; curriculum_manager boolean;
    records jsonb; options jsonb; capabilities jsonb := '[]'::jsonb;
BEGIN
    role_name := public.academic_package_actor(actor, tenant);
    manager := public.academic_package_allowed(actor, tenant, 'academic.class.manage');
    curriculum_manager := public.academic_package_allowed(actor, tenant, 'academic.curriculum.manage');
    reader := public.academic_package_allowed(actor, tenant, 'academic.curriculum.read') OR curriculum_manager;
    SELECT COALESCE(array_agg(c.class_id), '{}'::uuid[]) INTO classes FROM public.academic_classes c
    WHERE c.institution_id = tenant AND (manager
        OR public.academic_package_allowed(actor, tenant, 'academic.class.read', c.class_id)
        OR public.academic_package_allowed(actor, tenant, 'academic.package.assign', c.class_id)
        OR public.academic_package_allowed(actor, tenant, 'academic.package.change', c.class_id)
        OR public.academic_package_allowed(actor, tenant, 'academic.package.requests.review', c.class_id)
        OR (public.academic_package_allowed(actor, tenant, 'academic.package.own.read')
            AND EXISTS (SELECT 1 FROM public.academic_class_placements cp WHERE cp.class_id = c.class_id
                AND public.academic_package_owns(actor, tenant, cp.placement_id))));
    SELECT COALESCE(array_agg(c.curriculum_id), '{}'::uuid[]) INTO curricula FROM public.academic_curricula c
    WHERE c.institution_id = tenant AND (reader OR manager
        OR EXISTS (SELECT 1 FROM public.academic_classes cl WHERE cl.class_id = ANY(classes) AND cl.curriculum_id = c.curriculum_id));
    SELECT COALESCE(array_agg(cp.placement_id), '{}'::uuid[]) INTO placements
    FROM public.academic_class_placements cp WHERE cp.class_id = ANY(classes)
      AND (role_name <> 'student' OR public.academic_package_owns(actor, tenant, cp.placement_id));
    IF NOT reader AND NOT manager AND cardinality(classes) = 0
        AND NOT public.academic_package_allowed(actor, tenant, 'academic.package.own.read') THEN
        RAISE EXCEPTION 'Academic package read scope required' USING ERRCODE = '42501';
    END IF;
    IF manager OR curriculum_manager THEN
        capabilities := capabilities || '"manage"'::jsonb;
    END IF;
    IF manager THEN capabilities := capabilities || '"manage_class"'::jsonb; END IF;
    IF manager AND role_name = 'admin' AND public.academic_package_allowed(actor, tenant, 'courses.manage') THEN
        capabilities := capabilities || '"prepare_teaching"'::jsonb;
    END IF;
    IF curriculum_manager THEN capabilities := capabilities || '"manage_curriculum"'::jsonb; END IF;
    IF public.academic_package_allowed(actor, tenant, 'academic.package.assign') OR EXISTS (
        SELECT 1 FROM unnest(classes) id WHERE public.academic_package_allowed(actor, tenant, 'academic.package.assign', id)) THEN
        capabilities := capabilities || '"assign"'::jsonb;
    END IF;
    IF public.academic_package_allowed(actor, tenant, 'academic.package.change') OR EXISTS (
        SELECT 1 FROM unnest(classes) id WHERE public.academic_package_allowed(actor, tenant, 'academic.package.change', id)) THEN
        capabilities := capabilities || '"change"'::jsonb;
    END IF;
    IF public.academic_package_allowed(actor, tenant, 'academic.package.requests.review') OR EXISTS (
        SELECT 1 FROM unnest(classes) id WHERE public.academic_package_allowed(actor, tenant, 'academic.package.requests.review', id)) THEN
        capabilities := capabilities || '"review"'::jsonb;
    END IF;
    IF public.academic_package_allowed(actor, tenant, 'academic.package.own.select') THEN capabilities := capabilities || '"select"'::jsonb; END IF;
    IF public.academic_package_allowed(actor, tenant, 'academic.package.own.request') THEN capabilities := capabilities || '"request"'::jsonb; END IF;
    SELECT jsonb_build_object(
        'curricula', COALESCE((SELECT jsonb_agg(to_jsonb(c) || jsonb_build_object('locked', EXISTS (
            SELECT 1 FROM public.academic_classes cl WHERE cl.curriculum_id = c.curriculum_id)))
            FROM public.academic_curricula c WHERE c.curriculum_id = ANY(curricula)), '[]'),
        'curriculum_subjects', COALESCE((SELECT jsonb_agg(s) FROM public.academic_curriculum_subjects s WHERE s.curriculum_id = ANY(curricula)), '[]'),
        'packages', COALESCE((SELECT jsonb_agg(p) FROM public.academic_subject_packages p WHERE p.curriculum_id = ANY(curricula)), '[]'),
        'package_subjects', COALESCE((SELECT jsonb_agg(ps) FROM public.academic_package_subjects ps
            JOIN public.academic_subject_packages p USING(package_id) WHERE p.curriculum_id = ANY(curricula)), '[]'),
        'classes', COALESCE((SELECT jsonb_agg(to_jsonb(c) || jsonb_build_object('program_id', b.program_id,
            'academic_year_id', s.academic_year_id, 'changes_locked', clock_timestamp() >= c.change_cutoff,
            'can_assign', public.academic_package_allowed(actor, tenant, 'academic.package.assign', c.class_id),
            'can_change', public.academic_package_allowed(actor, tenant, 'academic.package.change', c.class_id),
            'can_review', public.academic_package_allowed(actor, tenant, 'academic.package.requests.review', c.class_id)))
            FROM public.academic_classes c JOIN public.academic_batches b USING(batch_id) JOIN public.semesters s USING(semester_id)
            WHERE c.class_id = ANY(classes)), '[]'),
        'class_packages', COALESCE((SELECT jsonb_agg(cp) FROM public.academic_class_packages cp WHERE cp.class_id = ANY(classes)), '[]'),
        'class_subjects', COALESCE((SELECT jsonb_agg(cs) FROM public.academic_class_subjects cs WHERE cs.class_id = ANY(classes)), '[]'),
        'class_responsibilities', COALESCE((SELECT jsonb_agg(cr) FROM public.academic_class_responsibilities cr
            WHERE cr.class_id = ANY(classes) AND role_name <> 'student'), '[]'),
        'placements', COALESCE((SELECT jsonb_agg(cp) FROM public.academic_class_placements cp WHERE cp.placement_id = ANY(placements)), '[]'),
        'assignments', COALESCE((SELECT jsonb_agg(a) FROM public.academic_package_assignments a WHERE a.placement_id = ANY(placements)), '[]'),
        'history', COALESCE((SELECT jsonb_agg(r ORDER BY r.applied_at DESC) FROM public.academic_package_revisions r
            JOIN public.academic_package_assignments a USING(assignment_id) WHERE a.placement_id = ANY(placements)), '[]'),
        'requests', COALESCE((SELECT jsonb_agg(to_jsonb(r) || jsonb_build_object('status', CASE
            WHEN r.status = 'pending' AND clock_timestamp() >= c.change_cutoff THEN 'expired'
            WHEN r.status = 'pending' AND r.source_revision <> a.revision THEN 'superseded' ELSE r.status END))
            FROM public.academic_package_requests r JOIN public.academic_package_assignments a USING(assignment_id)
            JOIN public.academic_class_placements cp USING(placement_id) JOIN public.academic_classes c USING(class_id)
            WHERE cp.placement_id = ANY(placements)), '[]')
    ) INTO records;
    SELECT jsonb_build_object(
        'programs', COALESCE((SELECT jsonb_agg(to_jsonb(p) || jsonb_build_object('department_name', d.name))
            FROM public.programs p JOIN public.departments d USING(department_id) WHERE d.institution_id = tenant
              AND (reader OR manager OR p.program_id IN (SELECT b.program_id FROM public.academic_classes c
                JOIN public.academic_batches b USING(batch_id) WHERE c.class_id = ANY(classes)))), '[]'),
        'batches', COALESCE((SELECT jsonb_agg(b) FROM public.academic_batches b WHERE b.institution_id = tenant
            AND (reader OR manager OR b.batch_id IN (SELECT c.batch_id FROM public.academic_classes c WHERE c.class_id = ANY(classes)))), '[]'),
        'academic_years', COALESCE((SELECT jsonb_agg(y) FROM public.academic_years y WHERE y.institution_id = tenant), '[]'),
        'semesters', COALESCE((SELECT jsonb_agg(s) FROM public.semesters s JOIN public.academic_years y USING(academic_year_id)
            WHERE y.institution_id = tenant), '[]'),
        'subjects', COALESCE((SELECT jsonb_agg(c) FROM public.courses c JOIN public.departments d USING(department_id)
            WHERE d.institution_id = tenant AND (reader OR manager OR EXISTS (
                SELECT 1 FROM public.academic_curriculum_subjects cs WHERE cs.curriculum_id = ANY(curricula) AND cs.course_id = c.course_id))), '[]'),
        'sections', COALESCE((SELECT jsonb_agg(to_jsonb(sec) || jsonb_build_object('course_id', o.course_id,
            'course_name', c.name, 'subject_name', c.name, 'program_id', o.program_id,
            'academic_year_id', o.academic_year_id, 'semester_id', o.semester_id))
            FROM public.sections sec JOIN public.course_offerings o USING(course_offering_id)
            JOIN public.courses c USING(course_id) JOIN public.departments d USING(department_id)
            WHERE d.institution_id = tenant AND (manager OR EXISTS (
                SELECT 1 FROM public.academic_class_subjects cs WHERE cs.class_id = ANY(classes) AND cs.section_id = sec.section_id))), '[]'),
        'registrations', COALESCE((SELECT jsonb_agg(r) FROM public.student_registrations r
            WHERE r.institution_id = tenant AND (manager OR EXISTS (
                SELECT 1 FROM public.academic_class_placements cp WHERE cp.registration_id = r.registration_id AND cp.placement_id = ANY(placements))
              OR (role_name <> 'student' AND EXISTS (SELECT 1 FROM public.academic_classes c
                JOIN public.academic_batches b USING(batch_id) JOIN public.semesters s USING(semester_id)
                WHERE c.class_id = ANY(classes) AND b.batch_id = r.batch_id AND b.program_id = r.program_id
                  AND public.academic_package_allowed(actor, tenant, 'academic.package.assign', c.class_id))))), '[]'),
        'responsibilities', COALESCE((SELECT jsonb_agg(to_jsonb(fr) || jsonb_build_object('name', rd.name,
            'faculty_email', u.email)) FROM public.faculty_responsibilities fr
            JOIN public.responsibility_definitions rd ON rd.code = fr.responsibility_code
            JOIN public.users u ON u.id = fr.faculty_user_id WHERE fr.institution_id = tenant
              AND manager AND fr.responsibility_code = 'class_in_charge' AND fr.is_active AND fr.revoked_at IS NULL), '[]')
    ) INTO options;
    RETURN jsonb_build_object('institution_id', tenant, 'capabilities', capabilities, 'records', records, 'options', options);
END;
$$;
