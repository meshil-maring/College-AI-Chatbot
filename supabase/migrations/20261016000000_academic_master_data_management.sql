-- Existing academic tables remain authoritative. No academic records are seeded.
BEGIN;
CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA extensions;
SET LOCAL search_path = public, extensions;

CREATE UNIQUE INDEX academic_departments_normalized_code ON public.departments(institution_id, lower(btrim(code)));
CREATE UNIQUE INDEX academic_programs_normalized_code ON public.programs(department_id, lower(btrim(code)));
CREATE UNIQUE INDEX academic_courses_normalized_code ON public.courses(department_id, lower(btrim(code)));
CREATE UNIQUE INDEX academic_years_normalized_code ON public.academic_years(institution_id, lower(btrim(code)));
CREATE UNIQUE INDEX academic_semesters_normalized_code ON public.semesters(academic_year_id, lower(btrim(code)));
CREATE UNIQUE INDEX academic_sections_normalized_code ON public.sections(course_offering_id, lower(btrim(code)));
ALTER TABLE public.academic_years ADD CONSTRAINT academic_years_active_dates_exclusion
    EXCLUDE USING gist (institution_id WITH =, daterange(start_date, end_date, '[]') WITH &&)
    WHERE (is_active);
ALTER TABLE public.academic_years ADD CONSTRAINT academic_years_current_active CHECK (NOT is_current OR is_active);
ALTER TABLE public.semesters ADD CONSTRAINT academic_semesters_current_active CHECK (NOT is_current OR is_active);

-- Tenant resolver is internal, never callable by browser roles.
CREATE FUNCTION public.academic_master_tenant(p_entity text, p_id uuid) RETURNS uuid
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE result uuid;
BEGIN
    CASE p_entity
    WHEN 'departments' THEN SELECT d.institution_id INTO result FROM public.departments d WHERE d.department_id=p_id;
    WHEN 'academic_years' THEN SELECT y.institution_id INTO result FROM public.academic_years y WHERE y.academic_year_id=p_id;
    WHEN 'programs' THEN SELECT d.institution_id INTO result FROM public.programs p JOIN public.departments d USING(department_id) WHERE p.program_id=p_id;
    WHEN 'courses' THEN SELECT d.institution_id INTO result FROM public.courses c JOIN public.departments d USING(department_id) WHERE c.course_id=p_id;
    WHEN 'semesters' THEN SELECT y.institution_id INTO result FROM public.semesters s JOIN public.academic_years y USING(academic_year_id) WHERE s.semester_id=p_id;
    WHEN 'program_courses' THEN SELECT public.academic_master_tenant('programs', pc.program_id) INTO result FROM public.program_courses pc WHERE pc.program_course_id=p_id;
    WHEN 'course_offerings' THEN SELECT public.academic_master_tenant('courses', o.course_id) INTO result FROM public.course_offerings o WHERE o.course_offering_id=p_id;
    WHEN 'sections' THEN SELECT public.academic_master_tenant('course_offerings', s.course_offering_id) INTO result FROM public.sections s WHERE s.section_id=p_id;
    ELSE RAISE EXCEPTION 'Unknown academic entity' USING ERRCODE='22023';
    END CASE;
    RETURN result;
END;
$$;

CREATE FUNCTION public.validate_academic_master_record() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    item jsonb := to_jsonb(NEW);
    previous jsonb;
    key text;
    owner uuid;
    parent_owner uuid;
    year_row public.academic_years;
    program_row public.programs;
    course_row public.courses;
    semester_row public.semesters;
    offering_row public.course_offerings;
    check_active boolean;
