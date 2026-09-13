-- ============================================================================
-- Phase 6.8 — Test / Exam Results (tenant-safe hardening of the existing
-- result tables)
-- ============================================================================
-- Phase 6.8 does NOT create a new result table: the existing
-- ``public.test_results`` (per-test/per-exam scores) and
-- ``public.student_results`` (per-semester consolidated summaries) tables
-- created by the Phase Admin-1 migration (20260909000000) already provide the
-- result data model, the FKs into the academic structure, the controlled
-- vocabularies, and the uniqueness rules:
--
--   test_results      UNIQUE(student_id, course_id, test_name,
--                            academic_year_id, semester_id)
--   student_results   UNIQUE(student_id, academic_year_id, semester_id,
--                            program_id)
--
-- This migration is purely ADDITIVE hardening so the result tables satisfy
-- the Phase 6.8 requirements, following exactly the Phase 6.7 attendance
-- pattern (which hardened student_attendance the same way):
--
--   1. tenant association -> a server-derived ``institution_id`` column whose
--      value always equals ``students.institution_id``. It is filled by a
--      BEFORE INSERT/UPDATE guard trigger from the STUDENT record — never
--      from the client — and cross-referenced against the academic context
--      (academic year, course, section, program) so a row can never pair a
--      student with academic context from a different institution.
--   2. score integrity -> ``scored_marks`` can never exceed ``max_marks``
--      (test_results), and ``total_credits_earned`` can never exceed
--      ``total_credits_max`` (student_results) at the database level.
--   3. academic-context integrity -> the row's academic_year_id/semester_id
--      must describe the SAME offering as an attached section (section ->
--      course_offerings), the academic year must belong to the student's
--      institution (academic_years.institution_id), the semester must belong
--      to the academic year (semesters.academic_year_id), and the
--      course/program must belong to the student's institution (via the
--      course/program -> department chain).
--   4. ownership immutability -> student_id / course_id / academic_year_id /
--      semester_id (test_results) and student_id / academic_year_id /
--      semester_id / program_id (student_results) can never be reassigned by
--      an UPDATE. section_id may be corrected but is revalidated on every
--      write.
--   5. updated_at freshness -> refreshed by the guard triggers on UPDATE.
--
-- ``percentage`` is DERIVED, not independently trusted: the application layer
-- computes it from scored_marks / max_marks on every create/update; the
-- existing ``test_results_percentage_check`` (0..100) remains the database
-- guard. No locked Phase 6.1-6.7 migration is modified. No new tables are
-- created. Application-layer authorization (RBAC + tenant) remains the
-- current model; these triggers are a database-level safety net.
-- ============================================================================

-- A. student_results.institution_id (same defense-in-depth pattern)
-- ---------------------------------------------------------------------------

ALTER TABLE "public"."student_results"
    ADD COLUMN "institution_id" "uuid";

UPDATE "public"."student_results" AS "sr"
SET "institution_id" = "s"."institution_id"
FROM "public"."students" AS "s"
WHERE "sr"."student_id" = "s"."student_id";

ALTER TABLE "public"."student_results"
    ALTER COLUMN "institution_id" SET NOT NULL;

ALTER TABLE ONLY "public"."student_results"
    ADD CONSTRAINT "student_results_institution_id_fkey"
    FOREIGN KEY ("institution_id")
    REFERENCES "public"."institutions" ("institution_id");

-- B. Score / credit integrity CHECKs (second defense layer)
-- ---------------------------------------------------------------------------
-- Server-side validation is enforced by the application layer; these CHECK
-- constraints guarantee the same invariants even for direct/service-role
-- writes. Both are compatible with the Phase Admin-1 seed data (verified:
-- 88/100, 76/100, 94/100, 18/20 and credits 8/8, 4/4).
-- The pre-existing ``test_results_max_marks_check`` (max_marks > 0),
-- ``test_results_scored_marks_check`` (scored_marks >= 0),
-- ``test_results_percentage_check`` (0..100) and
-- ``student_results_credits_check`` (total_credits_earned >= 0) are retained.

ALTER TABLE "public"."test_results"
    ADD CONSTRAINT "test_results_score_marks_check"
    CHECK (("scored_marks" IS NULL) OR ("scored_marks" <= "max_marks"));

