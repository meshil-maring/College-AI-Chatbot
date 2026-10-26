-- Shared Stage 1 tenant lock serializes parent changes and both generations of writes.
CREATE FUNCTION public.validate_academic_structure() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    item jsonb := to_jsonb(NEW);
    previous jsonb;
    key text;
    parent_active boolean;
    check_parent boolean := TG_OP = 'INSERT';
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-foundations:' || NEW.institution_id::text, 0)
    );
    IF TG_OP = 'UPDATE' THEN
        previous := to_jsonb(OLD);
        FOR key IN SELECT jsonb_object_keys(item) LOOP
            IF (key LIKE '%\_id' ESCAPE '\' OR key IN ('created_at', 'study_semester_number'))
               AND item -> key IS DISTINCT FROM previous -> key THEN
                RAISE EXCEPTION 'Academic identity and ancestry are immutable' USING ERRCODE = '22023';
            END IF;
        END LOOP;
        check_parent := NEW.is_active AND NOT OLD.is_active;
    END IF;
    IF check_parent THEN
        PERFORM 1 FROM public.institutions i
        JOIN public.organizations o ON o.organization_id = i.organization_id
        WHERE i.institution_id = NEW.institution_id
          AND i.is_active AND i.status = 'active' AND o.status = 'active'
        FOR SHARE OF i, o;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Active institution and organization required' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF TG_TABLE_NAME = 'study_semesters' THEN
        SELECT p.is_active AND d.is_active AND y.is_active INTO parent_active
        FROM public.programs p
        JOIN public.departments d
          ON d.department_id = p.department_id AND d.institution_id = p.institution_id
        JOIN public.academic_years y ON y.academic_year_id = NEW.academic_year_id
          AND y.institution_id = NEW.institution_id
        WHERE p.program_id = NEW.program_id AND p.institution_id = NEW.institution_id
        FOR SHARE OF p, d, y;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Program or academic year not found in institution' USING ERRCODE = '23503';
        END IF;
    ELSE
        SELECT d.is_active INTO parent_active FROM public.departments d
        WHERE d.department_id = NEW.department_id AND d.institution_id = NEW.institution_id
        FOR SHARE OF d;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Department not found in institution' USING ERRCODE = '23503';
        END IF;
    END IF;
    IF check_parent AND NOT parent_active THEN
        RAISE EXCEPTION 'Active academic parents required' USING ERRCODE = '23514';
    END IF;
    NEW.name := btrim(NEW.name);
    NEW.code := btrim(NEW.code);
    IF TG_OP = 'INSERT' THEN NEW.created_at := now(); END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;