BEGIN
    IF TG_OP='UPDATE' THEN
        previous := to_jsonb(OLD);
        FOR key IN SELECT jsonb_object_keys(item) LOOP
            IF (key LIKE '%\_id' ESCAPE '\' OR (TG_TABLE_NAME='sections' AND key='code'))
               AND item->key IS DISTINCT FROM previous->key THEN
                RAISE EXCEPTION 'Academic ancestry is immutable' USING ERRCODE='22023';
            END IF;
        END LOOP;
    END IF;
    IF item ? 'name' AND btrim(item->>'name')='' OR item ? 'code' AND btrim(item->>'code')='' THEN
        RAISE EXCEPTION 'Academic name and code must be nonblank' USING ERRCODE='23514';
    END IF;
    check_active := TG_OP='INSERT' OR (NEW.is_active AND NOT OLD.is_active);
    CASE TG_TABLE_NAME
    WHEN 'departments', 'academic_years' THEN owner := (item->>'institution_id')::uuid;
    WHEN 'programs', 'courses' THEN owner := public.academic_master_tenant('departments', (item->>'department_id')::uuid);
    WHEN 'semesters' THEN owner := public.academic_master_tenant('academic_years', (item->>'academic_year_id')::uuid);
    WHEN 'program_courses', 'course_offerings' THEN owner := public.academic_master_tenant('programs', (item->>'program_id')::uuid);
    WHEN 'sections' THEN owner := public.academic_master_tenant('course_offerings', (item->>'course_offering_id')::uuid);
    END CASE;
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-setup:' || owner::text, 0));
    CASE TG_TABLE_NAME
    WHEN 'departments', 'academic_years' THEN
        owner := (item->>'institution_id')::uuid;
        IF check_active AND NOT EXISTS(SELECT 1 FROM public.institutions i WHERE i.institution_id=owner AND i.is_active AND i.status='active') THEN
            RAISE EXCEPTION 'Active institution required' USING ERRCODE='23514';
        END IF;
    WHEN 'programs', 'courses' THEN
        owner := public.academic_master_tenant('departments', (item->>'department_id')::uuid);
        IF check_active AND NOT EXISTS(SELECT 1 FROM public.departments d WHERE d.department_id=(item->>'department_id')::uuid AND d.is_active) THEN
            RAISE EXCEPTION 'Active department required' USING ERRCODE='23514';
        END IF;
    WHEN 'semesters' THEN
        SELECT * INTO year_row FROM public.academic_years y WHERE y.academic_year_id=(item->>'academic_year_id')::uuid;
        owner := year_row.institution_id;
        IF (item->>'start_date')::date < year_row.start_date OR (item->>'end_date')::date > year_row.end_date
           OR (check_active AND NOT year_row.is_active) THEN
            RAISE EXCEPTION 'Semester must fit active academic year' USING ERRCODE='23514';
        END IF;
    WHEN 'program_courses', 'course_offerings' THEN
        SELECT * INTO program_row FROM public.programs p WHERE p.program_id=(item->>'program_id')::uuid;
        SELECT * INTO course_row FROM public.courses c WHERE c.course_id=(item->>'course_id')::uuid;
        owner := public.academic_master_tenant('programs', (item->>'program_id')::uuid);
        parent_owner := public.academic_master_tenant('courses', (item->>'course_id')::uuid);
        IF owner IS DISTINCT FROM parent_owner OR owner IS NULL THEN
            RAISE EXCEPTION 'Program and subject tenant mismatch' USING ERRCODE='23514';
        END IF;
        IF check_active AND (NOT program_row.is_active OR NOT course_row.is_active
            OR NOT EXISTS(SELECT 1 FROM public.departments d WHERE d.department_id=program_row.department_id AND d.is_active)
            OR NOT EXISTS(SELECT 1 FROM public.departments d WHERE d.department_id=course_row.department_id AND d.is_active)) THEN
            RAISE EXCEPTION 'Active program and subject required' USING ERRCODE='23514';
        END IF;
        IF (item->>'semester_id') IS NOT NULL THEN
            SELECT * INTO semester_row FROM public.semesters s WHERE s.semester_id=(item->>'semester_id')::uuid;
            SELECT * INTO year_row FROM public.academic_years y WHERE y.academic_year_id=semester_row.academic_year_id;
            IF year_row.institution_id IS DISTINCT FROM owner OR (check_active AND (NOT semester_row.is_active OR NOT year_row.is_active)) THEN
                RAISE EXCEPTION 'Invalid semester tenant or activity' USING ERRCODE='23514';
            END IF;
        END IF;
        IF TG_TABLE_NAME='course_offerings' THEN
            IF semester_row.academic_year_id IS DISTINCT FROM (item->>'academic_year_id')::uuid THEN
                RAISE EXCEPTION 'Offering year and semester mismatch' USING ERRCODE='23514';
            END IF;
            IF check_active AND NOT EXISTS(SELECT 1 FROM public.program_courses pc WHERE pc.program_id=(item->>'program_id')::uuid AND pc.course_id=(item->>'course_id')::uuid AND pc.is_active AND (pc.semester_id IS NULL OR pc.semester_id=(item->>'semester_id')::uuid)) THEN
                RAISE EXCEPTION 'Active matching curriculum link required' USING ERRCODE='23514';
            END IF;
        END IF;
    WHEN 'sections' THEN
        SELECT * INTO offering_row FROM public.course_offerings o WHERE o.course_offering_id=(item->>'course_offering_id')::uuid;
        owner := public.academic_master_tenant('course_offerings', (item->>'course_offering_id')::uuid);
        IF check_active AND (NOT offering_row.is_active
            OR NOT EXISTS(SELECT 1 FROM public.courses c JOIN public.departments d USING(department_id) WHERE c.course_id=offering_row.course_id AND c.is_active AND d.is_active)
            OR NOT EXISTS(SELECT 1 FROM public.programs p JOIN public.departments d USING(department_id) WHERE p.program_id=offering_row.program_id AND p.is_active AND d.is_active)
            OR NOT EXISTS(SELECT 1 FROM public.semesters s JOIN public.academic_years y USING(academic_year_id) WHERE s.semester_id=offering_row.semester_id AND s.is_active AND y.is_active)) THEN
            RAISE EXCEPTION 'Active offering ancestry required' USING ERRCODE='23514';
        END IF;
    END CASE;
    IF owner IS NULL THEN RAISE EXCEPTION 'Academic parent missing' USING ERRCODE='23514'; END IF;
    IF TG_TABLE_NAME='academic_years' AND TG_OP='UPDATE' THEN
        IF EXISTS(SELECT 1 FROM public.semesters s WHERE s.academic_year_id=(item->>'academic_year_id')::uuid
          AND (s.start_date<(item->>'start_date')::date OR s.end_date>(item->>'end_date')::date)) THEN
            RAISE EXCEPTION 'Year dates exclude existing semesters' USING ERRCODE='23514';
        END IF;
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DO $$
DECLARE entity text;
BEGIN
    FOREACH entity IN ARRAY ARRAY['departments','programs','academic_years','semesters','courses','program_courses','course_offerings','sections'] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', entity);
        EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC, anon, authenticated', entity);
        EXECUTE format('REVOKE DELETE, TRUNCATE ON public.%I FROM service_role', entity);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE ON public.%I TO service_role', entity);
        EXECUTE format('CREATE TRIGGER academic_master_validate BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.validate_academic_master_record()', entity);
    END LOOP;
END;
$$;

CREATE FUNCTION public.manage_academic_master_record(
    p_actor_user_id uuid, p_institution_id uuid, p_entity text, p_record_id uuid, p_payload jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
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
    PERFORM public.phase81_assert_institution_admin(p_actor_user_id, p_institution_id);
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
    IF NOT EXISTS(
        SELECT 1 FROM public.user_roles ur JOIN public.roles r ON r.id=ur.role_id
        JOIN public.role_permissions rp ON rp.role_id=r.id JOIN public.permissions permission ON permission.permission_id=rp.permission_id
        WHERE ur.user_id=p_actor_user_id AND ur.scope_type='institution' AND ur.scope_id=p_institution_id
          AND r.name='admin' AND r.is_active AND permission.is_active
          AND permission.code IN (resource||'.manage', resource||'.*', '*')
    ) AND NOT EXISTS(
        SELECT 1 FROM public.user_permission_grants g JOIN public.permissions permission USING(permission_id)
        WHERE g.user_id=p_actor_user_id AND g.institution_id=p_institution_id AND g.revoked_at IS NULL
          AND permission.is_active AND permission.code IN(resource||'.manage',resource||'.*','*')
    ) THEN RAISE EXCEPTION 'Academic permission required' USING ERRCODE='42501'; END IF;
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
$$;

REVOKE ALL ON FUNCTION public.academic_master_tenant(text,uuid), public.validate_academic_master_record(),
    public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.academic_master_tenant(text,uuid), public.validate_academic_master_record(),
    public.manage_academic_master_record(uuid,uuid,text,uuid,jsonb) TO service_role;
NOTIFY pgrst, 'reload schema';
COMMIT;
