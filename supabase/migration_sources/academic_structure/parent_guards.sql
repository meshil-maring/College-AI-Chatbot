-- Extend deactivation protection without changing Stage 1 routines or sources.
CREATE FUNCTION public.guard_academic_structure_parent() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-foundations:' || NEW.institution_id::text, 0)
    );
    IF NEW.is_active THEN RETURN NEW; END IF;
    IF TG_TABLE_NAME = 'departments' THEN
        IF EXISTS (
            SELECT 1 FROM public.subjects s
            WHERE s.department_id = NEW.department_id
              AND s.institution_id = NEW.institution_id AND s.is_active
        ) THEN
            RAISE EXCEPTION 'Deactivate dependent subjects first' USING ERRCODE = '23514';
        END IF;
        -- Existing Stage 1 guard already refuses active degree programs.
    ELSIF TG_TABLE_NAME = 'programs' THEN
        IF EXISTS (
            SELECT 1 FROM public.study_semesters s
            WHERE s.program_id = NEW.program_id
              AND s.institution_id = NEW.institution_id AND s.is_active
        ) THEN
            RAISE EXCEPTION 'Deactivate dependent study semesters first' USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'academic_years' THEN
        IF EXISTS (
            SELECT 1 FROM public.study_semesters s
            WHERE s.academic_year_id = NEW.academic_year_id
              AND s.institution_id = NEW.institution_id AND s.is_active
        ) THEN
            RAISE EXCEPTION 'Deactivate dependent study semesters first' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DO $$
DECLARE entity text;
BEGIN
    FOREACH entity IN ARRAY ARRAY['departments', 'programs', 'academic_years'] LOOP
        EXECUTE format('CREATE TRIGGER academic_structure_parent_guard BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.guard_academic_structure_parent()', entity);
    END LOOP;
END;
$$;