ALTER TABLE "public"."student_results"
    ADD CONSTRAINT "student_results_credits_earned_max_check"
    CHECK (("total_credits_earned" IS NULL) OR ("total_credits_max" IS NULL)
        OR ("total_credits_earned" <= "total_credits_max"));

-- ============================================================================
-- C. test_results.institution_id (server-derived canonical tenant key)
-- ---------------------------------------------------------------------------
-- The canonical tenant key remains students.institution_id (Phase 6.1/6.6
-- locks). We DENORMALIZE it onto the result row ONLY so queries can scope
-- tenant-safely and the FK/trigger guarantee the invariant; the trigger
-- overrides any caller-supplied value, so it is never client-controlled.

ALTER TABLE "public"."test_results"
    ADD COLUMN "institution_id" "uuid";

-- Backfill existing rows from their student records (FK integrity guarantees
-- every row has exactly one student).
UPDATE "public"."test_results" AS "tr"
SET "institution_id" = "s"."institution_id"
FROM "public"."students" AS "s"
WHERE "tr"."student_id" = "s"."student_id";

ALTER TABLE "public"."test_results"
    ALTER COLUMN "institution_id" SET NOT NULL;

ALTER TABLE ONLY "public"."test_results"
    ADD CONSTRAINT "test_results_institution_id_fkey"
    FOREIGN KEY ("institution_id")
    REFERENCES "public"."institutions" ("institution_id");

-- D. test_results tenant / academic-context guard trigger
-- ---------------------------------------------------------------------------
-- BEFORE INSERT OR UPDATE:
--   * institution_id is ALWAYS re-derived from the STUDENT record (any
--     caller-supplied value is overridden);
--   * the academic year must exist and belong to the student's institution;
--   * the course must exist and belong to the student's institution
--     (courses -> departments -> institution_id);
--   * when a section is attached, the section's offering must match the
--     row's course_id / academic_year_id / semester_id and belong to the
--     student's institution. A broken academic chain fails closed;
--   * on UPDATE the ownership fields (student_id, course_id,
--     academic_year_id, semester_id) can never be reassigned; section_id may
--     be corrected but is revalidated on every write;
--   * updated_at is refreshed on every UPDATE.

CREATE OR REPLACE FUNCTION "public"."test_results_tenant_guard"()
RETURNS "trigger"
LANGUAGE "plpgsql"
AS $function$
DECLARE
    v_student_institution_id "uuid";
    v_ay_institution_id "uuid";
    v_course_institution_id "uuid";
    v_section_course_id "uuid";
    v_section_academic_year_id "uuid";
    v_section_semester_id "uuid";
    v_section_institution_id "uuid";
BEGIN
    SELECT "s"."institution_id" INTO v_student_institution_id
    FROM "public"."students" AS "s"
    WHERE "s"."student_id" = "NEW"."student_id";

    IF v_student_institution_id IS NULL THEN
        RAISE EXCEPTION 'test result student does not exist';
    END IF;

    -- The tenant is server-derived from the student record; any
    -- caller-supplied value is overridden.
    "NEW"."institution_id" := v_student_institution_id;

    SELECT "ay"."institution_id" INTO v_ay_institution_id
    FROM "public"."academic_years" AS "ay"
    WHERE "ay"."academic_year_id" = "NEW"."academic_year_id";

    IF v_ay_institution_id IS NULL THEN
        RAISE EXCEPTION 'test result academic year does not exist';
    END IF;

    IF v_ay_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'test result student and academic year belong to different institutions';
    END IF;

    SELECT "d"."institution_id" INTO v_course_institution_id
    FROM "public"."courses" AS "c"
    JOIN "public"."departments" AS "d"
        ON "d"."department_id" = "c"."department_id"
    WHERE "c"."course_id" = "NEW"."course_id";

    IF v_course_institution_id IS NULL THEN
        RAISE EXCEPTION 'test result course academic chain cannot be resolved';
    END IF;

    IF v_course_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'test result student and course belong to different institutions';
    END IF;

    IF "NEW"."section_id" IS NOT NULL THEN
        SELECT "co"."course_id", "co"."academic_year_id", "co"."semester_id",
               "d"."institution_id"
        INTO v_section_course_id, v_section_academic_year_id,
             v_section_semester_id, v_section_institution_id
        FROM "public"."sections" AS "sec"
        JOIN "public"."course_offerings" AS "co"
            ON "co"."course_offering_id" = "sec"."course_offering_id"
        JOIN "public"."courses" AS "c"
            ON "c"."course_id" = "co"."course_id"
        JOIN "public"."departments" AS "d"
            ON "d"."department_id" = "c"."department_id"
        WHERE "sec"."section_id" = "NEW"."section_id";

        IF v_section_institution_id IS NULL THEN
            RAISE EXCEPTION 'test result section academic chain cannot be resolved';
        END IF;

        IF v_section_institution_id IS DISTINCT FROM v_student_institution_id THEN
            RAISE EXCEPTION 'test result student and section belong to different institutions';
        END IF;

        IF v_section_course_id IS DISTINCT FROM "NEW"."course_id"
           OR v_section_academic_year_id IS DISTINCT FROM "NEW"."academic_year_id"
           OR v_section_semester_id IS DISTINCT FROM "NEW"."semester_id" THEN
            RAISE EXCEPTION 'test result academic context must match the section offering';
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF "NEW"."student_id"      IS DISTINCT FROM "OLD"."student_id"
           OR "NEW"."course_id"    IS DISTINCT FROM "OLD"."course_id"
           OR "NEW"."academic_year_id" IS DISTINCT FROM "OLD"."academic_year_id"
           OR "NEW"."semester_id"  IS DISTINCT FROM "OLD"."semester_id" THEN
            RAISE EXCEPTION 'test result ownership fields cannot be changed';
        END IF;
        "NEW"."updated_at" := "now"();
    END IF;

    RETURN "NEW";
