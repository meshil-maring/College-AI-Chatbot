-- All Academic Setup generations serialize hierarchy changes with one tenant lock.
CREATE FUNCTION public.validate_academic_sections() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    item jsonb := to_jsonb(NEW);
    previous jsonb;
    key text;
    parent_active boolean;
    subject_active boolean;
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
    IF TG_TABLE_NAME = 'class_sections' THEN
        SELECT s.is_active AND p.is_active AND d.is_active AND y.is_active INTO parent_active
        FROM public.study_semesters s
        JOIN public.programs p ON p.program_id = s.program_id AND p.institution_id = s.institution_id
        JOIN public.departments d ON d.department_id = p.department_id
          AND d.institution_id = p.institution_id
        JOIN public.academic_years y ON y.academic_year_id = s.academic_year_id
          AND y.institution_id = s.institution_id
        WHERE s.study_semester_id = NEW.study_semester_id AND s.institution_id = NEW.institution_id
        FOR SHARE OF s, p, d, y;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Study semester not found in institution' USING ERRCODE = '23503';
        END IF;
        IF NOT NEW.is_active AND EXISTS (
            SELECT 1 FROM public.section_subject_assignments a
            WHERE a.section_id = NEW.section_id AND a.institution_id = NEW.institution_id AND a.is_active
        ) THEN
            RAISE EXCEPTION 'Remove active subject assignments first' USING ERRCODE = '23514';
        END IF;
        NEW.name := btrim(NEW.name);
        NEW.code := btrim(NEW.code);
    ELSE
        SELECT c.is_active AND s.is_active AND p.is_active AND d.is_active AND y.is_active
        INTO parent_active
        FROM public.class_sections c
        JOIN public.study_semesters s ON s.study_semester_id = c.study_semester_id
          AND s.institution_id = c.institution_id
        JOIN public.programs p ON p.program_id = s.program_id AND p.institution_id = s.institution_id
        JOIN public.departments d ON d.department_id = p.department_id
          AND d.institution_id = p.institution_id
        JOIN public.academic_years y ON y.academic_year_id = s.academic_year_id
          AND y.institution_id = s.institution_id
        WHERE c.section_id = NEW.section_id AND c.institution_id = NEW.institution_id
        FOR SHARE OF c, s, p, d, y;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Section not found in institution' USING ERRCODE = '23503';
        END IF;
        SELECT subject.is_active AND d.is_active INTO subject_active
        FROM public.subjects subject
        JOIN public.departments d ON d.department_id = subject.department_id
          AND d.institution_id = subject.institution_id
        WHERE subject.subject_id = NEW.subject_id AND subject.institution_id = NEW.institution_id
        FOR SHARE OF subject, d;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Subject not found in institution' USING ERRCODE = '23503';
        END IF;
        -- A subject from another department is reusable within this institution.
        parent_active := parent_active AND subject_active;
    END IF;
    IF check_parent AND NOT parent_active THEN
        RAISE EXCEPTION 'Active academic parents required' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'INSERT' THEN NEW.created_at := now(); END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;
