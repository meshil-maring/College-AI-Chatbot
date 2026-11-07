-- Remove legacy program_courses, course_offerings and sections from Academic Setup.
-- The Curriculum Structure system (curriculum_subjects, academic_offerings, academic_sections)
-- is the sole authoritative source for subject-program assignments going forward.
BEGIN;

SET LOCAL lock_timeout = '10s';

-- 1. Drop data tables in FK dependency order (sections → course_offerings → program_courses).
--    Triggers are dropped automatically with their tables.
DROP TABLE IF EXISTS public.sections RESTRICT;
DROP TABLE IF EXISTS public.course_offerings RESTRICT;
DROP TABLE IF EXISTS public.program_courses RESTRICT;

-- 2. Remove the three legacy entity branches from the tenant-resolver function.
CREATE OR REPLACE FUNCTION public.academic_master_tenant(p_entity text, p_id uuid)
RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
DECLARE result uuid;
BEGIN
    CASE p_entity
    WHEN 'departments'    THEN SELECT d.institution_id INTO result FROM public.departments d WHERE d.department_id = p_id;
    WHEN 'academic_years' THEN SELECT y.institution_id INTO result FROM public.academic_years y WHERE y.academic_year_id = p_id;
    WHEN 'programs'       THEN SELECT d.institution_id INTO result FROM public.programs p JOIN public.departments d USING(department_id) WHERE p.program_id = p_id;
    WHEN 'courses'        THEN SELECT d.institution_id INTO result FROM public.courses c JOIN public.departments d USING(department_id) WHERE c.course_id = p_id;
    WHEN 'semesters'      THEN SELECT y.institution_id INTO result FROM public.semesters s JOIN public.academic_years y USING(academic_year_id) WHERE s.semester_id = p_id;
    ELSE RAISE EXCEPTION 'Unknown academic entity' USING ERRCODE = '22023';
    END CASE;
    RETURN result;
END;
$$;