END;
$function$;

DROP TRIGGER IF EXISTS "trg_test_results_tenant_guard"
    ON "public"."test_results";

CREATE TRIGGER "trg_test_results_tenant_guard"
    BEFORE INSERT OR UPDATE ON "public"."test_results"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."test_results_tenant_guard"();

-- E. student_results tenant / academic-context guard trigger
-- ---------------------------------------------------------------------------
-- Same invariants as the test_results guard, adapted to the consolidated
-- per-semester summary row:
--   * institution_id is ALWAYS re-derived from the STUDENT record;
--   * the academic year must exist and belong to the student's institution;
--   * the semester must exist and belong to that academic year
--     (semesters.academic_year_id);
--   * the program must exist and belong to the student's institution
--     (programs -> departments -> institution_id);
--   * on UPDATE the ownership fields (student_id, academic_year_id,
--     semester_id, program_id) can never be reassigned;
--   * updated_at is refreshed on every UPDATE.

CREATE OR REPLACE FUNCTION "public"."student_results_tenant_guard"()
RETURNS "trigger"
LANGUAGE "plpgsql"
AS $function$
DECLARE
    v_student_institution_id "uuid";
    v_ay_institution_id "uuid";
    v_semester_academic_year_id "uuid";
    v_program_institution_id "uuid";
BEGIN
    SELECT "s"."institution_id" INTO v_student_institution_id
    FROM "public"."students" AS "s"
    WHERE "s"."student_id" = "NEW"."student_id";

    IF v_student_institution_id IS NULL THEN
        RAISE EXCEPTION 'result student does not exist';
    END IF;

    -- The tenant is server-derived from the student record; any
    -- caller-supplied value is overridden.
    "NEW"."institution_id" := v_student_institution_id;

    SELECT "ay"."institution_id" INTO v_ay_institution_id
    FROM "public"."academic_years" AS "ay"
    WHERE "ay"."academic_year_id" = "NEW"."academic_year_id";

    IF v_ay_institution_id IS NULL THEN
        RAISE EXCEPTION 'result academic year does not exist';
    END IF;

    IF v_ay_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'result student and academic year belong to different institutions';
    END IF;

    SELECT "sem"."academic_year_id" INTO v_semester_academic_year_id
    FROM "public"."semesters" AS "sem"
    WHERE "sem"."semester_id" = "NEW"."semester_id";

    IF v_semester_academic_year_id IS NULL THEN
        RAISE EXCEPTION 'result semester does not exist';
    END IF;

    IF v_semester_academic_year_id IS DISTINCT FROM "NEW"."academic_year_id" THEN
        RAISE EXCEPTION 'result semester must belong to the result academic year';
    END IF;

    SELECT "d"."institution_id" INTO v_program_institution_id
    FROM "public"."programs" AS "p"
    JOIN "public"."departments" AS "d"
        ON "d"."department_id" = "p"."department_id"
    WHERE "p"."program_id" = "NEW"."program_id";

    IF v_program_institution_id IS NULL THEN
        RAISE EXCEPTION 'result program academic chain cannot be resolved';
    END IF;

    IF v_program_institution_id IS DISTINCT FROM v_student_institution_id THEN
        RAISE EXCEPTION 'result student and program belong to different institutions';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF "NEW"."student_id"      IS DISTINCT FROM "OLD"."student_id"
           OR "NEW"."academic_year_id" IS DISTINCT FROM "OLD"."academic_year_id"
           OR "NEW"."semester_id"  IS DISTINCT FROM "OLD"."semester_id"
           OR "NEW"."program_id"   IS DISTINCT FROM "OLD"."program_id" THEN
            RAISE EXCEPTION 'result ownership fields cannot be changed';
        END IF;
        "NEW"."updated_at" := "now"();
    END IF;

    RETURN "NEW";
