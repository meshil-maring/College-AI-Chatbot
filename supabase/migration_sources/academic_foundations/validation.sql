-- Enforce ancestry and deactivation invariants even for privileged SQL writers.
CREATE FUNCTION public.validate_academic_foundation() RETURNS trigger
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
            IF (key LIKE '%\_id' ESCAPE '\' OR key = 'created_at')
               AND item -> key IS DISTINCT FROM previous -> key THEN
                RAISE EXCEPTION 'Academic identity and ancestry are immutable' USING ERRCODE = '22023';
            END IF;
        END LOOP;
        check_parent := NEW.is_active AND NOT OLD.is_active;
    END IF;
    IF check_parent AND NOT EXISTS (
        SELECT 1 FROM public.institutions i
        JOIN public.organizations o ON o.organization_id = i.organization_id
        WHERE i.institution_id = NEW.institution_id
          AND i.is_active AND i.status = 'active' AND o.status = 'active'
    ) THEN
        RAISE EXCEPTION 'Active institution and organization required' USING ERRCODE = '23514';
    END IF;
    IF TG_TABLE_NAME = 'programs' THEN
        SELECT d.is_active INTO parent_active FROM public.departments d
        WHERE d.department_id = NEW.department_id AND d.institution_id = NEW.institution_id
        FOR SHARE OF d;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Department not found in institution' USING ERRCODE = '23503';
        END IF;
        IF check_parent AND NOT parent_active THEN
            RAISE EXCEPTION 'Active department required' USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'departments' AND NOT NEW.is_active THEN
        IF EXISTS (
            SELECT 1 FROM public.programs p
            WHERE p.department_id = NEW.department_id
              AND p.institution_id = NEW.institution_id AND p.is_active
        ) THEN
            RAISE EXCEPTION 'Deactivate dependent degree programs first' USING ERRCODE = '23514';
        END IF;
    END IF;
    NEW.name := btrim(NEW.name);
    NEW.code := btrim(NEW.code);
    IF TG_OP = 'INSERT' THEN NEW.created_at := now(); END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;
