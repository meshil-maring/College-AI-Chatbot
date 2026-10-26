CREATE FUNCTION public.manage_academic_structure(
    p_actor_user_id uuid, p_institution_id uuid, p_entity text, p_record_id uuid, p_payload jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    relation_name text;
    id_column text;
    allowed text[];
    immutable text[];
    required text[] := ARRAY['name', 'code'];
    key text;
    kind text;
    before_row jsonb;
    after_row jsonb;
    effective jsonb;
    item_id uuid := COALESCE(p_record_id, gen_random_uuid());
    fields text;
    expressions text;
BEGIN
    CASE p_entity
    WHEN 'semesters' THEN
        relation_name := 'study_semesters';
        id_column := 'study_semester_id';
        immutable := ARRAY['program_id', 'academic_year_id', 'study_semester_number'];
        allowed := ARRAY['name', 'code', 'description', 'is_active'] || immutable;
        required := required || immutable;
    WHEN 'subjects' THEN
        relation_name := 'subjects';
        id_column := 'subject_id';
        immutable := ARRAY['department_id'];
        allowed := ARRAY['name', 'code', 'description', 'credits', 'is_active'] || immutable;
        required := required || ARRAY['department_id', 'credits'];
    ELSE RAISE EXCEPTION 'Unknown academic structure entity' USING ERRCODE = '22023';
    END CASE;
    -- Reuse exact scoped active-admin authority; do not replace its Stage 1 helper.
    PERFORM public.assert_academic_foundation_actor(p_actor_user_id, p_institution_id, p_entity);
    IF p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' OR p_payload = '{}'::jsonb THEN
        RAISE EXCEPTION 'Academic fields required' USING ERRCODE = '22023';
    END IF;
    IF p_record_id IS NULL AND NOT p_payload ?& required THEN
        RAISE EXCEPTION 'Required academic fields missing' USING ERRCODE = '22023';
    END IF;
    FOR key IN SELECT jsonb_object_keys(p_payload) LOOP
        IF NOT key = ANY(allowed) OR (p_record_id IS NOT NULL AND key = ANY(immutable)) THEN
            RAISE EXCEPTION 'Unsupported or immutable academic field' USING ERRCODE = '22023';
        END IF;
        kind := jsonb_typeof(p_payload -> key);
        IF kind = 'null' AND key <> 'description' THEN
            RAISE EXCEPTION 'Required academic field cannot be null' USING ERRCODE = '22023';
        END IF;
        IF kind <> 'null' AND (
            (key = 'is_active' AND kind <> 'boolean') OR
            (key IN ('credits', 'study_semester_number') AND kind <> 'number') OR
            (key NOT IN ('is_active', 'credits', 'study_semester_number') AND kind <> 'string')
        ) THEN
            RAISE EXCEPTION 'Invalid academic field type' USING ERRCODE = '22023';
        END IF;
        IF key = 'study_semester_number' AND NOT (p_payload ->> key) ~ '^[0-9]+$' THEN
            RAISE EXCEPTION 'Study semester number must be an integer' USING ERRCODE = '22023';
        END IF;
    END LOOP;
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-foundations:' || p_institution_id::text, 0)
    );
    IF p_record_id IS NOT NULL THEN
        EXECUTE format('SELECT to_jsonb(t) FROM public.%I t WHERE %I = $1 AND institution_id = $2 FOR UPDATE',
                       relation_name, id_column) INTO before_row USING p_record_id, p_institution_id;
        IF before_row IS NULL THEN
            RAISE EXCEPTION 'Academic record not found' USING ERRCODE = 'P0002';
        END IF;
    END IF;
    effective := COALESCE(before_row, '{}'::jsonb) || p_payload ||
        jsonb_build_object(id_column, item_id, 'institution_id', p_institution_id);
    -- SQL identifiers come only from the closed entity/field whitelists.
    -- Omitted create fields keep their database defaults; all values are bound.
    SELECT string_agg(format('%I', k), ','), string_agg(format('r.%I', k), ',')
    INTO fields, expressions
    FROM jsonb_object_keys(CASE WHEN p_record_id IS NULL THEN effective ELSE p_payload END) AS k;
    IF p_record_id IS NULL THEN
        EXECUTE format('INSERT INTO public.%I AS t (%s) SELECT %s FROM jsonb_populate_record(NULL::public.%I, $1) r RETURNING to_jsonb(t)',
                       relation_name, fields, expressions, relation_name) INTO after_row USING effective;
    ELSE
        EXECUTE format('UPDATE public.%I AS t SET (%s) = (SELECT %s FROM jsonb_populate_record(NULL::public.%I, $1) r) WHERE %I = $2 AND institution_id = $3 RETURNING to_jsonb(t)',
                       relation_name, fields, expressions, relation_name, id_column)
        INTO after_row USING effective, p_record_id, p_institution_id;
    END IF;
    INSERT INTO public.admin_audit_log (
        actor_user_id, institution_id, action, table_name, record_id, record_data, status
    ) VALUES (
        p_actor_user_id, p_institution_id,
        'academic.' || p_entity || CASE WHEN p_record_id IS NULL THEN '.create'
            WHEN before_row ->> 'is_active' = 'true' AND after_row ->> 'is_active' = 'false'
                THEN '.deactivate'
            WHEN before_row ->> 'is_active' = 'false' AND after_row ->> 'is_active' = 'true'
                THEN '.activate' ELSE '.update' END,
        relation_name, item_id::text, jsonb_build_object('before', before_row, 'after', after_row), 'success'
    );
    RETURN after_row;
END;
$$;