END;
$function$;

DROP TRIGGER IF EXISTS "trg_student_results_tenant_guard"
    ON "public"."student_results";

CREATE TRIGGER "trg_student_results_tenant_guard"
    BEFORE INSERT OR UPDATE ON "public"."student_results"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."student_results_tenant_guard"();

-- F. Indexes (justified query patterns)
-- ---------------------------------------------------------------------------
-- * tenant-scoped management lists by institution;
-- * the existing student/conducted ordering used by list_test_results;
-- * the academic-year/semester filter used by admin and student reads;
-- * the student/issued ordering used by list_student_results.

CREATE INDEX IF NOT EXISTS "idx_test_results_institution_id"
    ON "public"."test_results" ("institution_id");

CREATE INDEX IF NOT EXISTS "idx_test_results_student_conducted"
    ON "public"."test_results" ("student_id", "conducted_at");

CREATE INDEX IF NOT EXISTS "idx_test_results_ay_semester"
    ON "public"."test_results" ("academic_year_id", "semester_id");

CREATE INDEX IF NOT EXISTS "idx_student_results_institution_id"
    ON "public"."student_results" ("institution_id");

CREATE INDEX IF NOT EXISTS "idx_student_results_student_issued"
    ON "public"."student_results" ("student_id", "issued_at");

CREATE INDEX IF NOT EXISTS "idx_student_results_ay_semester"
    ON "public"."student_results" ("academic_year_id", "semester_id");

-- G. Column comments ---------------------------------------------------------

COMMENT ON COLUMN "public"."test_results"."institution_id"
    IS 'Canonical tenant key denormalized onto the result row. Always equals students.institution_id; maintained by the test_results_tenant_guard trigger and never trusted from the client.';

COMMENT ON COLUMN "public"."student_results"."institution_id"
    IS 'Canonical tenant key denormalized onto the result row. Always equals students.institution_id; maintained by the student_results_tenant_guard trigger and never trusted from the client.';

-- ============================================================================
-- ROLLBACK (inverse DDL — apply manually only if this phase is reverted)
-- ============================================================================
-- DROP TRIGGER IF EXISTS "trg_student_results_tenant_guard"
--     ON "public"."student_results";
-- DROP TRIGGER IF EXISTS "trg_test_results_tenant_guard"
--     ON "public"."test_results";
-- DROP FUNCTION IF EXISTS "public"."student_results_tenant_guard"();
-- DROP FUNCTION IF EXISTS "public"."test_results_tenant_guard"();
-- DROP INDEX IF EXISTS "idx_student_results_ay_semester";
-- DROP INDEX IF EXISTS "idx_student_results_student_issued";
-- DROP INDEX IF EXISTS "idx_student_results_institution_id";
-- DROP INDEX IF EXISTS "idx_test_results_ay_semester";
-- DROP INDEX IF EXISTS "idx_test_results_student_conducted";
-- DROP INDEX IF EXISTS "idx_test_results_institution_id";
-- ALTER TABLE "public"."student_results"
--     DROP CONSTRAINT "student_results_credits_earned_max_check",
--     DROP CONSTRAINT "student_results_institution_id_fkey";
-- ALTER TABLE "public"."test_results"
--     DROP CONSTRAINT "test_results_score_marks_check",
--     DROP CONSTRAINT "test_results_institution_id_fkey";
-- ALTER TABLE "public"."student_results" DROP COLUMN "institution_id";
-- ALTER TABLE "public"."test_results" DROP COLUMN "institution_id";
-- ============================================================================