-- 3. Remove the three legacy entity branches from the row-level validator trigger function.
CREATE OR REPLACE FUNCTION public.validate_academic_master_record() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    item     jsonb := to_jsonb(NEW);
    previous jsonb;
    key      text;
    owner    uuid;
    year_row public.academic_years;
    check_active boolean;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        previous := to_jsonb(OLD);
        FOR key IN SELECT jsonb_object_keys(item) LOOP
            IF (key LIKE '%\_id' ESCAPE '\' OR (TG_TABLE_NAME = 'sections' AND key = 'code'))
               AND item -> key IS DISTINCT FROM previous -> key THEN
                RAISE EXCEPTION 'Academic ancestry is immutable' USING ERRCODE = '22023';
            END IF;
        END LOOP;
    END IF;
    IF item ? 'name' AND btrim(item ->> 'name') = ''
       OR item ? 'code' AND btrim(item ->> 'code') = '' THEN
        RAISE EXCEPTION 'Academic name and code must be nonblank' USING ERRCODE = '23514';
    END IF;
    check_active := TG_OP = 'INSERT' OR (NEW.is_active AND NOT OLD.is_active);
    CASE TG_TABLE_NAME
    WHEN 'departments', 'academic_years' THEN
        owner := (item ->> 'institution_id')::uuid;
        IF check_active AND NOT EXISTS (
            SELECT 1 FROM public.institutions i
            WHERE i.institution_id = owner AND i.is_active AND i.status = 'active'
        ) THEN
            RAISE EXCEPTION 'Active institution required' USING ERRCODE = '23514';
        END IF;
    WHEN 'programs', 'courses' THEN
        owner := public.academic_master_tenant('departments', (item ->> 'department_id')::uuid);
        IF check_active AND NOT EXISTS (
            SELECT 1 FROM public.departments d
            WHERE d.department_id = (item ->> 'department_id')::uuid AND d.is_active
        ) THEN
            RAISE EXCEPTION 'Active department required' USING ERRCODE = '23514';
        END IF;
    WHEN 'semesters' THEN
        SELECT * INTO year_row FROM public.academic_years y
        WHERE y.academic_year_id = (item ->> 'academic_year_id')::uuid;
        owner := year_row.institution_id;
        IF (item ->> 'start_date')::date < year_row.start_date
           OR (item ->> 'end_date')::date > year_row.end_date
           OR (check_active AND NOT year_row.is_active) THEN
            RAISE EXCEPTION 'Semester must fit active academic year' USING ERRCODE = '23514';
        END IF;
    END CASE;
    IF owner IS NULL THEN
        RAISE EXCEPTION 'Academic parent missing' USING ERRCODE = '23514';
    END IF;
    IF TG_TABLE_NAME = 'academic_years' AND TG_OP = 'UPDATE' THEN
        IF EXISTS (
            SELECT 1 FROM public.semesters s
            WHERE s.academic_year_id = (item ->> 'academic_year_id')::uuid
              AND (s.start_date < (item ->> 'start_date')::date
                   OR s.end_date > (item ->> 'end_date')::date)
        ) THEN
            RAISE EXCEPTION 'Year dates exclude existing semesters' USING ERRCODE = '23514';
        END IF;
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

-- 4. Remove the three legacy entity branches from the master-record writer RPC.
CREATE OR REPLACE FUNCTION public.manage_academic_master_record(
    p_actor_user_id uuid, p_institution_id uuid,
    p_entity text, p_record_id uuid, p_payload jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $_$
DECLARE
    id_column   text;
    resource    text;
    allowed     text[];
    immutable   text[];
    key         text;
    before_row  jsonb;
    after_row   jsonb;
    item_id     uuid := COALESCE(p_record_id, gen_random_uuid());
    fields      text;
    expressions text;
    effective   jsonb;
BEGIN
    CASE p_entity
    WHEN 'departments'    THEN id_column := 'department_id';    resource := 'departments';    allowed := ARRAY['name','code','description','is_active'];                                                                                                immutable := ARRAY['institution_id','campus_id'];
    WHEN 'programs'       THEN id_column := 'program_id';       resource := 'departments';    allowed := ARRAY['department_id','name','code','description','degree_type','duration_years','total_credits','is_active'];                                 immutable := ARRAY['department_id'];
    WHEN 'academic_years' THEN id_column := 'academic_year_id'; resource := 'academic_years'; allowed := ARRAY['name','code','start_date','end_date','is_current','is_active'];                                                                         immutable := ARRAY['institution_id'];
    WHEN 'semesters'      THEN id_column := 'semester_id';      resource := 'semesters';      allowed := ARRAY['academic_year_id','name','code','semester_number','start_date','end_date','is_current','is_active'];                                    immutable := ARRAY['academic_year_id'];
    WHEN 'courses'        THEN id_column := 'course_id';        resource := 'courses';        allowed := ARRAY['department_id','name','code','description','credits','lecture_hours','tutorial_hours','practical_hours','is_active'];                   immutable := ARRAY['department_id'];
    ELSE RAISE EXCEPTION 'Unknown academic entity' USING ERRCODE = '22023';
    END CASE;
    PERFORM public.assert_academic_foundation_actor(p_actor_user_id, p_institution_id, resource);
    IF p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' OR p_payload = '{}'::jsonb THEN
        RAISE EXCEPTION 'Academic fields required' USING ERRCODE = '22023';
    END IF;
    FOR key IN SELECT jsonb_object_keys(p_payload) LOOP
        IF NOT key = ANY(allowed) OR (p_record_id IS NOT NULL AND key = ANY(immutable)) THEN
            RAISE EXCEPTION 'Unsupported or immutable academic field' USING ERRCODE = '22023';
        END IF;
    END LOOP;
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:' || p_institution_id::text, 0));
    IF p_record_id IS NOT NULL THEN
        IF public.academic_master_tenant(p_entity, p_record_id) IS DISTINCT FROM p_institution_id THEN
            RAISE EXCEPTION 'Academic record not found' USING ERRCODE = 'P0002';
        END IF;
        EXECUTE format('SELECT to_jsonb(t) FROM public.%I t WHERE %I = $1 FOR UPDATE',
                       p_entity, id_column) INTO before_row USING p_record_id;
    END IF;
    effective := COALESCE(before_row, '{}'::jsonb) || p_payload
                 || jsonb_build_object(id_column, item_id);
    IF p_entity IN ('departments', 'academic_years') THEN
        effective := effective || jsonb_build_object('institution_id', p_institution_id);
    ELSE
        CASE p_entity
        WHEN 'programs', 'courses' THEN
            resource := public.academic_master_tenant('departments',
                            (effective ->> 'department_id')::uuid)::text;
        WHEN 'semesters' THEN
            resource := public.academic_master_tenant('academic_years',
                            (effective ->> 'academic_year_id')::uuid)::text;
        END CASE;
        IF resource IS DISTINCT FROM p_institution_id::text THEN
            RAISE EXCEPTION 'Academic parent not found' USING ERRCODE = 'P0002';
        END IF;
    END IF;
    SELECT string_agg(format('%I', k), ','), string_agg(format('r.%I', k), ',')
    INTO fields, expressions
    FROM jsonb_object_keys(CASE WHEN p_record_id IS NULL THEN effective ELSE p_payload END) AS k;
    IF p_record_id IS NULL THEN
        EXECUTE format(
            'INSERT INTO public.%I AS t (%s) SELECT %s FROM jsonb_populate_record(NULL::public.%I, $1) r RETURNING to_jsonb(t)',
            p_entity, fields, expressions, p_entity)
        INTO after_row USING effective;
    ELSE
        EXECUTE format(
            'UPDATE public.%I AS t SET (%s) = (SELECT %s FROM jsonb_populate_record(NULL::public.%I, $1) r) WHERE %I = $2 RETURNING to_jsonb(t)',
            p_entity, fields, expressions, p_entity, id_column)
        INTO after_row USING effective, p_record_id;
    END IF;
    INSERT INTO public.admin_audit_log(actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor_user_id, p_institution_id,
        'academic.' || p_entity || CASE
            WHEN p_record_id IS NULL          THEN '.create'
            WHEN p_payload ->> 'is_active' = 'false' THEN '.deactivate'
            WHEN p_payload ->> 'is_active' = 'true'  THEN '.activate'
            ELSE '.update' END,
        p_entity, item_id, jsonb_build_object('before', before_row, 'after', after_row));
    RETURN after_row;
END;
$_$;

-- 5. Remove legacy entity branches from the deactivation-guard trigger function.
CREATE OR REPLACE FUNCTION public.guard_export_academic_parent() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE owner uuid; blocked boolean := false;
BEGIN
    IF NEW.is_active OR NOT OLD.is_active THEN RETURN NEW; END IF;
    owner := public.academic_master_tenant(TG_TABLE_NAME,
                 (to_jsonb(OLD) ->> TG_ARGV[0])::uuid);
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:' || owner::text, 0));
    CASE TG_TABLE_NAME
    WHEN 'departments' THEN
        blocked := EXISTS(SELECT 1 FROM public.programs WHERE department_id = OLD.department_id AND is_active)
                OR EXISTS(SELECT 1 FROM public.courses  WHERE department_id = OLD.department_id AND is_active);
    WHEN 'programs' THEN
        blocked := false; -- program_courses and course_offerings no longer exist
    WHEN 'courses' THEN
        blocked := false; -- program_courses and course_offerings no longer exist
    WHEN 'academic_years' THEN
        blocked := EXISTS(SELECT 1 FROM public.semesters WHERE academic_year_id = OLD.academic_year_id AND is_active);
    WHEN 'semesters' THEN
        blocked := false; -- program_courses and course_offerings no longer exist
    ELSE NULL;
    END CASE;
    IF blocked THEN
        RAISE EXCEPTION 'Deactivate dependent academic records first' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

-- 6. Retire the courses.manage permission that was only needed for program_courses/offerings/sections.
--    Keep courses.read and courses.manage active — they still gate course CRUD.
--    (No permission changes needed; the resource mapping stays valid for courses entity.)

NOTIFY pgrst, 'reload schema';
COMMIT;
