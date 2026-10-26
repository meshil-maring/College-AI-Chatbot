CREATE OR REPLACE FUNCTION "public"."manage_academic_master_record"("p_actor_user_id" "uuid", "p_institution_id" "uuid", "p_entity" "text", "p_record_id" "uuid", "p_payload" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $_$
DECLARE
    id_column text;
    resource text;
    allowed text[];
    immutable text[];
    key text;
    before_row jsonb;
    after_row jsonb;
    item_id uuid := COALESCE(p_record_id, gen_random_uuid());
    fields text;
    expressions text;
    effective jsonb;
BEGIN
    CASE p_entity
    WHEN 'departments' THEN id_column:='department_id'; resource:='departments'; allowed:=ARRAY['name','code','description','is_active']; immutable:=ARRAY['institution_id','campus_id'];
    WHEN 'programs' THEN id_column:='program_id'; resource:='departments'; allowed:=ARRAY['department_id','name','code','description','degree_type','duration_years','total_credits','is_active']; immutable:=ARRAY['department_id'];
    WHEN 'academic_years' THEN id_column:='academic_year_id'; resource:='academic_years'; allowed:=ARRAY['name','code','start_date','end_date','is_current','is_active']; immutable:=ARRAY['institution_id'];
    WHEN 'semesters' THEN id_column:='semester_id'; resource:='semesters'; allowed:=ARRAY['academic_year_id','name','code','semester_number','start_date','end_date','is_current','is_active']; immutable:=ARRAY['academic_year_id'];
    WHEN 'courses' THEN id_column:='course_id'; resource:='courses'; allowed:=ARRAY['department_id','name','code','description','credits','lecture_hours','tutorial_hours','practical_hours','is_active']; immutable:=ARRAY['department_id'];
    WHEN 'program_courses' THEN id_column:='program_course_id'; resource:='courses'; allowed:=ARRAY['program_id','course_id','semester_id','course_type','is_required','is_active']; immutable:=ARRAY['program_id','course_id','semester_id'];
    WHEN 'course_offerings' THEN id_column:='course_offering_id'; resource:='courses'; allowed:=ARRAY['course_id','program_id','academic_year_id','semester_id','capacity','is_active']; immutable:=ARRAY['course_id','program_id','academic_year_id','semester_id'];
    WHEN 'sections' THEN id_column:='section_id'; resource:='courses'; allowed:=ARRAY['course_offering_id','name','code','capacity','is_active']; immutable:=ARRAY['course_offering_id','code'];
    ELSE RAISE EXCEPTION 'Unknown academic entity' USING ERRCODE='22023';
    END CASE;
    PERFORM public.assert_academic_foundation_actor(p_actor_user_id, p_institution_id, resource);
    IF p_payload IS NULL OR jsonb_typeof(p_payload)<>'object' OR p_payload='{}'::jsonb THEN
        RAISE EXCEPTION 'Academic fields required' USING ERRCODE='22023';
    END IF;
    FOR key IN SELECT jsonb_object_keys(p_payload) LOOP
        IF NOT key=ANY(allowed) OR (p_record_id IS NOT NULL AND key=ANY(immutable)) THEN
            RAISE EXCEPTION 'Unsupported or immutable academic field' USING ERRCODE='22023';
        END IF;
    END LOOP;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:' || p_institution_id::text, 0));
    IF p_record_id IS NOT NULL THEN
        IF public.academic_master_tenant(p_entity, p_record_id) IS DISTINCT FROM p_institution_id THEN
            RAISE EXCEPTION 'Academic record not found' USING ERRCODE='P0002';
        END IF;
        EXECUTE format('SELECT to_jsonb(t) FROM public.%I t WHERE %I=$1 FOR UPDATE',p_entity,id_column) INTO before_row USING p_record_id;
    END IF;
    effective := COALESCE(before_row,'{}'::jsonb) || p_payload || jsonb_build_object(id_column,item_id);
    IF p_entity IN ('departments','academic_years') THEN
        effective := effective || jsonb_build_object('institution_id',p_institution_id);
    ELSE
        CASE p_entity
        WHEN 'programs','courses' THEN resource:=public.academic_master_tenant('departments',(effective->>'department_id')::uuid)::text;
        WHEN 'semesters' THEN resource:=public.academic_master_tenant('academic_years',(effective->>'academic_year_id')::uuid)::text;
        WHEN 'program_courses','course_offerings' THEN resource:=public.academic_master_tenant('programs',(effective->>'program_id')::uuid)::text;
        WHEN 'sections' THEN resource:=public.academic_master_tenant('course_offerings',(effective->>'course_offering_id')::uuid)::text;
        END CASE;
        IF resource IS DISTINCT FROM p_institution_id::text THEN
            RAISE EXCEPTION 'Academic parent not found' USING ERRCODE='P0002';
        END IF;
    END IF;
    -- Populate only validated keys so SQL defaults remain authoritative.
    SELECT string_agg(format('%I',k),','),string_agg(format('r.%I',k),',') INTO fields,expressions
      FROM jsonb_object_keys(CASE WHEN p_record_id IS NULL THEN effective ELSE p_payload END) AS k;
    IF p_record_id IS NULL THEN
        EXECUTE format('INSERT INTO public.%I AS t (%s) SELECT %s FROM jsonb_populate_record(NULL::public.%I,$1) r RETURNING to_jsonb(t)',p_entity,fields,expressions,p_entity)
          INTO after_row USING effective;
    ELSE
        EXECUTE format('UPDATE public.%I AS t SET (%s)=(SELECT %s FROM jsonb_populate_record(NULL::public.%I,$1) r) WHERE %I=$2 RETURNING to_jsonb(t)',p_entity,fields,expressions,p_entity,id_column)
          INTO after_row USING effective,p_record_id;
    END IF;
    INSERT INTO public.admin_audit_log(actor_user_id,institution_id,action,table_name,record_id,record_data)
    VALUES(p_actor_user_id,p_institution_id,
        'academic.'||p_entity||CASE WHEN p_record_id IS NULL THEN '.create' WHEN p_payload->>'is_active'='false' THEN '.deactivate' WHEN p_payload->>'is_active'='true' THEN '.activate' ELSE '.update' END,
        p_entity,item_id,jsonb_build_object('before',before_row,'after',after_row));
    RETURN after_row;
END;
$_$;
