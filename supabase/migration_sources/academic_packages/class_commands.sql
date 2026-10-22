CREATE FUNCTION public.academic_package_class_command(
    p_actor uuid, p_tenant uuid, p_operation text, p_payload jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE class_row public.academic_classes; previous jsonb; result jsonb; item uuid;
    batch public.academic_batches; term public.semesters; curriculum public.academic_curricula;
    cutoff timestamptz; starts timestamptz; ends timestamptz; subject public.academic_curriculum_subjects;
    program_code text; package_code text;
BEGIN
    PERFORM public.academic_package_require(p_actor, p_tenant, 'academic.class.manage');
    item := (p_payload->>'class_id')::uuid;
    IF item IS NOT NULL THEN
        SELECT * INTO class_row FROM public.academic_classes
        WHERE class_id = item AND institution_id = p_tenant FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Class not found' USING ERRCODE = 'P0002'; END IF;
        previous := to_jsonb(class_row);
    END IF;
    IF p_operation = 'save_class' THEN
        SELECT b.* INTO batch FROM public.academic_batches b
        JOIN public.programs p USING(program_id) JOIN public.departments d USING(department_id)
        WHERE b.batch_id = (p_payload->>'batch_id')::uuid AND b.institution_id = p_tenant
          AND b.program_id = (p_payload->>'program_id')::uuid AND b.is_active AND p.is_active AND d.is_active
        FOR SHARE OF b, p, d;
        IF NOT FOUND THEN RAISE EXCEPTION 'Active matching batch required' USING ERRCODE = '23514'; END IF;
        SELECT s.* INTO term FROM public.semesters s JOIN public.academic_years y USING(academic_year_id)
        WHERE s.semester_id = (p_payload->>'semester_id')::uuid AND y.institution_id = p_tenant
          AND s.is_active AND y.is_active FOR SHARE OF s, y;
        IF NOT FOUND THEN RAISE EXCEPTION 'Active term required' USING ERRCODE = '23514'; END IF;
        SELECT * INTO curriculum FROM public.academic_curricula
        WHERE curriculum_id = (p_payload->>'curriculum_id')::uuid AND institution_id = p_tenant
          AND program_id = batch.program_id FOR SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Matching curriculum required' USING ERRCODE = '23514'; END IF;
        starts := term.start_date::timestamp AT TIME ZONE 'UTC';
        ends := (term.end_date + 1)::timestamp AT TIME ZONE 'UTC';
        cutoff := COALESCE((p_payload->>'change_cutoff')::timestamptz,
            class_row.change_cutoff, starts + (ends - starts) / 2);
        IF item IS NULL THEN
            IF NOT EXISTS (SELECT 1 FROM public.academic_subject_packages p
                WHERE p.curriculum_id = curriculum.curriculum_id
                  AND p.study_semester = (p_payload->>'study_semester')::integer
                  AND EXISTS (SELECT 1 FROM public.academic_package_subjects ps WHERE ps.package_id = p.package_id)) THEN
                RAISE EXCEPTION 'Create at least one complete package before freezing a class curriculum' USING ERRCODE = '23514';
            END IF;
            IF cutoff < starts OR cutoff > starts + (ends - starts) / 2 THEN
                RAISE EXCEPTION 'Cutoff must be within the first calendar half of the term' USING ERRCODE = '23514';
            END IF;
            item := gen_random_uuid();
            SELECT upper(regexp_replace(code, '[^a-zA-Z0-9]', '', 'g')) INTO program_code
            FROM public.programs WHERE program_id = batch.program_id;
            INSERT INTO public.academic_classes(class_id, institution_id, batch_id, semester_id, study_semester,
                curriculum_id, section_code, code, student_choice_enabled, teaching_start, teaching_end, change_cutoff, created_by)
            VALUES (item, p_tenant, batch.batch_id, term.semester_id, (p_payload->>'study_semester')::integer,
                curriculum.curriculum_id, btrim(p_payload->>'section_code'),
                left(COALESCE(NULLIF(program_code, ''), 'CLS'), 24) || '-' || batch.start_year || '-S'
                    || (p_payload->>'study_semester') || '-' || left(upper(regexp_replace(btrim(p_payload->>'section_code'),
                        '[^a-zA-Z0-9]', '', 'g')), 16) || '-' || upper(left(item::text, 8)),
                COALESCE((p_payload->>'student_choice_enabled')::boolean, false),
                starts, ends, cutoff, p_actor);
        ELSE
            IF (class_row.batch_id, class_row.semester_id, class_row.study_semester, class_row.curriculum_id, class_row.section_code)
                IS DISTINCT FROM (batch.batch_id, term.semester_id, (p_payload->>'study_semester')::integer,
                    curriculum.curriculum_id, btrim(p_payload->>'section_code')) THEN
                RAISE EXCEPTION 'Class identity is immutable' USING ERRCODE = '22023';
            END IF;
            IF cutoff > class_row.change_cutoff OR cutoff < class_row.teaching_start THEN
                RAISE EXCEPTION 'A class cutoff can only be shortened' USING ERRCODE = '23514';
            END IF;
            UPDATE public.academic_classes SET student_choice_enabled = (p_payload->>'student_choice_enabled')::boolean,
                change_cutoff = cutoff WHERE class_id = item;
        END IF;
        SELECT to_jsonb(c) INTO result FROM public.academic_classes c WHERE class_id = item;
    ELSIF p_operation = 'set_class_package' THEN
        SELECT p.code INTO package_code FROM public.academic_subject_packages p WHERE p.package_id = (p_payload->>'package_id')::uuid
          AND p.curriculum_id = class_row.curriculum_id AND p.study_semester = class_row.study_semester;
        IF NOT FOUND THEN RAISE EXCEPTION 'Package is outside this class curriculum' USING ERRCODE = '23514'; END IF;
        INSERT INTO public.academic_class_packages(class_id, package_id, selection_code, enabled)
        VALUES (item, (p_payload->>'package_id')::uuid,
            class_row.code || '-' || package_code,
            COALESCE((p_payload->>'enabled')::boolean, true))
        ON CONFLICT (class_id, package_id) DO UPDATE SET enabled = EXCLUDED.enabled
        RETURNING to_jsonb(academic_class_packages.*) INTO result;
    ELSIF p_operation = 'set_class_subject' THEN
        SELECT * INTO subject FROM public.academic_curriculum_subjects
        WHERE curriculum_subject_id = (p_payload->>'curriculum_subject_id')::uuid
          AND curriculum_id = class_row.curriculum_id AND study_semester = class_row.study_semester;
        IF NOT FOUND THEN RAISE EXCEPTION 'Subject is outside this class curriculum' USING ERRCODE = '23514'; END IF;
        SELECT * INTO batch FROM public.academic_batches WHERE batch_id = class_row.batch_id;
        PERFORM 1 FROM public.sections sec JOIN public.course_offerings o USING(course_offering_id)
        JOIN public.courses c USING(course_id) JOIN public.departments d USING(department_id)
        WHERE sec.section_id = (p_payload->>'section_id')::uuid AND o.course_id = subject.course_id
          AND o.program_id = batch.program_id AND o.semester_id = class_row.semester_id
          AND d.institution_id = p_tenant AND sec.is_active AND o.is_active AND c.is_active AND d.is_active
        FOR SHARE OF sec, o, c, d;
        IF NOT FOUND THEN RAISE EXCEPTION 'Active matching teaching section required' USING ERRCODE = '23514'; END IF;
        IF EXISTS (SELECT 1 FROM public.academic_package_assignments a
            JOIN public.academic_class_placements cp USING(placement_id) WHERE cp.class_id = item)
            AND EXISTS (SELECT 1 FROM public.academic_class_subjects cs
                WHERE cs.class_id = item AND cs.curriculum_subject_id = subject.curriculum_subject_id
                  AND cs.section_id <> (p_payload->>'section_id')::uuid) THEN
            RAISE EXCEPTION 'Teaching mapping is in use' USING ERRCODE = '23514';
        END IF;
        INSERT INTO public.academic_class_subjects(class_id, curriculum_subject_id, section_id)
        VALUES (item, subject.curriculum_subject_id, (p_payload->>'section_id')::uuid)
        ON CONFLICT (class_id, curriculum_subject_id) DO UPDATE SET section_id = EXCLUDED.section_id
        RETURNING to_jsonb(academic_class_subjects.*) INTO result;
    ELSIF p_operation = 'set_class_responsibility' THEN
        SELECT * INTO batch FROM public.academic_batches WHERE batch_id = class_row.batch_id;
        PERFORM 1 FROM public.faculty_responsibilities fr
        WHERE fr.responsibility_id = (p_payload->>'responsibility_id')::uuid AND fr.institution_id = p_tenant
          AND fr.responsibility_code = 'class_in_charge' AND fr.scope_type = 'section'
          AND fr.program_id = batch.program_id AND fr.semester_id = class_row.semester_id
          AND fr.academic_year_id = (SELECT academic_year_id FROM public.semesters WHERE semester_id = class_row.semester_id)
          AND EXISTS (SELECT 1 FROM public.academic_class_subjects cs
            WHERE cs.class_id = item AND cs.section_id = fr.section_id)
          AND fr.is_active AND fr.revoked_at IS NULL FOR SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Matching class responsibility required' USING ERRCODE = '23514'; END IF;
        IF COALESCE((p_payload->>'enabled')::boolean, true) THEN
            INSERT INTO public.academic_class_responsibilities(class_id, responsibility_id)
            VALUES (item, (p_payload->>'responsibility_id')::uuid) ON CONFLICT DO NOTHING;
        ELSE
            DELETE FROM public.academic_class_responsibilities
            WHERE class_id = item AND responsibility_id = (p_payload->>'responsibility_id')::uuid;
        END IF;
        result := jsonb_build_object('class_id', item, 'responsibility_id', p_payload->>'responsibility_id',
            'enabled', COALESCE((p_payload->>'enabled')::boolean, true));
    ELSE
        RAISE EXCEPTION 'Unknown class operation' USING ERRCODE = '22023';
    END IF;
    PERFORM public.academic_package_audit(p_actor, p_tenant, p_operation, 'academic_classes', item, previous, result);
    RETURN result;
END;
$$;
