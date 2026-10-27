CREATE FUNCTION public.manage_academic_structure_record(
    p_actor_user_id uuid, p_institution_id uuid, p_entity text, p_record_id uuid, p_payload jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE id_column text; resource text; allowed text[]; mutable text[]; key text;
    before_row jsonb; after_row jsonb; item jsonb; item_id uuid:=COALESCE(p_record_id,gen_random_uuid());
    columns text; expressions text;
BEGIN
    CASE p_entity
    WHEN 'program_semesters' THEN
        id_column:='program_semester_id'; resource:='departments';
        allowed:=ARRAY['program_id','name','code','semester_number','is_active'];
        mutable:=ARRAY['name','code','is_active'];
    WHEN 'curriculum_versions' THEN
        id_column:='curriculum_version_id'; resource:='courses';
        allowed:=ARRAY['program_id','academic_year_id','name','version','total_semesters','description','is_active'];
        mutable:=ARRAY['name','description','status','is_active'];
    WHEN 'curriculum_subjects' THEN
        id_column:='curriculum_subject_id'; resource:='courses';
        allowed:=ARRAY['curriculum_version_id','program_semester_id','course_id','course_type','is_required','is_active'];
        mutable:=ARRAY['course_type','is_required','is_active'];
    WHEN 'admission_cohorts' THEN
        id_column:='admission_cohort_id'; resource:='departments';
        allowed:=ARRAY['program_id','curriculum_version_id','academic_year_id','name','code','start_year','end_year','expected_count','description','status'];
        mutable:=ARRAY['name','code','expected_count','description','status'];
    WHEN 'academic_sections' THEN
        id_column:='academic_section_id'; resource:='courses';
        allowed:=ARRAY['admission_cohort_id','program_semester_id','semester_id','name','code','capacity','description','is_active'];
        mutable:=ARRAY['name','capacity','description','is_active'];
    WHEN 'academic_offerings' THEN
        id_column:='academic_offering_id'; resource:='courses';
        allowed:=ARRAY['academic_section_id','curriculum_subject_id','capacity','is_active'];
        mutable:=ARRAY['capacity','is_active'];
    ELSE RAISE EXCEPTION 'Unknown academic entity' USING ERRCODE='22023';
    END CASE;
    PERFORM public.assert_academic_foundation_actor(p_actor_user_id,p_institution_id,resource);
    IF p_payload IS NULL OR jsonb_typeof(p_payload)<>'object' OR p_payload='{}'::jsonb THEN
        RAISE EXCEPTION 'Academic fields required' USING ERRCODE='22023';
    END IF;
    FOR key IN SELECT jsonb_object_keys(p_payload) LOOP
        IF NOT key=ANY(CASE WHEN p_record_id IS NULL THEN allowed ELSE mutable END) THEN
            RAISE EXCEPTION 'Unsupported or immutable academic field' USING ERRCODE='22023';
        END IF;
    END LOOP;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:'||p_institution_id::text,0));
    IF p_record_id IS NOT NULL THEN
        EXECUTE format('SELECT to_jsonb(t) FROM public.%I t WHERE %I=$1 AND institution_id=$2 FOR UPDATE',p_entity,id_column)
            INTO before_row USING p_record_id,p_institution_id;
        IF before_row IS NULL THEN RAISE EXCEPTION 'Academic record not found' USING ERRCODE='P0002'; END IF;
    END IF;
    item:=COALESCE(before_row,'{}'::jsonb)||p_payload||jsonb_build_object(id_column,item_id,'institution_id',p_institution_id);
    SELECT string_agg(format('%I',field),','),string_agg(format('r.%I',field),',') INTO columns,expressions
      FROM jsonb_object_keys(CASE WHEN p_record_id IS NULL THEN item ELSE p_payload END) AS field;
    IF p_record_id IS NULL THEN
        EXECUTE format('INSERT INTO public.%I AS t (%s) SELECT %s FROM jsonb_populate_record(NULL::public.%I,$1) r RETURNING to_jsonb(t)',p_entity,columns,expressions,p_entity)
            INTO after_row USING item;
    ELSE
        EXECUTE format('UPDATE public.%I AS t SET (%s)=(SELECT %s FROM jsonb_populate_record(NULL::public.%I,$1) r) WHERE %I=$2 AND institution_id=$3 RETURNING to_jsonb(t)',p_entity,columns,expressions,p_entity,id_column)
            INTO after_row USING item,p_record_id,p_institution_id;
    END IF;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data)
    VALUES(p_actor_user_id,p_institution_id,'academic.'||p_entity||CASE WHEN p_record_id IS NULL THEN '.create' ELSE '.update' END,
        p_entity,item_id::text,jsonb_build_object('before',before_row,'after',after_row));
    RETURN after_row;
END;
$$;
