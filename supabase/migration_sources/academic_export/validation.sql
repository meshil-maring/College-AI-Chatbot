CREATE OR REPLACE FUNCTION "public"."validate_academic_master_record"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $$
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
