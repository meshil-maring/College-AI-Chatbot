-- Add guards to Stage 2 tables without replacing any existing routine or source.
CREATE FUNCTION public.guard_academic_sections_parent() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-foundations:' || NEW.institution_id::text, 0)
    );
    IF NEW.is_active THEN RETURN NEW; END IF;
    IF TG_TABLE_NAME = 'study_semesters' THEN
        IF EXISTS (
            SELECT 1 FROM public.class_sections c
            WHERE c.study_semester_id = NEW.study_semester_id
              AND c.institution_id = NEW.institution_id AND c.is_active
        ) THEN
            RAISE EXCEPTION 'Deactivate dependent sections first' USING ERRCODE = '23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'subjects' THEN
        IF EXISTS (
            SELECT 1 FROM public.section_subject_assignments a
            WHERE a.subject_id = NEW.subject_id
              AND a.institution_id = NEW.institution_id AND a.is_active
        ) THEN
            RAISE EXCEPTION 'Remove active subject assignments first' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DO $$
DECLARE entity text;
BEGIN
    FOREACH entity IN ARRAY ARRAY['study_semesters', 'subjects'] LOOP
        EXECUTE format('CREATE TRIGGER academic_sections_parent_guard BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.guard_academic_sections_parent()', entity);
    END LOOP;
END;
$$;
