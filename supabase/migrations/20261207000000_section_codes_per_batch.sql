-- Section codes are unique within a batch's program semester instead of
-- across the institution, so every batch can use simple codes such as "A" and
-- "B", and Section A can continue from Semester 1 into Semester 2.
--
-- Nothing resolves a section by its code alone (codes are display labels;
-- every lookup uses academic_section_id), and codes that are unique across the
-- institution are already unique within each batch and program semester, so
-- existing rows comply.
-- The new index is created before the old one is dropped, so there is no
-- window without a uniqueness rule.
BEGIN;

SET LOCAL lock_timeout = '10s';

CREATE UNIQUE INDEX academic_sections_cohort_code_unique
    ON public.academic_sections (admission_cohort_id, program_semester_id, lower(btrim(code)));

DROP INDEX public.academic_sections_code_unique;

COMMIT;
