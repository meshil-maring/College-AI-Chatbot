-- Academic Setup consistency rules (feat/academic-setup-workflow).
--
-- 1. Published curricula snapshot each subject's credits and teaching hours.
--    The snapshot columns were integer while courses store numeric(5,2), so a
--    1.5-credit subject would be frozen as 2. The snapshot now uses the same
--    numeric(5,2) type. Existing values are whole numbers and convert exactly.
--
-- 2. New write rules, enforced by one extra BEFORE trigger. They block new
--    inconsistent data only; a read-only check of the live project before this
--    migration found no rows that break them.
--    - A batch starts in the calendar year its intake academic year starts,
--      and cannot run longer than its program's duration (shorter spans remain
--      allowed for lateral-entry batches).
--    - A section's dated teaching term must fall within its batch's years.
--    - A subject offering's capacity cannot exceed its section's capacity, and a
--      section's capacity cannot be lowered below an active offering's capacity.
--
-- Violations raise 23514 like the existing structure guards; the frontend
-- checks the same rules first so administrators see a specific message.
BEGIN;

SET LOCAL lock_timeout = '10s';

ALTER TABLE public.curriculum_subjects
    ALTER COLUMN credits TYPE numeric(5,2),
    ALTER COLUMN lecture_hours TYPE numeric(5,2),
    ALTER COLUMN tutorial_hours TYPE numeric(5,2),
    ALTER COLUMN practical_hours TYPE numeric(5,2);

CREATE FUNCTION public.validate_academic_setup_consistency() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    intake_start date;
    duration numeric;
    cohort record;
    term record;
    section_capacity integer;
BEGIN
    -- Same tenant lock as every other academic write, so capacity checks on
    -- sections and offerings cannot interleave.
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:' || NEW.institution_id::text, 0));
    CASE TG_TABLE_NAME
    WHEN 'admission_cohorts' THEN
        IF TG_OP = 'UPDATE'
           AND NEW.academic_year_id IS NOT DISTINCT FROM OLD.academic_year_id
           AND NEW.start_year IS NOT DISTINCT FROM OLD.start_year
           AND NEW.end_year IS NOT DISTINCT FROM OLD.end_year THEN
            RETURN NEW;
        END IF;
        SELECT y.start_date INTO intake_start FROM public.academic_years y
         WHERE y.academic_year_id = NEW.academic_year_id AND y.institution_id = NEW.institution_id;
        SELECT p.duration_years INTO duration FROM public.programs p
         WHERE p.program_id = NEW.program_id;
        IF intake_start IS NOT NULL
           AND NEW.start_year <> EXTRACT(YEAR FROM intake_start)::integer THEN
            RAISE EXCEPTION 'Batch start year must match its intake academic year'
                USING ERRCODE = '23514';
        END IF;
        IF duration IS NOT NULL AND NEW.end_year - NEW.start_year > ceil(duration) THEN
            RAISE EXCEPTION 'Batch cannot run longer than its program duration'
                USING ERRCODE = '23514';
        END IF;
    WHEN 'academic_sections' THEN
        IF TG_OP = 'INSERT'
           OR NEW.admission_cohort_id IS DISTINCT FROM OLD.admission_cohort_id
           OR NEW.semester_id IS DISTINCT FROM OLD.semester_id THEN
            SELECT c.start_year, c.end_year INTO cohort FROM public.admission_cohorts c
             WHERE c.admission_cohort_id = NEW.admission_cohort_id
               AND c.institution_id = NEW.institution_id;
            SELECT s.start_date, s.end_date INTO term FROM public.semesters s
             WHERE s.semester_id = NEW.semester_id;
            IF cohort.start_year IS NOT NULL AND term.start_date IS NOT NULL
               AND (term.start_date < make_date(cohort.start_year, 1, 1)
                    OR term.end_date > make_date(cohort.end_year, 12, 31)) THEN
                RAISE EXCEPTION 'Section teaching term must fall within its batch years'
                    USING ERRCODE = '23514';
            END IF;
        END IF;
        IF NEW.capacity IS NOT NULL AND (TG_OP = 'INSERT' OR NEW.capacity IS DISTINCT FROM OLD.capacity)
           AND EXISTS (SELECT 1 FROM public.academic_offerings o
                        WHERE o.academic_section_id = NEW.academic_section_id
                          AND o.is_active AND o.capacity > NEW.capacity) THEN
            RAISE EXCEPTION 'Section capacity is below a subject offering capacity'
                USING ERRCODE = '23514';
        END IF;
    WHEN 'academic_offerings' THEN
        IF NEW.capacity IS NOT NULL AND NEW.is_active THEN
            SELECT s.capacity INTO section_capacity FROM public.academic_sections s
             WHERE s.academic_section_id = NEW.academic_section_id
               AND s.institution_id = NEW.institution_id;
            IF section_capacity IS NOT NULL AND NEW.capacity > section_capacity THEN
                RAISE EXCEPTION 'Offering capacity cannot exceed its section capacity'
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END CASE;
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.validate_academic_setup_consistency() FROM PUBLIC, anon, authenticated;

CREATE TRIGGER structure_consistency BEFORE INSERT OR UPDATE ON public.admission_cohorts
    FOR EACH ROW EXECUTE FUNCTION public.validate_academic_setup_consistency();
CREATE TRIGGER structure_consistency BEFORE INSERT OR UPDATE ON public.academic_sections
    FOR EACH ROW EXECUTE FUNCTION public.validate_academic_setup_consistency();
CREATE TRIGGER structure_consistency BEFORE INSERT OR UPDATE ON public.academic_offerings
    FOR EACH ROW EXECUTE FUNCTION public.validate_academic_setup_consistency();

NOTIFY pgrst, 'reload schema';

COMMIT;
