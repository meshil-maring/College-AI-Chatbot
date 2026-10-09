-- Some linked databases predate the reconstructed baseline and retain a
-- semester_number curriculum column instead of the optional semester UUID.
-- Preserve those values while aligning the table with Academic Setup.
BEGIN;

ALTER TABLE public.program_courses
    ADD COLUMN IF NOT EXISTS semester_id uuid;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_constraint
        WHERE conrelid = 'public.program_courses'::regclass
          AND conname = 'program_courses_semester_id_fkey'
    ) THEN
        ALTER TABLE public.program_courses
            ADD CONSTRAINT program_courses_semester_id_fkey
            FOREIGN KEY (semester_id) REFERENCES public.semesters(semester_id);
    END IF;

    -- New curriculum links may apply to any semester. An obsolete required
    -- number must not prevent inserts through the existing audited write RPC.
    IF EXISTS (
        SELECT 1 FROM pg_catalog.pg_attribute
        WHERE attrelid = 'public.program_courses'::regclass
          AND attname = 'semester_number' AND NOT attisdropped
    ) THEN
        ALTER TABLE public.program_courses
            ALTER COLUMN semester_number DROP NOT NULL;
    END IF;
END;
$$;

NOTIFY pgrst, 'reload schema';
COMMIT;
