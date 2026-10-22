CREATE FUNCTION public.academic_package_editable(p_curriculum uuid, p_tenant uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM 1 FROM public.academic_curricula WHERE curriculum_id = p_curriculum
      AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Curriculum not found' USING ERRCODE = 'P0002'; END IF;
    IF EXISTS (SELECT 1 FROM public.academic_classes WHERE curriculum_id = p_curriculum) THEN
        RAISE EXCEPTION 'Curriculum version is in use; create another version' USING ERRCODE = '23514';
    END IF;
END;
$$;

CREATE FUNCTION public.academic_package_curriculum_command(
    p_actor uuid, p_tenant uuid, p_operation text, p_payload jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE item uuid; curriculum uuid; result jsonb; previous jsonb; subject uuid; member uuid; ids uuid[];
BEGIN
    PERFORM public.academic_package_require(p_actor, p_tenant, 'academic.curriculum.manage');
    IF p_operation = 'save_curriculum' THEN
        curriculum := (p_payload->>'curriculum_id')::uuid;
        PERFORM 1 FROM public.programs p JOIN public.departments d USING(department_id)
        WHERE p.program_id = (p_payload->>'program_id')::uuid AND d.institution_id = p_tenant
          AND p.is_active AND d.is_active FOR SHARE OF p, d;
        IF NOT FOUND THEN RAISE EXCEPTION 'Active program required' USING ERRCODE = '23514'; END IF;
        IF curriculum IS NULL THEN
            INSERT INTO public.academic_curricula(institution_id, program_id, name, code, version, created_by)
            VALUES (p_tenant, (p_payload->>'program_id')::uuid, btrim(p_payload->>'name'),
                btrim(p_payload->>'code'), (p_payload->>'version')::integer, p_actor)
            RETURNING to_jsonb(academic_curricula.*), curriculum_id INTO result, item;
        ELSE
            PERFORM public.academic_package_editable(curriculum, p_tenant);
            SELECT to_jsonb(c) INTO previous FROM public.academic_curricula c WHERE curriculum_id = curriculum;
            IF (previous->>'program_id')::uuid IS DISTINCT FROM (p_payload->>'program_id')::uuid
                OR (previous->>'version')::integer IS DISTINCT FROM (p_payload->>'version')::integer THEN
                RAISE EXCEPTION 'Curriculum program and version are immutable' USING ERRCODE = '22023';
            END IF;
            UPDATE public.academic_curricula SET name = btrim(p_payload->>'name'), code = btrim(p_payload->>'code')
            WHERE curriculum_id = curriculum RETURNING to_jsonb(academic_curricula.*), curriculum_id INTO result, item;
        END IF;
    ELSIF p_operation = 'set_curriculum_subject' THEN
        curriculum := (p_payload->>'curriculum_id')::uuid;
        PERFORM public.academic_package_editable(curriculum, p_tenant);
        subject := (p_payload->>'course_id')::uuid;
        PERFORM 1 FROM public.courses c JOIN public.departments d USING(department_id)
        WHERE c.course_id = subject AND d.institution_id = p_tenant AND c.is_active AND d.is_active
        FOR SHARE OF c, d;
        IF NOT FOUND THEN RAISE EXCEPTION 'Active subject required' USING ERRCODE = '23514'; END IF;
        IF COALESCE((p_payload->>'is_core')::boolean, false) AND p_payload->>'course_type' <> 'core' THEN
            RAISE EXCEPTION 'Shared core subjects require core classification' USING ERRCODE = '23514';
        END IF;
        SELECT to_jsonb(s) INTO previous FROM public.academic_curriculum_subjects s
        WHERE curriculum_id = curriculum AND course_id = subject
          AND study_semester = (p_payload->>'study_semester')::integer;
        INSERT INTO public.academic_curriculum_subjects(curriculum_id, study_semester, course_id, course_type, is_core)
        VALUES (curriculum, (p_payload->>'study_semester')::integer, subject, p_payload->>'course_type',
            COALESCE((p_payload->>'is_core')::boolean, false))
        ON CONFLICT (curriculum_id, study_semester, course_id) DO UPDATE
        SET course_type = EXCLUDED.course_type, is_core = EXCLUDED.is_core
        RETURNING to_jsonb(academic_curriculum_subjects.*), curriculum_subject_id INTO result, item;
    ELSIF p_operation = 'save_package' THEN
        curriculum := (p_payload->>'curriculum_id')::uuid;
        PERFORM public.academic_package_editable(curriculum, p_tenant);
        IF jsonb_typeof(p_payload->'curriculum_subject_ids') IS DISTINCT FROM 'array' THEN
            RAISE EXCEPTION 'Package subjects required' USING ERRCODE = '22023';
        END IF;
        SELECT array_agg(value::uuid) INTO ids FROM jsonb_array_elements_text(p_payload->'curriculum_subject_ids');
        IF COALESCE(cardinality(ids), 0) NOT BETWEEN 1 AND 100
            OR cardinality(ids) <> (SELECT count(DISTINCT x) FROM unnest(ids) AS x) THEN
            RAISE EXCEPTION 'Package requires unique subject members' USING ERRCODE = '23514';
        END IF;
        FOREACH member IN ARRAY ids LOOP
            PERFORM 1 FROM public.academic_curriculum_subjects WHERE curriculum_subject_id = member
              AND curriculum_id = curriculum AND study_semester = (p_payload->>'study_semester')::integer;
            IF NOT FOUND THEN RAISE EXCEPTION 'Package subject context mismatch' USING ERRCODE = '23514'; END IF;
        END LOOP;
        item := (p_payload->>'package_id')::uuid;
        IF item IS NULL THEN
            INSERT INTO public.academic_subject_packages(curriculum_id, study_semester, name, code)
            VALUES (curriculum, (p_payload->>'study_semester')::integer, btrim(p_payload->>'name'), btrim(p_payload->>'code'))
            RETURNING to_jsonb(academic_subject_packages.*), package_id INTO result, item;
        ELSE
            SELECT to_jsonb(p) INTO previous FROM public.academic_subject_packages p
            WHERE package_id = item AND curriculum_id = curriculum
              AND study_semester = (p_payload->>'study_semester')::integer FOR UPDATE;
            IF NOT FOUND THEN RAISE EXCEPTION 'Package not found' USING ERRCODE = 'P0002'; END IF;
            UPDATE public.academic_subject_packages SET name = btrim(p_payload->>'name'), code = btrim(p_payload->>'code')
            WHERE package_id = item RETURNING to_jsonb(academic_subject_packages.*) INTO result;
            DELETE FROM public.academic_package_subjects WHERE package_id = item;
        END IF;
        INSERT INTO public.academic_package_subjects(package_id, curriculum_subject_id)
        SELECT item, x FROM unnest(ids) AS x;
        result := result || jsonb_build_object('curriculum_subject_ids', to_jsonb(ids));
    ELSE
        RAISE EXCEPTION 'Unknown curriculum operation' USING ERRCODE = '22023';
    END IF;
    PERFORM public.academic_package_audit(p_actor, p_tenant, p_operation, 'academic_curricula', item, previous, result);
    RETURN result;
END;
$$;
